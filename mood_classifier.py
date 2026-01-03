import os
import json
import tempfile
from typing import Dict, Any

import numpy as np

# =============================
#  OPTIONAL AUDIO LIBRARIES
# =============================
try:
    import librosa
    import soundfile as sf
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

# =============================
#  OPTIONAL HUGGINGFACE STUFF
# =============================
try:
    from transformers import pipeline
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

def classify_mood(audio_file: bytes, file_format: str = "wav") -> Dict[str, Any]:
    """
    Classify mood/characteristics of audio from bytes.
    
    Args:
        audio_file: Audio file as bytes
        file_format: File format extension (default: "wav")
    
    Returns:
        Dictionary with mood classification results
    """
    if not AUDIO_AVAILABLE:
        return {"error": "Audio libraries missing. Please install librosa and soundfile."}

    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_format}") as tmp:
            tmp.write(audio_file)
            tmp_path = tmp.name

        y, sr = librosa.load(tmp_path, sr=22050, duration=30, mono=True)
        if len(y) < sr * 2:
            return {"error": "Audio too short (minimum 2 seconds required)"}

        rms = librosa.feature.rms(y=y)[0]
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)

        avg_rms = float(np.mean(rms))
        raw_onset = float(np.mean(onset_env))
        raw_mfcc_var = float(np.var(mfcc))

        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]

        avg_centroid = float(np.mean(centroid))
        avg_bandwidth = float(np.mean(bandwidth))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)[0]))

        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempo = float(tempo)

        # ---------- High-level categorical descriptors ----------

        # Tempo label
        if tempo < 80:
            tempo_label = "slow"
        elif tempo < 120:
            tempo_label = "moderate"
        else:
            tempo_label = "fast"

        # Loudness / dynamics (robust normalization)
        rms_p10 = float(np.percentile(rms, 10))
        rms_p90 = float(np.percentile(rms, 90))
        rms_norm = (avg_rms - rms_p10) / (rms_p90 - rms_p10 + 1e-9)
        rms_norm = float(np.clip(rms_norm, 0.0, 1.0))

        if rms_norm < 0.3:
            dynamic_profile = "soft"
        elif rms_norm < 0.7:
            dynamic_profile = "medium"
        else:
            dynamic_profile = "strong"

        # Onset / rhythmic activity
        onset_energy = float(np.log1p(raw_onset))
        onset_median = float(np.median(onset_env))
        onset_norm = onset_energy / (onset_median + 1e-9)
        onset_norm = float(np.clip(onset_norm, 0.0, 3.0))

        if onset_norm < 0.8:
            rhythmic_profile = "smooth"
        elif onset_norm < 1.6:
            rhythmic_profile = "groovy"
        else:
            rhythmic_profile = "driving"

        # Timbre (brightness)
        timbre_score = float(
            0.65 * (avg_centroid / 3000.0) +
            0.35 * (avg_bandwidth / 4000.0)
        )

        if timbre_score < 0.45:
            timbre = "dark"
        elif timbre_score < 0.75:
            timbre = "neutral"
        else:
            timbre = "bright"

        # Texture density (harmonic/texture complexity)
        mfcc_var_log = float(np.log1p(raw_mfcc_var))
        if mfcc_var_log < 6.0:
            texture_density = "sparse"
        elif mfcc_var_log < 8.5:
            texture_density = "medium"
        else:
            texture_density = "dense"

        # Expression (using HF model if available)
        expression = "unknown"
        if HF_AVAILABLE:
            try:
                emo = pipeline(
                    "audio-classification",
                    model="MIT/ast-finetuned-audioset-10-10-0.4593",
                    device=-1
                )
                top = emo(tmp_path)[0]
                tag = top["label"].lower()

                if any(x in tag for x in ["choir", "vocal", "sing", "speech"]):
                    expression = "vocal"
                elif any(x in tag for x in ["instrument", "guitar", "piano", "string"]):
                    expression = "instrumental"
                elif any(x in tag for x in ["drum", "beat", "percussion"]):
                    expression = "rhythmic"
                elif "ambient" in tag:
                    expression = "ambient"
                else:
                    expression = "mixed"
            except:
                expression = "unknown"

        # Quick human-friendly tags (for playlist / use-case thinking)
        tags = []

        if tempo_label == "slow":
            tags.append("slow-paced")
        elif tempo_label == "moderate":
            tags.append("mid-tempo")
        else:
            tags.append("fast-tempo")

        if dynamic_profile == "soft":
            tags.append("gentle-dynamics")
        elif dynamic_profile == "strong":
            tags.append("powerful-dynamics")

        if rhythmic_profile == "smooth":
            tags.append("smooth-flow")
        elif rhythmic_profile == "groovy":
            tags.append("rhythmic-groove")
        else:
            tags.append("driving-rhythm")

        if timbre == "dark":
            tags.append("warm-dark-tone")
        elif timbre == "bright":
            tags.append("bright-edgy-tone")

        if texture_density == "sparse":
            tags.append("minimal-texture")
        elif texture_density == "dense":
            tags.append("rich-texture")

        if expression != "unknown":
            tags.append(f"{expression}-focused")

        # Summary block for the LLM / UI
        summary = {
            "tempo_bpm": tempo,
            "tempo_label": tempo_label,
            "dynamic_profile": dynamic_profile,
            "rhythmic_profile": rhythmic_profile,
            "timbre": timbre,
            "texture_density": texture_density,
            "expression": expression,
        }

        # Low-level features for more advanced analysis
        features = {
            "tempo": tempo,
            "avg_rms": avg_rms,
            "onset_energy_log": onset_energy,
            "mfcc_variance_log": mfcc_var_log,
            "spectral_centroid": avg_centroid,
            "spectral_bandwidth": avg_bandwidth,
            "zcr": zcr,
            "rms_norm": rms_norm,
            "onset_norm": onset_norm,
        }

        return {
            "timbre": timbre,
            "expression": expression,
            "summary": summary,
            "tags": tags,
            "features": features,
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass

