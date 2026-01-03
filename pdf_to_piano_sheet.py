import re
from typing import List, Tuple
from PyPDF2 import PdfReader

from music21 import environment
us = environment.UserSettings()
us['musicxmlPath'] = r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"
us['musescoreDirectPNGPath'] = r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"

from music21 import stream, note, tempo, meter, clef, key

# ------------------------------
# CONFIGURATION
# ------------------------------

PDF_INPUT_PATH = "./input_notes/input_notes.pdf"    # <-- change this to your input PDF path
PDF_OUTPUT_PATH = "./output_sheet/output_sheet.pdf"  # <-- this will be the generated pianist-ready sheet

FRAME_SECONDS = 0.50   # each detection frame duration in seconds (0.50s in your PDF)
BPM = 120              # assumed tempo; adjust to match the original song

# ------------------------------
# STEP 1: PARSE PDF INTO NOTE EVENTS
# ------------------------------

NOTE_LINE_RE = re.compile(
    r"^\s*([A-Ga-g])(#|b)?(\d)\s*\((\d+\.\d+)s\)\s*$"
)

def parse_pdf_to_notes(pdf_path: str) -> List[Tuple[str, float]]:
    """
    Read the PDF and extract a list of (pitch_name, duration_seconds) tuples.
    Example output: [("A3", 0.5), ("A3", 0.5), ("C#5", 0.5), ...]
    """
    reader = PdfReader(pdf_path)
    events: List[Tuple[str, float]] = []

    for page in reader.pages:
        text = page.extract_text() or ""
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            m = NOTE_LINE_RE.match(line)
            if not m:
                # Ignore non-note lines (titles, blank lines, etc.)
                continue
            letter, accidental, octave, dur_str = m.groups()
            pitch_name = letter.upper()
            if accidental:
                pitch_name += accidental
            pitch_name += octave
            duration_seconds = float(dur_str)
            events.append((pitch_name, duration_seconds))
    if not events:
        raise ValueError("No note events found in the PDF. Check the format or regex.")
    return events

# ------------------------------
# STEP 2: MERGE REPEATED NOTES INTO LONGER DURATIONS
# ------------------------------

def merge_repeated_notes(events: List[Tuple[str, float]]) -> List[Tuple[str, int]]:
    """
    Merge consecutive identical notes into a single (pitch_name, frame_count).
    We assume every event uses the same frame duration (FRAME_SECONDS).
    """
    if not events:
        return []

    merged: List[Tuple[str, int]] = []
    current_pitch, current_frames = events[0][0], 1

    for pitch_name, dur in events[1:]:
        # Sanity check: durations should all equal FRAME_SECONDS
        if abs(dur - FRAME_SECONDS) > 1e-3:
            raise ValueError(
                f"Unexpected frame duration {dur} (expected {FRAME_SECONDS}). "
                "Check the input PDF or FRAME_SECONDS."
            )
        if pitch_name == current_pitch:
            current_frames += 1
        else:
            merged.append((current_pitch, current_frames))
            current_pitch, current_frames = pitch_name, 1

    merged.append((current_pitch, current_frames))
    return merged

# ------------------------------
# STEP 3: CONVERT TO A MUSIC21 SCORE
# ------------------------------

def build_score_from_merged(merged: List[Tuple[str, int]]) -> stream.Score:
    """
    Convert merged (pitch_name, frame_count) into a music21 Score with
    quantized durations based on FRAME_SECONDS and BPM.
    """
    if not merged:
        raise ValueError("Merged notes list is empty.")

    seconds_per_beat = 60.0 / BPM
    frames_per_beat = max(1, round(seconds_per_beat / FRAME_SECONDS))

    sc = stream.Score()
    part = stream.Part()
    sc.insert(0, part)

    # Basic metadata: tempo, time signature, clef, key
    part.append(tempo.MetronomeMark(number=BPM))
    part.append(meter.TimeSignature("4/4"))
    part.append(clef.TrebleClef())
    # Neutral key (C major / A minor). You can change this later if needed.
    part.append(key.KeySignature(0))

    for pitch_name, frame_count in merged:
        # Convert frames to beats, then to quarterLength
        beats = frame_count / frames_per_beat
        ql = beats  # in 4/4, 1 beat = quarter note => quarterLength = beats

        # Skip any pathological tiny durations
        if ql <= 0:
            continue

        n = note.Note(pitch_name)
        n.quarterLength = ql
        part.append(n)

    return sc

# ------------------------------
# STEP 4: END-TO-END CONVERSION
# ------------------------------

def convert_pdf_notes_to_piano_sheet(
    input_pdf: str = PDF_INPUT_PATH,
    output_pdf: str = PDF_OUTPUT_PATH,
) -> None:
    """
    Full pipeline:
      1. Read raw notes from input PDF
      2. Merge repeated frames into longer notes
      3. Build a music21 Score
      4. Write it out as a PDF of sheet music (requires MuseScore/LilyPond configured)
    """
    # 1) Parse
    events = parse_pdf_to_notes(input_pdf)

    # 2) Merge repeated
    merged = merge_repeated_notes(events)

    # 3) Build score
    sc = build_score_from_merged(merged)

    # 4) Export to PDF
    # music21 uses your default musicxml-to-pdf converter (MuseScore, etc.).
    # Make sure environment is configured (see music21 docs: environment.set()).
    sc.write("musicxml.pdf", fp=output_pdf)
    print(f"Written cleaned piano sheet to: {output_pdf}")

if __name__ == "__main__":
    convert_pdf_notes_to_piano_sheet()
