"""
Piano Extraction and Sheet Music Generation Module
Extracts piano notes from mixed audio, generates sheet music PDF, and synthesizes MIDI to audio.
"""

import os
import numpy as np
from typing import Optional, List, Tuple, Dict, Callable
import tempfile
import subprocess

# Audio processing imports
try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    librosa = None
    sf = None

# MIDI imports
try:
    from midiutil import MIDIFile
    MIDIUTIL_AVAILABLE = True
except ImportError:
    MIDIUTIL_AVAILABLE = False
    MIDIFile = None

try:
    import pretty_midi
    PRETTY_MIDI_AVAILABLE = True
except ImportError:
    PRETTY_MIDI_AVAILABLE = False
    pretty_midi = None

# Sheet music generation
try:
    import music21
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False
    music21 = None

# PDF generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    canvas = None


class PianoExtractor:
    """
    Extracts piano notes from mixed audio, generates sheet music, and synthesizes MIDI to audio.
    """
    
    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    def __init__(self):
        """Initialize the Piano Extractor."""
        if not LIBROSA_AVAILABLE:
            raise ImportError("librosa and soundfile are required. Install with: pip install librosa soundfile")
    
    def extract_piano_from_audio(self, audio_path: str, 
                                  target_sr: int = 16000,  # Lower SR for speed
                                  hop_length: int = 1024,  # Larger hop for speed
                                  frame_length: int = 2048,
                                  fmin: float = 27.5,  # A0 (lowest piano note)
                                  fmax: float = 4186.0,
                                  max_duration: Optional[float] = 60.0) -> Tuple[np.ndarray, int]:
        """
        Extract ONLY piano audio from mixed audio, removing vocals and other instruments.
        Uses harmonic-percussive separation and vocal suppression techniques.
        
        Args:
            audio_path: Path to input audio file
            target_sr: Target sample rate (lower = faster)
            hop_length: Hop length for STFT (larger = faster)
            frame_length: Frame length for STFT
            fmin: Minimum frequency (A0 = 27.5 Hz)
            fmax: Maximum frequency (C8 = 4186 Hz)
            max_duration: Maximum duration in seconds to process (None = full file)
            
        Returns:
            Tuple of (piano_audio_array, sample_rate) - vocals removed
        """
        if not LIBROSA_AVAILABLE:
            raise ImportError("librosa is required for audio processing")
        
        # Load audio - preserve stereo if available for better vocal removal
        y, sr = librosa.load(audio_path, sr=target_sr, mono=False, duration=max_duration)
        
        # Process stereo vs mono differently
        if len(y.shape) > 1:
            # STEREO: Use difference channel technique to remove centered vocals
            # Vocals are typically centered (same in L and R), piano is often panned
            y_left = y[0]
            y_right = y[1]
            
            # Extract harmonic components from both channels (piano is harmonic)
            y_harmonic_l, y_percussive_l = librosa.effects.hpss(y_left, margin=8.0)
            y_harmonic_r, y_percussive_r = librosa.effects.hpss(y_right, margin=8.0)
            
            # Difference channel: L - R removes centered vocals, keeps panned instruments
            y_diff = y_harmonic_l - y_harmonic_r
            
            # Sum channel: L + R keeps everything (but we'll filter it)
            y_sum = (y_harmonic_l + y_harmonic_r) / 2
            
            # Blend: prefer difference (less vocals) but keep some sum for fullness
            y = 0.8 * y_diff + 0.2 * y_sum
        else:
            # MONO: Use HPSS to separate harmonic (piano) from percussive (drums/vocals)
            y_harmonic, y_percussive = librosa.effects.hpss(y, margin=8.0)
            # Piano is primarily harmonic, vocals have more percussive/transient elements
            y = y_harmonic
        
        # Apply frequency filtering to focus on piano range and suppress vocal frequencies
        stft = librosa.stft(y, hop_length=hop_length, n_fft=frame_length)
        frequencies = librosa.fft_frequencies(sr=sr, n_fft=frame_length)
        magnitudes = np.abs(stft)
        phases = np.angle(stft)
        
        # Create mask for piano frequency range
        piano_mask = (frequencies >= fmin) & (frequencies <= fmax)
        
        # Suppress vocal frequency ranges (vocals: ~85-255 Hz fundamental, but harmonics extend higher)
        # Vocal fundamentals: 85-255 Hz (male: 85-180 Hz, female: 165-255 Hz)
        # Vocal harmonics extend up to ~3000 Hz, but we'll suppress the fundamental range more aggressively
        vocal_fundamental_min = 80.0
        vocal_fundamental_max = 300.0
        vocal_mask = ~((frequencies >= vocal_fundamental_min) & (frequencies <= vocal_fundamental_max))
        
        # Also suppress very high frequencies (above piano range) that might contain vocal artifacts
        high_freq_mask = frequencies <= fmax
        
        # Combine masks: keep piano range, suppress vocal fundamentals, remove high noise
        combined_mask = piano_mask & vocal_mask & high_freq_mask
        
        # Apply spectral subtraction: reduce energy in vocal range
        stft_filtered = stft.copy()
        
        # Strong suppression in vocal fundamental range
        for i, freq in enumerate(frequencies):
            if not combined_mask[i]:
                # Suppress non-piano frequencies
                stft_filtered[i, :] *= 0.1  # Reduce by 90%
            elif (freq >= vocal_fundamental_min) and (freq <= vocal_fundamental_max):
                # Extra suppression for vocal fundamental range
                stft_filtered[i, :] *= 0.05  # Reduce by 95%
        
        # Apply magnitude-based filtering: keep strong harmonic components (piano)
        # Reduce components that look like vocal formants
        magnitudes_filtered = np.abs(stft_filtered)
        # Enhance strong harmonic components (piano has clear harmonics)
        harmonic_enhancement = np.ones_like(magnitudes_filtered)
        for i in range(1, len(frequencies) - 1):
            # If this frequency is a harmonic of a lower frequency, enhance it (piano characteristic)
            for harmonic in [2, 3, 4]:  # Check 2nd, 3rd, 4th harmonics
                if i * harmonic < len(frequencies):
                    if magnitudes_filtered[i * harmonic, :].max() > 0.3:
                        harmonic_enhancement[i, :] *= 1.2
        
        stft_filtered = stft_filtered * harmonic_enhancement
        
        # Convert back to time domain
        y_filtered = librosa.istft(stft_filtered, hop_length=hop_length, n_fft=frame_length)
        
        # Apply additional filtering: remove residual vocal-like transients
        # Use median filtering to smooth out vocal artifacts
        if len(y_filtered) > 0:
            # Simple smoothing to reduce vocal transients
            window_size = int(sr * 0.01)  # 10ms window
            if window_size > 1:
                y_smooth = np.convolve(y_filtered, np.ones(window_size)/window_size, mode='same')
                y_filtered = 0.8 * y_filtered + 0.2 * y_smooth
        
        # Normalize audio
        if np.max(np.abs(y_filtered)) > 0:
            y_filtered = y_filtered / np.max(np.abs(y_filtered))
        
        return y_filtered, sr
    
    def extract_notes_from_piano_audio(self, audio_array: np.ndarray, sr: int,
                                       hop_length: int = 1024,  # Larger hop for speed
                                       frame_length: int = 2048,
                                       fmin: float = 27.5,
                                       fmax: float = 4186.0) -> List[Tuple[float, str, int, float, float]]:
        """
        Extract musical notes from piano audio using optimized pitch detection.
        Enhanced to merge consecutive frames and properly detect note onsets.
        
        Args:
            audio_array: Audio signal array
            sr: Sample rate
            hop_length: Hop length for analysis (larger = faster)
            frame_length: Frame length for analysis
            fmin: Minimum frequency
            fmax: Maximum frequency
            
        Returns:
            List of tuples: (time, note_name, octave, frequency, duration)
        """
        if not LIBROSA_AVAILABLE:
            raise ImportError("librosa is required")
        
        # Extract fundamental frequencies using pyin with optimized parameters
        # Increase fmin to avoid detecting very low subharmonics (piano lowest note is A0 = 27.5 Hz)
        # But for most music, we want to start from around C2 (65.41 Hz) to avoid grave notes
        effective_fmin = max(fmin, 60.0)  # Minimum 60 Hz to avoid very low subharmonics
        effective_fmax = min(fmax, 2000.0)  # Limit to reasonable piano range
        
        f0, voiced_flag, voiced_probs = librosa.pyin(
            audio_array,
            fmin=effective_fmin,
            fmax=effective_fmax,
            frame_length=frame_length,
            hop_length=hop_length,
            n_thresholds=50  # Reduced from 100 for speed
        )
        
        # Enhanced note extraction with proper onset detection and merging
        notes = []
        times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=hop_length)
        
        # Minimum note duration (in seconds) to filter out noise
        min_note_duration = 0.1  # 100ms minimum
        
        # Process frames to detect note onsets and merge consecutive same notes
        current_note = None
        current_note_start_idx = None
        current_note_start_time = None
        
        for i, (time, freq) in enumerate(zip(times, f0)):
            # Check if this frame has a valid frequency
            # Filter out very low frequencies that are likely subharmonics
            if not np.isnan(freq) and voiced_flag[i] and effective_fmin <= freq <= effective_fmax:
                note_name, octave = self._frequency_to_note(freq)
                
                if note_name:
                    # Additional validation: filter out notes that are too low
                    # Most piano music is in the range C1 (octave 1) to C7 (octave 7)
                    # If we detect a note below C1, it might be a subharmonic - correct octave or skip
                    if octave < 1:
                        # Check if doubling the frequency gives a valid note in a higher octave
                        doubled_freq = freq * 2.0
                        if effective_fmin <= doubled_freq <= effective_fmax:
                            note_name_doubled, octave_doubled = self._frequency_to_note(doubled_freq)
                            if note_name_doubled and 1 <= octave_doubled <= 7:
                                # Use the doubled frequency (one octave higher)
                                note_name = note_name_doubled
                                octave = octave_doubled
                                freq = doubled_freq
                            else:
                                # Skip this note - it's too low
                                continue
                        else:
                            # Skip this note - it's too low
                            continue
                    
                    # Filter out notes above C7 (octave 7) as they're likely harmonics
                    if octave > 7:
                        continue
                    
                    # Check if this is a continuation of the current note
                    if current_note is not None:
                        # Check if frequency is close enough to current note (within 50 cents = ~3% frequency difference)
                        current_freq = current_note[3]  # frequency from current_note tuple
                        freq_ratio = freq / current_freq if current_freq > 0 else 1.0
                        cents_diff = 1200 * np.log2(freq_ratio) if freq_ratio > 0 else 1000
                        
                        # If same note (within 50 cents) and same note name/octave, continue the note
                        if (abs(cents_diff) < 50 and 
                            current_note[1] == note_name and 
                            current_note[2] == octave):
                            # Continue current note - update end time
                            continue
                    
                    # This is a new note onset - save previous note if it exists and meets minimum duration
                    if current_note is not None and current_note_start_idx is not None:
                        duration = time - current_note_start_time
                        if duration >= min_note_duration:
                            # Update duration in the note tuple
                            final_note = (current_note[0], current_note[1], current_note[2], 
                                        current_note[3], duration)
                            notes.append(final_note)
                    
                    # Start new note
                    current_note = (time, note_name, octave, freq, 0.0)  # duration will be calculated later
                    current_note_start_idx = i
                    current_note_start_time = time
            else:
                # No valid frequency - end current note if it exists
                if current_note is not None and current_note_start_idx is not None:
                    duration = time - current_note_start_time
                    if duration >= min_note_duration:
                        final_note = (current_note[0], current_note[1], current_note[2], 
                                    current_note[3], duration)
                        notes.append(final_note)
                    current_note = None
                    current_note_start_idx = None
                    current_note_start_time = None
        
        # Don't forget the last note
        if current_note is not None and current_note_start_idx is not None:
            if len(times) > 0:
                final_time = times[-1] + (times[1] - times[0]) if len(times) > 1 else times[-1]
                duration = final_time - current_note_start_time
                if duration >= min_note_duration:
                    final_note = (current_note[0], current_note[1], current_note[2], 
                                current_note[3], duration)
                    notes.append(final_note)
        
        # Sort by time
        notes.sort(key=lambda x: x[0])
        
        # Filter out notes that are too close together (likely noise or duplicates)
        # Minimum time gap between note onsets (in seconds)
        min_onset_gap = 0.05  # 50ms minimum gap
        filtered_notes = []
        
        for i, note in enumerate(notes):
            if i == 0:
                # Always keep the first note
                filtered_notes.append(note)
            else:
                # Check time gap from previous note
                prev_time = filtered_notes[-1][0]
                current_time = note[0]
                time_gap = current_time - prev_time
                
                # Also check if it's the same note (might be a duplicate)
                prev_note_name = filtered_notes[-1][1]
                prev_octave = filtered_notes[-1][2]
                current_note_name = note[1]
                current_octave = note[2]
                
                is_same_note = (prev_note_name == current_note_name and 
                               prev_octave == current_octave)
                
                # Keep note if:
                # 1. There's enough time gap, OR
                # 2. It's a different note (even if close in time - could be a chord or fast passage)
                if time_gap >= min_onset_gap or not is_same_note:
                    filtered_notes.append(note)
                # Otherwise, if it's the same note and too close, extend the previous note's duration instead
                elif is_same_note and time_gap < min_onset_gap:
                    # Extend previous note to cover this one
                    prev_note = filtered_notes[-1]
                    new_end_time = current_time + note[4]  # current note start + its duration
                    new_duration = new_end_time - prev_note[0]
                    extended_note = (prev_note[0], prev_note[1], prev_note[2], prev_note[3], new_duration)
                    filtered_notes[-1] = extended_note
        
        # Quantize note durations to standard musical values (improves readability in sheet music)
        quantized_notes = []
        for time, note_name, octave, freq, duration in filtered_notes:
            # Quantize duration to nearest standard note value
            # Standard durations in beats (assuming 4/4 time): whole=4.0, half=2.0, quarter=1.0, eighth=0.5, sixteenth=0.25
            # But we're working in seconds, so we need to consider tempo
            # For now, use standard durations in seconds (approximate for 120 BPM)
            standard_durations = [4.0, 2.0, 1.0, 0.5, 0.25, 0.125, 0.0625]
            quantized_duration = min(standard_durations, key=lambda x: abs(x - duration))
            
            # Don't make notes significantly shorter than original (preserve musical intent)
            if quantized_duration < duration * 0.7:  # If quantization makes it too short
                quantized_duration = duration  # Keep original
            
            quantized_notes.append((time, note_name, octave, freq, quantized_duration))
        
        return quantized_notes
    
    def _frequency_to_note(self, frequency: float) -> Tuple[Optional[str], Optional[int]]:
        """
        Convert frequency to note name and octave using accurate pitch calculation.
        
        Uses A4 = 440 Hz as reference. Returns note name (e.g., 'C', 'C#') and octave number.
        Octave 4 contains middle C (C4 = 261.63 Hz).
        
        Enhanced to handle octave calculation correctly and prevent low/grave notes.
        """
        if frequency <= 0:
            return None, None
        
        # Standard tuning: A4 = 440 Hz
        A4 = 440.0
        
        # Calculate semitones from A4
        # semitones = 12 * log2(freq / A4)
        semitones = 12 * np.log2(frequency / A4)
        semitones_rounded = round(semitones)
        
        # A4 is 9 semitones above C4 in the chromatic scale
        # So to get the note index: (semitones_from_A4 + 9) mod 12
        # This gives us: A4 -> 9, B4 -> 10, C5 -> 11, C#5 -> 0, etc.
        note_index = (semitones_rounded + 9) % 12
        
        # Calculate octave correctly
        # A4 is in octave 4, so: octave = 4 + floor((semitones + 9) / 12)
        # For negative numbers, we need to be careful with integer division
        semitones_from_C4 = semitones_rounded + 9
        
        # Use proper floor division that works for both positive and negative
        if semitones_from_C4 >= 0:
            octave = 4 + semitones_from_C4 // 12
        else:
            # For negative, we need to round down correctly
            # e.g., -1 should give octave 3, -13 should give octave 3, etc.
            octave = 4 + (semitones_from_C4 - 11) // 12
        
        # Validate and correct octave if it seems too low
        # Piano range is typically C1 (32.70 Hz) to C7 (2093 Hz) for most music
        # If we detect a note below C1, it might be a subharmonic - try octave higher
        if octave < 1 and frequency < 65.0:  # Below C2
            # Check if doubling the frequency gives a more reasonable note
            doubled_freq = frequency * 2.0
            if 32.0 <= doubled_freq <= 4186.0:  # Within piano range
                # Recalculate with doubled frequency
                semitones_doubled = 12 * np.log2(doubled_freq / A4)
                semitones_rounded_doubled = round(semitones_doubled)
                note_index = (semitones_rounded_doubled + 9) % 12
                semitones_from_C4_doubled = semitones_rounded_doubled + 9
                if semitones_from_C4_doubled >= 0:
                    octave = 4 + semitones_from_C4_doubled // 12
                else:
                    octave = 4 + (semitones_from_C4_doubled - 11) // 12
                frequency = doubled_freq  # Update frequency for validation
        
        # Validate octave range (piano range is roughly C0 to C8)
        # But filter out very low notes (below C1) unless they're clearly valid
        if octave < 0 or octave > 8:
            return None, None
        
        # Additional validation: if frequency is very low but octave is high, something's wrong
        # C1 = 32.70 Hz, so if frequency < 30 Hz and octave >= 1, it's likely wrong
        if frequency < 30.0 and octave >= 1:
            # Try one octave lower
            octave -= 1
            if octave < 0:
                return None, None
        
        note_name = self.NOTE_NAMES[note_index]
        return note_name, octave
    
    def _estimate_note_duration(self, f0_array: np.ndarray, start_idx: int, 
                               times: np.ndarray, hop_length: int, sr: int) -> float:
        """Estimate note duration by checking how long the frequency remains stable."""
        if start_idx >= len(f0_array) - 1:
            return 0.5
        
        start_freq = f0_array[start_idx]
        if np.isnan(start_freq):
            return 0.5
        
        duration_frames = 1
        tolerance = start_freq * 0.05  # 5% frequency tolerance
        
        for i in range(start_idx + 1, len(f0_array)):
            if np.isnan(f0_array[i]):
                break
            if abs(f0_array[i] - start_freq) <= tolerance:
                duration_frames += 1
            else:
                break
        
        duration_seconds = librosa.frames_to_time(duration_frames, sr=sr, hop_length=hop_length)
        return max(0.25, min(duration_seconds, 4.0))  # Clamp between 0.25 and 4 seconds
    
    def _estimate_note_duration_fast(self, f0_array: np.ndarray, start_idx: int, 
                                     times: np.ndarray, hop_length: int, sr: int) -> float:
        """Fast duration estimation - simplified version."""
        if start_idx >= len(times) - 1:
            return 0.5
        
        # Use fixed duration based on tempo (simplified)
        # Average note duration is roughly 0.5 seconds for most music
        return 0.5
    
    def _find_peaks(self, array: np.ndarray, threshold: float = 0.3) -> List[int]:
        """Find peaks in an array above threshold."""
        peaks = []
        for i in range(1, len(array) - 1):
            if array[i] > threshold and array[i] > array[i-1] and array[i] > array[i+1]:
                peaks.append(i)
        return peaks
    
    def notes_to_midi(self, notes: List[Tuple[float, str, int, float, float]], 
                     output_path: str, tempo: int = 120) -> bool:
        """
        Convert extracted notes to MIDI file.
        
        Args:
            notes: List of (time, note_name, octave, frequency, duration) tuples
            output_path: Path to save MIDI file
            tempo: Tempo in BPM
            
        Returns:
            True if successful
        """
        if not MIDIUTIL_AVAILABLE:
            raise ImportError("midiutil is required. Install with: pip install midiutil")
        
        try:
            midi = MIDIFile(1)
            track = 0
            channel = 0
            volume = 100
            
            midi.addTempo(track, 0, tempo)
            
            note_to_midi = {
                'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
                'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11
            }
            
            for time_sec, note_name, octave, freq, duration in notes:
                # Final validation: skip notes that are extremely low (likely subharmonics)
                # Most piano music is in octave 1-7 range
                # C1 = MIDI note 24, C7 = MIDI note 108
                # Notes below C1 are very rare and likely subharmonics
                if octave < 1:
                    # Skip extremely low notes (below C1) - they're almost certainly subharmonics
                    continue
                if octave > 7:
                    # Skip very high notes (above C7) - they're likely harmonics
                    continue
                
                # Convert time from seconds to beats (MIDI uses beats, where 1 beat = 1 quarter note at the given tempo)
                time_beat = (time_sec * tempo) / 60.0
                
                # Calculate MIDI note number (0-127)
                # MIDI note calculation: C4 (middle C) = 60
                # Formula: (octave + 1) * 12 + note_offset
                # For C4 (octave=4, C=0): (4+1)*12 + 0 = 60 ✓
                # For C2 (octave=2, C=0): (2+1)*12 + 0 = 36 ✓
                # For C1 (octave=1, C=0): (1+1)*12 + 0 = 24 ✓
                midi_note = (octave + 1) * 12 + note_to_midi[note_name]
                
                # Clamp MIDI note to valid range (0-127)
                # Ensure it's in a reasonable piano range (C1 to C7 = 24 to 108)
                midi_note = max(24, min(108, int(midi_note)))  # Clamp to C1-C7 range
                
                # Convert duration from seconds to beats
                # Duration in beats = (duration_seconds * tempo_bpm) / 60
                duration_beat = (duration * tempo) / 60.0
                
                # Ensure minimum duration of 1/16th note (0.25 beats) for readability
                # But don't make it too long if the original was very short
                duration_beat = max(0.125, min(duration_beat, 16.0))  # Clamp between 1/8th note and 4 whole notes
                
                # Only add note if time and duration are valid
                if time_beat >= 0 and duration_beat > 0:
                    midi.addNote(track, channel, midi_note, time_beat, duration_beat, volume)
            
            with open(output_path, "wb") as f:
                midi.writeFile(f)
            
            return True
        except Exception as e:
            raise Exception(f"Error creating MIDI file: {e}")
    
    def midi_to_audio(self, midi_path: str, output_audio_path: str, 
                     sr: int = 22050, instrument: int = 0) -> bool:
        """
        Convert MIDI file to audio using pretty_midi.
        
        Args:
            midi_path: Path to MIDI file
            output_audio_path: Path to save audio file
            sr: Sample rate for output audio
            instrument: MIDI instrument number (0 = Acoustic Grand Piano)
            
        Returns:
            True if successful
        """
        if not PRETTY_MIDI_AVAILABLE:
            raise ImportError("pretty_midi is required. Install with: pip install pretty_midi")
        
        try:
            # Load MIDI file
            midi_data = pretty_midi.PrettyMIDI(midi_path)
            
            # Synthesize to audio using fluidsynth
            # Note: This requires fluidsynth library to be available
            # pretty_midi will use fluidsynth if available, otherwise it may raise an error
            audio = midi_data.fluidsynth(fs=sr)
            
            # Normalize
            if np.max(np.abs(audio)) > 0:
                audio = audio / np.max(np.abs(audio))
            
            # Save as WAV
            sf.write(output_audio_path, audio, sr)
            
            return True
        except Exception as e:
            # Provide helpful error message
            error_msg = str(e)
            if 'fluidsynth' in error_msg.lower() or 'soundfont' in error_msg.lower():
                raise Exception(
                    f"MIDI synthesis failed: {error_msg}\n\n"
                    "💡 Tip: For better MIDI-to-audio synthesis, you may need to install fluidsynth.\n"
                    "On Windows: Download fluidsynth from https://www.fluidsynth.org/\n"
                    "On Linux: sudo apt-get install fluidsynth\n"
                    "On macOS: brew install fluidsynth"
                )
            else:
                raise Exception(f"Error synthesizing MIDI to audio: {e}")
    
    def midi_to_musicxml(self, midi_path: str, musicxml_path: str) -> bool:
        """
        Convert MIDI file to MusicXML using music21.
        
        Args:
            midi_path: Path to input MIDI file
            musicxml_path: Path to save MusicXML file
            
        Returns:
            True if successful
        """
        if not MUSIC21_AVAILABLE:
            raise ImportError("music21 is required for MIDI to MusicXML conversion")
        
        try:
            # Parse MIDI file with music21
            midi_stream = music21.converter.parse(midi_path)
            
            # Ensure it's a Score object
            if not isinstance(midi_stream, music21.stream.Score):
                # If it's a Stream, wrap it in a Score
                score = music21.stream.Score()
                score.append(midi_stream)
                midi_stream = score
            
            # Preserve tempo from MIDI
            # music21 should automatically extract tempo, but we can ensure it's set
            if hasattr(midi_stream, 'metronomeMarkBoundaries'):
                # Tempo should be preserved from MIDI
                pass
            
            # Add metadata if not present
            if not midi_stream.metadata:
                midi_stream.metadata = music21.metadata.Metadata()
                midi_stream.metadata.title = "Piano Sheet Music"
            
            # Quantize notes for better readability
            # This rounds note durations to standard note values
            try:
                midi_stream = midi_stream.quantize(quarterLengthDivisors=[4, 3], inPlace=False)
            except:
                # If quantization fails, continue without it
                pass
            
            # Export to MusicXML
            midi_stream.write('musicxml', fp=musicxml_path)
            
            return True
        except Exception as e:
            raise Exception(f"Error converting MIDI to MusicXML: {e}")
    
    def musicxml_to_pdf(self, musicxml_path: str, pdf_path: str, musescore_path: Optional[str] = None) -> bool:
        """
        Convert MusicXML file to PDF using MuseScore command-line.
        
        Args:
            musicxml_path: Path to input MusicXML file
            pdf_path: Path to save PDF file
            musescore_path: Path to MuseScore executable (default: auto-detect)
            
        Returns:
            True if successful
        """
        # Default MuseScore path (Windows)
        if musescore_path is None:
            musescore_path = r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"
        
        # Check if MuseScore exists
        if not os.path.exists(musescore_path):
            raise FileNotFoundError(
                f"MuseScore not found at: {musescore_path}\n"
                "Please install MuseScore 4 or specify the correct path."
            )
        
        # Check if input file exists
        if not os.path.exists(musicxml_path):
            raise FileNotFoundError(f"MusicXML file not found: {musicxml_path}")
        
        try:
            # Run MuseScore command-line: MuseScore4.exe input.musicxml -o output.pdf -f
            # -f flag forces overwrite
            cmd = [
                musescore_path,
                musicxml_path,
                "-o", pdf_path,
                "-f"
            ]
            
            # Run the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            # Check if PDF was created
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                return True
            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                raise Exception(f"MuseScore conversion failed: {error_msg}")
                
        except subprocess.TimeoutExpired:
            raise Exception("MuseScore conversion timed out after 60 seconds")
        except Exception as e:
            raise Exception(f"Error converting MusicXML to PDF: {e}")
    
    def generate_sheet_music_pdf(self, notes: List[Tuple[float, str, int, float, float]], 
                                 output_path: str, title: str = "Piano Sheet Music") -> bool:
        """
        Generate sheet music PDF from extracted notes using music21.
        DEPRECATED: Use midi_to_pdf_workflow instead for better results.
        
        Args:
            notes: List of (time, note_name, octave, frequency, duration) tuples
            output_path: Path to save PDF
            title: Title for the sheet music
            
        Returns:
            True if successful
        """
        if not MUSIC21_AVAILABLE:
            # Fallback to simple PDF
            return self._generate_simple_sheet_pdf(notes, output_path, title)
        
        try:
            # Create a music21 stream
            stream = music21.stream.Stream()
            stream.metadata = music21.metadata.Metadata()
            stream.metadata.title = title
            
            # Group notes by time to create chords
            from collections import defaultdict
            notes_by_time = defaultdict(list)
            
            for time, note_name, octave, freq, duration in notes:
                # Round time to nearest 16th note for cleaner sheet music
                rounded_time = round(time * 4) / 4
                notes_by_time[rounded_time].append((note_name, octave, duration))
            
            # Convert to music21 notes
            current_time = 0.0
            for time in sorted(notes_by_time.keys()):
                time_beat = time * 4  # Convert to quarter notes
                
                if time_beat > current_time:
                    # Add rest if there's a gap
                    rest_duration = time_beat - current_time
                    rest = music21.note.Rest(quarterLength=rest_duration)
                    stream.append(rest)
                    current_time = time_beat
                
                # Get notes at this time
                note_data = notes_by_time[time]
                
                if len(note_data) == 1:
                    # Single note
                    note_name, octave, duration = note_data[0]
                    note = music21.note.Note(f"{note_name}{octave}")
                    note.quarterLength = max(0.25, duration * 4)  # Convert to quarter notes
                    stream.append(note)
                    current_time += note.quarterLength
                else:
                    # Chord
                    chord_notes = []
                    max_duration = max(d[2] for d in note_data)
                    for note_name, octave, duration in note_data:
                        chord_notes.append(music21.note.Note(f"{note_name}{octave}"))
                    chord = music21.chord.Chord(chord_notes)
                    chord.quarterLength = max(0.25, max_duration * 4)
                    stream.append(chord)
                    current_time += chord.quarterLength
            
            # Generate PDF
            stream.write('musicxml.pdf', fp=output_path)
            
            return True
        except Exception as e:
            # Fallback to simple PDF if music21 fails
            print(f"Warning: music21 PDF generation failed: {e}. Using simple PDF.")
            return self._generate_simple_sheet_pdf(notes, output_path, title)
    
    def midi_to_pdf_workflow(self, midi_path: str, pdf_path: str, 
                             musescore_path: Optional[str] = None,
                             tempo: int = 120) -> bool:
        """
        Complete workflow: MIDI → MusicXML → PDF using music21 and MuseScore.
        
        Step 1: Parse MIDI with music21
        Step 2: Convert to MusicXML (preserving tempo, key signature, time signature)
        Step 3: Quantize notes for readability
        Step 4: Convert MusicXML to PDF via MuseScore
        
        Args:
            midi_path: Path to input MIDI file
            pdf_path: Path to save PDF file
            musescore_path: Path to MuseScore executable (default: auto-detect)
            tempo: Tempo in BPM (for metadata)
            
        Returns:
            True if successful
        """
        if not MUSIC21_AVAILABLE:
            raise ImportError("music21 is required for MIDI to PDF conversion")
        
        try:
            # Step 1: Parse MIDI with music21
            midi_stream = music21.converter.parse(midi_path)
            
            # Ensure it's a Score object
            if not isinstance(midi_stream, music21.stream.Score):
                score = music21.stream.Score()
                score.append(midi_stream)
                midi_stream = score
            
            # Step 2: Preserve and set metadata (tempo, key signature, time signature)
            if not midi_stream.metadata:
                midi_stream.metadata = music21.metadata.Metadata()
                midi_stream.metadata.title = "Piano Sheet Music"
            
            # Add tempo if not present
            tempo_found = False
            for element in midi_stream.flat:
                if isinstance(element, music21.tempo.MetronomeMark):
                    tempo_found = True
                    break
            
            if not tempo_found:
                # Add tempo mark
                mm = music21.tempo.MetronomeMark(number=tempo)
                midi_stream.insert(0, mm)
            
            # Step 3: Quantize notes for readability
            # This rounds note durations to standard note values (quarter, eighth, etc.)
            try:
                midi_stream = midi_stream.quantize(
                    quarterLengthDivisors=[4, 3],  # Allow quarter, eighth, sixteenth, triplets
                    inPlace=False
                )
            except Exception as quantize_error:
                # If quantization fails, continue without it
                print(f"Warning: Quantization failed: {quantize_error}. Continuing without quantization.")
            
            # Create temporary MusicXML file
            temp_dir = os.path.dirname(pdf_path)
            musicxml_path = os.path.join(temp_dir, os.path.splitext(os.path.basename(pdf_path))[0] + ".musicxml")
            
            # Step 4: Export to MusicXML
            midi_stream.write('musicxml', fp=musicxml_path)
            
            # Step 5: Convert MusicXML to PDF via MuseScore
            self.musicxml_to_pdf(musicxml_path, pdf_path, musescore_path)
            
            # Clean up temporary MusicXML file (optional - can keep for debugging)
            try:
                if os.path.exists(musicxml_path):
                    os.remove(musicxml_path)
            except:
                pass  # Don't fail if cleanup fails
            
            return True
            
        except Exception as e:
            raise Exception(f"Error in MIDI to PDF workflow: {e}")
    
    def _generate_simple_sheet_pdf(self, notes: List[Tuple[float, str, int, float, float]], 
                                  output_path: str, title: str) -> bool:
        """Generate a simple text-based sheet music PDF."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF generation")
        
        try:
            c = canvas.Canvas(output_path, pagesize=letter)
            width, height = letter
            margin = 0.75 * inch
            y = height - margin
            
            # Title
            c.setFont("Helvetica-Bold", 20)
            c.drawString(margin, y, title)
            y -= 0.5 * inch
            
            # Instructions
            c.setFont("Helvetica", 10)
            c.drawString(margin, y, "Piano Notes Extracted from Audio")
            y -= 0.4 * inch
            
            # Group notes by measure (4 beats = 1 measure at 120 BPM)
            from collections import defaultdict
            measures = defaultdict(list)
            
            for time, note_name, octave, freq, duration in notes:
                measure_num = int(time // 2.0)  # 2 seconds per measure at 120 BPM
                measures[measure_num].append((time, note_name, octave, duration))
            
            # Draw staff lines and notes
            staff_y = y
            staff_height = 2 * inch
            line_spacing = 0.2 * inch
            
            # Draw staff
            for i in range(5):
                line_y = staff_y - (i * line_spacing)
                c.line(margin, line_y, width - margin, line_y)
            
            y = staff_y - staff_height - 0.3 * inch
            
            # Draw notes
            c.setFont("Helvetica", 9)
            for measure_num in sorted(measures.keys()):
                if y < margin:
                    c.showPage()
                    y = height - margin
                    c.setFont("Helvetica-Bold", 20)
                    c.drawString(margin, y, title)
                    y -= 0.3 * inch
                    c.setFont("Helvetica", 9)
                
                measure_notes = measures[measure_num]
                x = margin + (measure_num % 4) * 2 * inch
                
                for time, note_name, octave, duration in measure_notes:
                    note_text = f"{note_name}{octave} ({duration:.2f}s)"
                    c.drawString(x, y, note_text)
                    y -= 0.15 * inch
            
            c.showPage()
            c.save()
            return True
        except Exception as e:
            raise Exception(f"Error creating simple PDF: {e}")
    
    def process_audio_to_piano_sheet(self, audio_path: str, output_dir: str,
                                    tempo: int = 120,
                                    max_duration: Optional[float] = 60.0,
                                    callback: Optional[Callable[[int, str], None]] = None) -> Dict[str, str]:
        """
        Complete workflow: Extract piano → Generate MIDI → Generate PDF → Synthesize audio.
        Optimized for speed.
        
        Args:
            audio_path: Path to input audio file
            output_dir: Directory for output files
            tempo: Tempo in BPM
            max_duration: Maximum duration in seconds to process (None = full file, 60 = first minute)
            callback: Optional callback function(step, message) for progress updates
            
        Returns:
            Dictionary with paths to generated files:
            {
                'piano_audio': path to extracted piano audio,
                'midi': path to MIDI file,
                'pdf': path to sheet music PDF,
                'synthesized_audio': path to synthesized MIDI audio
            }
        """
        os.makedirs(output_dir, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        
        # Step 1: Extract piano from audio (optimized)
        if callback:
            callback(1, "Extracting piano from mixed audio...")
        piano_audio, sr = self.extract_piano_from_audio(audio_path, max_duration=max_duration)
        piano_audio_path = os.path.join(output_dir, f"{base_name}_piano.wav")
        sf.write(piano_audio_path, piano_audio, sr)
        
        # Step 2: Extract notes (optimized)
        if callback:
            callback(2, "Extracting musical notes...")
        notes = self.extract_notes_from_piano_audio(piano_audio, sr)
        
        if not notes:
            raise Exception("No notes extracted from audio. Please check the audio file.")
        
        # Step 3: Generate MIDI
        if callback:
            callback(3, "Generating MIDI file...")
        midi_path = os.path.join(output_dir, f"{base_name}_piano.mid")
        self.notes_to_midi(notes, midi_path, tempo=tempo)
        
        # Step 4: Generate PDF using MIDI → MusicXML → PDF workflow
        if callback:
            callback(4, "Generating sheet music PDF...")
        pdf_path = os.path.join(output_dir, f"{base_name}_sheet_music.pdf")
        
        # Use the new MIDI → PDF workflow (MIDI → MusicXML → PDF via MuseScore)
        try:
            # Try the new workflow first
            self.midi_to_pdf_workflow(midi_path, pdf_path, tempo=tempo)
        except Exception as e:
            # Fallback to old method if new workflow fails
            print(f"Warning: MIDI → PDF workflow failed: {e}. Trying fallback method.")
            try:
                self.generate_sheet_music_pdf(notes, pdf_path, title=f"Piano Sheet Music - {base_name}")
            except Exception as e2:
                # Final fallback to simple PDF
                print(f"Warning: Advanced PDF generation failed, using simple PDF: {e2}")
                self._generate_simple_sheet_pdf(notes, pdf_path, f"Piano Sheet Music - {base_name}")
        
        # Step 5: Synthesize MIDI to audio (optional - can be skipped if too slow)
        synthesized_audio_path = None
        try:
            if callback:
                callback(5, "Synthesizing MIDI to audio...")
            synthesized_audio_path = os.path.join(output_dir, f"{base_name}_synthesized.wav")
            self.midi_to_audio(midi_path, synthesized_audio_path, sr=sr)
        except Exception as e:
            print(f"Warning: MIDI synthesis failed (optional step): {e}")
            synthesized_audio_path = None
        
        return {
            'piano_audio': piano_audio_path,
            'midi': midi_path,
            'pdf': pdf_path,
            'synthesized_audio': synthesized_audio_path,
            'notes_count': len(notes)
        }

