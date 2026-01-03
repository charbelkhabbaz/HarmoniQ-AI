# Piano Extraction Tool - Technical Explanation

## Overview

The Piano Extraction tool is a sophisticated audio processing feature within HarmoniQ AI that isolates piano audio from mixed audio tracks, extracts musical notes, and automatically generates professional sheet music. The processing pipeline transforms raw audio files into structured musical notation, producing MIDI files, sheet music PDFs, and synthesized audio outputs. This tool demonstrates advanced signal processing techniques including source separation, pitch detection, and automated music transcription.

## Architecture & Workflow

The Piano Extraction tool operates through a multi-stage processing pipeline that transforms mixed audio into formatted sheet music with multiple output formats.

### Stage 1: Piano Audio Isolation

**Technology:** `librosa` (Audio Analysis Library) - Harmonic-Percussive Source Separation (HPSS) + Spectral Filtering

The tool first separates piano audio from mixed audio containing vocals, drums, and other instruments:

#### 1.1 Audio Loading & Preprocessing
- **Sample Rate Optimization:** Loads audio at 16kHz sample rate for computational efficiency (lower = faster processing)
- **Stereo Preservation:** Maintains stereo channels if available for enhanced vocal removal
- **Duration Limiting:** Optionally processes only first 60 seconds (default) or full file for performance optimization

#### 1.2 Source Separation Techniques

**For Stereo Audio:**
- **Harmonic Component Extraction:** Uses HPSS (Harmonic-Percussive Source Separation) with margin=8.0 to extract harmonic components from left and right channels separately
- **Vocal Cancellation Algorithm:** 
  - Vocals are typically centered (identical in L and R channels)
  - Piano is often panned (different in L and R channels)
  - Calculates difference channel: `y_diff = y_harmonic_l - y_harmonic_r` (removes centered vocals, keeps panned instruments)
  - Calculates sum channel: `y_sum = (y_harmonic_l + y_harmonic_r) / 2`
  - Blends signals: `y = 0.8 * y_diff + 0.2 * y_sum` (prefer difference for vocal removal, keep sum for fullness)

**For Mono Audio:**
- **HPSS Separation:** Separates harmonic (piano) from percussive (drums/vocals) components
- **Harmonic Selection:** Piano is primarily harmonic; vocals contain more percussive/transient elements
- **Output:** Uses only harmonic component (`y = y_harmonic`)

#### 1.3 Frequency-Domain Filtering

**Short-Time Fourier Transform (STFT) Analysis:**
- Converts time-domain audio to frequency domain using STFT
- Parameters: hop_length=1024, frame_length=2048 (optimized for speed)
- Extracts magnitude spectrum and phase information

**Piano Frequency Range Masking:**
- **Piano Range:** 27.5 Hz (A0 - lowest piano note) to 4186 Hz (C8 - highest piano note)
- Creates frequency mask: `piano_mask = (frequencies >= 27.5) & (frequencies <= 4186)`

**Vocal Frequency Suppression:**
- **Vocal Fundamentals:** 80-300 Hz range (male: 85-180 Hz, female: 165-255 Hz)
- Creates inverse mask: `vocal_mask = ~((frequencies >= 80) & (frequencies <= 300))`
- **Spectral Subtraction:** Reduces energy in vocal range by 90-95%
  - Non-piano frequencies: multiplied by 0.1 (90% reduction)
  - Vocal fundamental range: multiplied by 0.05 (95% reduction)

**Harmonic Enhancement:**
- Detects and enhances harmonic relationships (2nd, 3rd, 4th harmonics)
- Piano characteristics: clear harmonic structure with multiple overtones
- Multiplies strong harmonic components by 1.2x to emphasize piano characteristics

#### 1.4 Time-Domain Post-Processing

**Inverse STFT:**
- Converts filtered frequency-domain signal back to time domain
- Reconstructs audio using modified magnitude and original phase

**Transient Smoothing:**
- Applies 10ms moving average window to reduce vocal-like transients
- Blends smoothed signal: `y_filtered = 0.8 * y_filtered + 0.2 * y_smooth`

**Audio Normalization:**
- Normalizes peak amplitude to prevent clipping
- Formula: `y_normalized = y / max(|y|)`

**Output:** Clean piano-only audio signal as numpy array with sample rate

---

### Stage 2: Musical Note Extraction

**Technology:** `librosa.pyin()` (Probabilistic YIN Pitch Detection) + Frequency-to-Note Conversion

The isolated piano audio is analyzed to detect individual musical notes with timing information:

#### 2.1 Pitch Detection Algorithm

**Probabilistic YIN (PYIN) Method:**
- Advanced pitch detection algorithm optimized for polyphonic music
- Parameters: fmin=60 Hz, fmax=2000 Hz (avoid subharmonics and harmonics)
- **Frame Analysis:** Processes audio in overlapping frames
  - hop_length=1024 samples (larger = faster)
  - frame_length=2048 samples
  - n_thresholds=50 (reduced from 100 for speed optimization)

**Output:** 
- `f0`: Array of fundamental frequencies (Hz) for each frame
- `voiced_flag`: Boolean array indicating voiced (musical) vs unvoiced (noise) frames
- `voiced_probs`: Probability estimates for voicing decisions

#### 2.2 Frequency-to-Note Conversion

**Musical Note Mapping Algorithm:**
- **Reference Frequency:** A4 = 440 Hz (standard tuning)
- **Formula:** Calculates semitones from A4: `semitones = 12 * log₂(freq / 440)`
- **Note Index Calculation:** Maps to 12-note chromatic scale (C, C#, D, D#, E, F, F#, G, G#, A, A#, B)
- **Octave Calculation:**
  - Formula: `octave = 4 + floor((semitones + 9) / 12)`
  - C4 (middle C) = 261.63 Hz serves as reference point
  - Handles negative semitones correctly for notes below A4

**Subharmonic Detection & Correction:**
- Filters out notes below C1 (octave 1) - likely subharmonics
- Attempts octave correction by doubling frequency if subharmonic detected
- Validates corrected frequency falls within valid range (C1 to C7)

#### 2.3 Note Onset Detection & Merging

**Consecutive Frame Analysis:**
- Tracks note continuity across frames
- Detects note onsets (new notes starting)
- Merges consecutive frames of same note into single note event

**Frequency Stability Check:**
- Uses 50-cent tolerance (approximately 3% frequency difference) to determine same note
- Formula: `cents_diff = 1200 * log₂(freq₁ / freq₂)`
- If frequency within 50 cents and same note name/octave → continues current note

**Duration Estimation:**
- Calculates note duration from onset to offset (silence or new note)
- Minimum note duration: 100ms (filters out noise/artifacts)

#### 2.4 Note Filtering & Quantization

**Duplicate Filtering:**
- Removes notes that are too close together (< 50ms gap) and identical
- If same note detected within 50ms → extends previous note duration instead of creating duplicate

**Duration Quantization:**
- Rounds note durations to standard musical values:
  - Whole note = 4.0 beats
  - Half note = 2.0 beats
  - Quarter note = 1.0 beat
  - Eighth note = 0.5 beats
  - Sixteenth note = 0.25 beats
- Preserves musical intent (won't shorten notes by more than 30%)

**Output:** List of note tuples: `(time_seconds, note_name, octave, frequency_hz, duration_seconds)`
- Example: `(0.5, 'C', 4, 261.63, 0.5)` = Middle C starting at 0.5s, duration 0.5s

---

### Stage 3: MIDI File Generation

**Technology:** `midiutil` (MIDI File Creation Library)

Extracted notes are converted into standard MIDI format for compatibility with music software:

#### 3.1 MIDI File Structure

**Track Creation:**
- Creates single-track MIDI file
- Sets tempo metadata (default: 120 BPM, range: 60-180 BPM)
- Configures channel 0 with volume 100

#### 3.2 Note-to-MIDI Mapping

**MIDI Note Number Calculation:**
- **Formula:** `midi_note = (octave + 1) * 12 + note_offset`
- **Examples:**
  - C4 (middle C) = (4+1)*12 + 0 = 60
  - C2 = (2+1)*12 + 0 = 36
  - C1 = (1+1)*12 + 0 = 24
- **Range Validation:** Clamps to valid piano range (C1-C7 = MIDI notes 24-108)

**Time Conversion:**
- Converts seconds to beats: `time_beats = (time_seconds * tempo_bpm) / 60`
- Converts duration to beats: `duration_beats = (duration_seconds * tempo_bpm) / 60`
- **Duration Clamping:** Ensures minimum 1/8th note (0.125 beats), maximum 4 whole notes (16 beats)

#### 3.3 MIDI File Output

**File Structure:**
- Standard MIDI format (.mid file)
- Contains tempo track, note events with timing and duration
- Compatible with all MIDI software and hardware

**Output:** Standard MIDI file (.mid) with all extracted notes in musical time

---

### Stage 4: Sheet Music PDF Generation

**Technology:** `music21` (Music Analysis Library) + MuseScore (Sheet Music Renderer)

MIDI files are converted to professional sheet music notation:

#### 4.1 MIDI to MusicXML Conversion

**music21 Parsing:**
- Loads MIDI file using `music21.converter.parse()`
- Converts MIDI events to music21 Score objects
- Preserves tempo, timing, and note information

**Score Organization:**
- Creates proper Score structure if MIDI doesn't contain one
- Adds metadata (title, composer information)
- Inserts tempo markings if missing (MetronomeMark objects)

**Quantization:**
- Rounds note durations to standard musical values for readability
- Parameters: `quarterLengthDivisors=[4, 3]` (allows quarter, eighth, sixteenth notes, triplets)
- Improves sheet music readability while preserving musical intent

**MusicXML Export:**
- Converts music21 Score to MusicXML format
- MusicXML is standard XML format for music notation
- Preserves all musical information (notes, timing, dynamics, etc.)

#### 4.2 MusicXML to PDF Rendering

**MuseScore Command-Line Integration:**
- Uses MuseScore 4 executable for professional rendering
- Command format: `MuseScore4.exe input.musicxml -o output.pdf -f`
- Flags: `-f` forces overwrite, `-o` specifies output path

**Rendering Process:**
- MuseScore reads MusicXML file
- Renders professional-quality sheet music with proper formatting:
  - Staff lines and clefs
  - Note heads, stems, and beams
  - Time signatures and key signatures
  - Proper spacing and layout
- Generates PDF document (60-second timeout)

**Fallback Mechanisms:**
- If MuseScore unavailable: Falls back to music21's built-in PDF generator
- If music21 fails: Uses simple PDF generator with basic note representation
- Ensures PDF generation always succeeds, though quality may vary

**Output:** Professional sheet music PDF file with formatted musical notation

---

### Stage 5: MIDI Synthesis to Audio (Optional)

**Technology:** `pretty_midi` + `fluidsynth` (Sound Synthesis)

MIDI file is synthesized back to audio for playback verification:

#### 5.1 MIDI Loading

**pretty_midi Parsing:**
- Loads MIDI file structure
- Extracts all note events, timing, and instrument information

#### 5.2 Audio Synthesis

**FluidSynth Integration:**
- Uses FluidSynth library for sound synthesis
- Requires soundfont file (instrument samples)
- Default instrument: Acoustic Grand Piano (MIDI program 0)
- Sample rate: 22050 Hz

**Synthesis Process:**
- Converts MIDI note events to audio samples
- Applies instrument timbre from soundfont
- Handles note timing and velocity (volume)

**Audio Normalization:**
- Normalizes peak amplitude to prevent clipping
- Formula: `audio_normalized = audio / max(|audio|)`

**Output:** Synthesized WAV audio file matching the extracted MIDI

---

## Complete Workflow Summary

```
Mixed Audio File (MP3/WAV/FLAC)
    ↓
[Stage 1] Piano Isolation
    ├─ HPSS Source Separation
    ├─ Frequency Filtering (27.5-4186 Hz)
    ├─ Vocal Suppression (80-300 Hz)
    └─ Harmonic Enhancement
    ↓
Piano-only Audio (WAV)
    ↓
[Stage 2] Note Extraction
    ├─ PYIN Pitch Detection
    ├─ Frequency-to-Note Conversion
    ├─ Onset Detection & Merging
    └─ Duration Quantization
    ↓
List of Notes (time, note, octave, frequency, duration)
    ↓
[Stage 3] MIDI Generation
    ├─ Note-to-MIDI Mapping
    ├─ Time Conversion (seconds → beats)
    └─ MIDI File Creation
    ↓
MIDI File (.mid)
    ↓
[Stage 4] PDF Generation
    ├─ MIDI → MusicXML (music21)
    ├─ Quantization
    └─ MusicXML → PDF (MuseScore)
    ↓
Sheet Music PDF
    ↓
[Stage 5] Audio Synthesis (Optional)
    └─ MIDI → Audio (FluidSynth)
    ↓
Synthesized Audio (WAV)
```

## Key Technologies Used

1. **librosa**: Audio signal processing, HPSS, STFT, pitch detection (PYIN)
2. **NumPy**: Numerical computations, array operations
3. **midiutil**: MIDI file creation and manipulation
4. **music21**: Music analysis, MIDI parsing, MusicXML conversion
5. **MuseScore 4**: Professional sheet music rendering engine
6. **pretty_midi**: MIDI file processing and synthesis
7. **fluidsynth**: Sound synthesis (optional, requires external library)
8. **soundfile**: Audio file I/O operations

## Technical Features

### 1. Advanced Source Separation
- Harmonic-Percussive Source Separation (HPSS) for instrument isolation
- Stereo-based vocal cancellation using phase difference
- Frequency-domain filtering with spectral subtraction

### 2. Robust Pitch Detection
- Probabilistic YIN (PYIN) algorithm optimized for polyphonic music
- Subharmonic detection and correction
- Octave validation and range filtering

### 3. Intelligent Note Processing
- Note onset detection with frequency stability analysis
- Consecutive note merging to prevent duplicates
- Duration quantization to standard musical values
- Minimum duration filtering to remove noise

### 4. Professional Output Generation
- Standard MIDI format for universal compatibility
- Professional sheet music PDF via MuseScore
- Multiple fallback mechanisms for reliability
- Synthesized audio for playback verification

### 5. Performance Optimization
- Reduced sample rate (16kHz) for faster processing
- Larger hop lengths for computational efficiency
- Optional duration limiting (default: 60 seconds)
- Optimized parameter selection (n_thresholds, frame sizes)

## Technical Parameters

### Audio Processing
- **Sample Rate:** 16,000 Hz (optimized for speed)
- **STFT Hop Length:** 1024 samples
- **STFT Frame Length:** 2048 samples
- **Piano Frequency Range:** 27.5 Hz - 4186 Hz
- **Vocal Suppression Range:** 80 Hz - 300 Hz

### Pitch Detection
- **Frequency Range:** 60 Hz - 2000 Hz (avoids subharmonics)
- **PYIN Thresholds:** 50 (speed optimization)
- **Frequency Tolerance:** 50 cents (≈3% difference)

### Note Processing
- **Minimum Note Duration:** 100ms
- **Minimum Onset Gap:** 50ms
- **Valid Octave Range:** 1-7 (C1 to C7)

### MIDI Generation
- **Tempo Range:** 60-180 BPM (default: 120 BPM)
- **MIDI Note Range:** 24-108 (C1 to C7)
- **Volume:** 100 (maximum)

## Output Files Generated

1. **Piano Audio (WAV):** Isolated piano-only audio file
2. **MIDI File (.mid):** Standard MIDI format with all notes
3. **Sheet Music PDF:** Professional notation with staff, notes, and formatting
4. **Synthesized Audio (WAV, optional):** Re-synthesized audio from MIDI for verification

## Use Cases

1. **Music Transcription:** Convert audio recordings to sheet music
2. **Music Education:** Extract piano parts for learning purposes
3. **Music Analysis:** Study piano arrangements and note sequences
4. **Music Production:** Isolate piano tracks for remixing or editing
5. **Accessibility:** Create sheet music from audio-only sources

## Limitations & Considerations

1. **Audio Quality:** Best results with clear audio, minimal background noise
2. **Piano Prominence:** Requires piano to be audible in the mix
3. **Polyphonic Complexity:** Very dense chords may have detection inaccuracies
4. **Tempo Detection:** Assumes user-provided tempo; automatic tempo detection not implemented
5. **MuseScore Dependency:** Requires MuseScore 4 installation for best PDF quality
6. **Processing Time:** Longer audio files require more processing time
7. **Harmonic Confusion:** Very similar frequencies may be misidentified

## Future Enhancements

Potential improvements could include:
- Automatic tempo detection from audio
- Key signature detection and application
- Chord recognition and notation
- Multiple instrument extraction (not just piano)
- Real-time processing for live audio
- Improved accuracy for complex polyphonic passages
- Machine learning-based note recognition refinement

---

*This tool demonstrates the integration of advanced signal processing, music information retrieval, and automated notation generation to transform audio recordings into structured musical data and professional sheet music.*


