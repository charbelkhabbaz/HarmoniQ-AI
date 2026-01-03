"""
Music Tools - LangChain Tool Wrappers
Wraps existing music processing functions as LangChain tools for agent use.

This module provides all music-related tools that can be used by a LangChain agent.
Each tool is decorated with @tool and can be called by the agent automatically.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List

from langchain_core.tools import tool

# Import existing modules
from music_chatbot import MusicChatbot
from music_chatbot_youtube import MusicChatbotYouTube
from piano_extraction import PianoExtractor
from audio_transcription import AudioTranscriber
from mood_classifier import classify_mood
from pdf_generator import PDFGenerator

# ============================================
# OPTIONAL "additional" MUSIC RECOGNITION PACKAGE
# (LLM_Project-main/additional/MusicRecognition-main)
# ============================================

ADDITIONAL_MUSIC_AVAILABLE = False
_additional_root: Optional[Path] = None

try:
    # Resolve path to additional/MusicRecognition-main relative to this file
    _candidate_root = (
        Path(__file__).resolve().parent.parent
        / "additional"
        / "MusicRecognition-main"
    )
    if _candidate_root.exists():
        if str(_candidate_root) not in sys.path:
            sys.path.insert(0, str(_candidate_root))

        from music_recognition import (  # type: ignore
            load_audio_bytes_to_wav_bytes,
            recognize_with_audd,
            get_spotify_metadata,
            extract_audio_features_from_wav_bytes,
            heuristic_mood_from_features,
            SingerAgent,
            create_singer_agent,
            MusicRAGChatbot,
            create_rag_chatbot,
        )

        ADDITIONAL_MUSIC_AVAILABLE = True
        _additional_root = _candidate_root
    else:
        _additional_root = None
except Exception:
    # If anything fails, we simply mark the additional package as unavailable.
    ADDITIONAL_MUSIC_AVAILABLE = False
    _additional_root = None

# ============================================
# GLOBAL INSTANCES (Initialized externally)
# ============================================

_chatbot_instance: Optional[MusicChatbot] = None
_youtube_chatbot_instance: Optional[MusicChatbotYouTube] = None
_piano_extractor: Optional[PianoExtractor] = None

# Instances from the optional "additional" MusicRecognition-main package
_additional_singer_agent: Optional["SingerAgent"] = None  # type: ignore[name-defined]
_additional_rag_chatbot: Optional["MusicRAGChatbot"] = None  # type: ignore[name-defined]

# ============================================
# INITIALIZATION FUNCTION
# ============================================

def initialize_tools(db_config: Dict[str, Any], api_key: str, model: str, openrouter_url: str = "https://openrouter.ai/api/v1/chat/completions"):
    """
    Initialize backend instances for tools to use.
    Must be called before using any tools.
    
    Args:
        db_config: Database configuration dictionary
        api_key: OpenRouter API key
        model: Model name for API calls
        openrouter_url: OpenRouter API URL
    """
    global _chatbot_instance, _youtube_chatbot_instance, _piano_extractor
    
    try:
        _chatbot_instance = MusicChatbot(db_config, api_key, model)
        _chatbot_instance.connect_db()  # Connect to database
    except Exception as e:
        print(f"Warning: Failed to initialize MusicChatbot: {e}")
        _chatbot_instance = None
    
    try:
        _youtube_chatbot_instance = MusicChatbotYouTube(api_key, openrouter_url, model)
    except Exception as e:
        print(f"Warning: Failed to initialize MusicChatbotYouTube: {e}")
        _youtube_chatbot_instance = None
    
    try:
        _piano_extractor = PianoExtractor()
    except Exception as e:
        print(f"Warning: Failed to initialize PianoExtractor: {e}")
        _piano_extractor = None

    # Note: tools from the optional "additional" MusicRecognition-main package
    # are lazily initialized inside their respective tool functions. This keeps
    # this initializer focused on the core database / YouTube / piano tools.

# ============================================
# DATABASE & QUERY TOOLS
# ============================================

@tool
def query_music_database(question: str) -> str:
    """
    Query the music database using natural language.
    Converts questions to SQL and executes queries on the music database.
    
    Use this tool when users ask about:
    - Artists, albums, songs in the database
    - Music features (energy, danceability, etc.)
    - Database statistics or counts
    - Filtering or searching within the database
    
    Args:
        question: Natural language question about the database
                 Examples:
                 - "Show me all artists"
                 - "Find songs with high energy"
                 - "What are the top 10 most energetic songs?"
                 - "List albums released in 2023"
    
    Returns:
        Natural language answer with database results, or error message
    """
    if not _chatbot_instance:
        return "Error: Music chatbot not initialized. Database connection may be unavailable."
    
    try:
        result = _chatbot_instance.ask(question)
        answer = result.get('answer', 'No answer available')
        
        # Include SQL query info if available (for debugging)
        if result.get('sql_query'):
            answer += f"\n\n[SQL Query: {result['sql_query']}]"
        
        return answer
    except Exception as e:
        return f"Error querying database: {str(e)}"

@tool
def search_music_web(query: str, max_results: int = 3) -> str:
    """
    Search the web for music-related information.
    
    Use this tool when users ask about:
    - Latest music trends or news
    - Music theory or genres
    - Artist biographies or achievements
    - Album reviews or ratings
    - Music industry information
    
    Args:
        query: Search query string (2-4 words recommended)
               Examples:
               - "latest music trends 2024"
               - "jazz music history"
               - "Taylor Swift latest album"
        max_results: Maximum number of results to return (default: 3, max: 5)
    
    Returns:
        Formatted string with search results including titles, descriptions, and URLs
    """
    if not _chatbot_instance:
        return "Error: Music chatbot not initialized."
    
    try:
        # Limit max_results to reasonable value
        max_results = min(max_results, 5)
        
        results = _chatbot_instance.search_web(query, max_results)
        
        if not results:
            return f"No search results found for '{query}'"
        
        formatted = f"Web Search Results for '{query}':\n\n"
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            body = result.get('body', 'No description')
            href = result.get('href', '')
            
            formatted += f"[{i}] {title}\n"
            formatted += f"    {body[:300]}...\n"
            if href:
                formatted += f"    Source: {href}\n"
            formatted += "\n"
        
        return formatted
    except Exception as e:
        return f"Error searching web: {str(e)}"

# ============================================
# LYRICS TOOLS
# ============================================

@tool
def get_song_lyrics(song_name: str, artist_name: Optional[str] = None) -> str:
    """
    Get lyrics for a song by song name and optional artist name.
    
    Use this tool when users ask for:
    - Song lyrics
    - Lyrics of a specific song
    - Words to a song
    
    Args:
        song_name: Name of the song (required)
                   Examples: "Bohemian Rhapsody", "Shape of You", "Blinding Lights"
        artist_name: Optional artist name for better accuracy
                     Examples: "Queen", "Ed Sheeran", "The Weeknd"
    
    Returns:
        Complete lyrics text with proper formatting (verses, choruses, etc.),
        or error message if lyrics not found
    """
    if not _chatbot_instance:
        return "Error: Music chatbot not initialized."
    
    try:
        lyrics = _chatbot_instance.get_lyrics_by_name(song_name, artist_name)
        
        if lyrics:
            # Store in chatbot for potential translation
            _chatbot_instance.current_lyrics = lyrics
            return f"Lyrics for '{song_name}'" + (f" by {artist_name}" if artist_name else "") + ":\n\n" + lyrics
        else:
            return f"Could not find lyrics for '{song_name}'" + (f" by {artist_name}" if artist_name else "")
    except Exception as e:
        return f"Error getting lyrics: {str(e)}"

@tool
def translate_lyrics(lyrics: str, target_language: str = "Spanish") -> str:
    """
    Translate song lyrics to a target language.
    
    Use this tool when users want to:
    - Translate lyrics to another language
    - Get lyrics in a different language
    - Convert lyrics from one language to another
    
    Args:
        lyrics: Lyrics text to translate (can be partial or full lyrics)
        target_language: Target language name
                        Supported: Spanish, French, German, Italian, Portuguese,
                                   Japanese, Korean, Chinese, Arabic, Hindi, Russian
    
    Returns:
        Translated lyrics text, or error message if translation fails
    """
    if not _chatbot_instance:
        return "Error: Music chatbot not initialized."
    
    try:
        # If no lyrics provided, try to use current lyrics from chatbot
        if not lyrics and _chatbot_instance.current_lyrics:
            lyrics = _chatbot_instance.current_lyrics
        
        if not lyrics:
            return "Error: No lyrics provided. Please get lyrics first using get_song_lyrics tool."
        
        translated = _chatbot_instance.translate_lyrics(lyrics, target_language)
        
        if translated:
            # Store translation
            _chatbot_instance.current_translation = translated
            return f"Translation to {target_language}:\n\n{translated}"
        else:
            return f"Failed to translate lyrics to {target_language}"
    except Exception as e:
        return f"Error translating lyrics: {str(e)}"

@tool
def generate_lyrics_pdf(lyrics: str, output_path: str, title: str = "Song Lyrics",
                        is_translation: bool = False, target_language: str = "Translated") -> str:
    """
    Generate a PDF file with lyrics.
    
    Use this tool when users want to:
    - Download lyrics as PDF
    - Save lyrics to a file
    - Create a printable lyrics document
    
    Args:
        lyrics: Lyrics text to include in PDF
        output_path: Path where PDF will be saved (include .pdf extension)
                     Examples: "lyrics.pdf", "/tmp/song_lyrics.pdf"
        title: Title for the PDF document (default: "Song Lyrics")
        is_translation: Whether this is a translation (default: False)
        target_language: Target language if translation (default: "Translated")
    
    Returns:
        Success message with file path, or error message if generation fails
    """
    if not _chatbot_instance:
        return "Error: Music chatbot not initialized."
    
    try:
        # If no lyrics provided, try to use current lyrics
        if not lyrics and _chatbot_instance.current_lyrics:
            lyrics = _chatbot_instance.current_lyrics
        
        if not lyrics:
            return "Error: No lyrics provided. Please get lyrics first using get_song_lyrics tool."
        
        # Ensure output_path has .pdf extension
        if not output_path.endswith('.pdf'):
            output_path += '.pdf'
        
        success = _chatbot_instance.generate_lyrics_pdf(
            lyrics=lyrics,
            output_path=output_path,
            title=title,
            is_translation=is_translation,
            target_language=target_language
        )
        
        if success and os.path.exists(output_path):
            return f"PDF generated successfully at: {os.path.abspath(output_path)}"
        else:
            return f"Failed to generate PDF at: {output_path}"
    except Exception as e:
        return f"Error generating PDF: {str(e)}"

# ============================================
# PIANO EXTRACTION TOOLS
# ============================================

@tool
def extract_piano_from_audio(audio_path: str, tempo: int = 120, 
                             max_duration: Optional[float] = 60.0) -> str:
    """
    Extract piano notes from audio file and generate sheet music, MIDI, and audio files.
    
    Use this tool when users:
    - Upload an audio file and want piano notes extracted
    - Want sheet music from an audio file
    - Need MIDI file from audio
    - Want to isolate piano from mixed audio
    
    Args:
        audio_path: Path to audio file (.wav, .mp3, .m4a, .ogg, .flac)
                   Must be an absolute path or relative to current directory
        tempo: Tempo in BPM for MIDI generation (default: 120, range: 60-180)
        max_duration: Maximum duration in seconds to process
                     Use None for full file, or specify seconds (e.g., 60.0 for first minute)
                     Default: 60.0 (recommended for faster processing)
    
    Returns:
        JSON string with paths to generated files:
        {
            "piano_audio": "path/to/piano.wav",
            "midi": "path/to/piano.mid",
            "pdf": "path/to/sheet_music.pdf",
            "synthesized_audio": "path/to/synthesized.wav" (optional),
            "notes_count": 150
        }
        Or error message if extraction fails
    """
    if not _piano_extractor:
        return json.dumps({"error": "Piano extractor not initialized. Please install librosa and soundfile."})
    
    if not os.path.exists(audio_path):
        return json.dumps({"error": f"Audio file not found: {audio_path}"})
    
    try:
        # Create temporary output directory
        output_dir = tempfile.mkdtemp(prefix="piano_extraction_")
        
        # Process audio
        results = _piano_extractor.process_audio_to_piano_sheet(
            audio_path=audio_path,
            output_dir=output_dir,
            tempo=tempo,
            max_duration=max_duration
        )
        
        # Convert to JSON string
        return json.dumps(results, indent=2)
    except Exception as e:
        error_msg = f"Error extracting piano: {str(e)}"
        return json.dumps({"error": error_msg})

# ============================================
# YOUTUBE TOOLS
# ============================================

@tool
def extract_youtube_audio(youtube_url: str, output_dir: Optional[str] = None) -> str:
    """
    Download and extract audio from a YouTube video.
    
    Use this tool when users:
    - Provide a YouTube URL and want the audio
    - Want to download music from YouTube
    - Need audio file from YouTube video
    
    Args:
        youtube_url: YouTube video URL
                     Examples:
                     - "https://www.youtube.com/watch?v=VIDEO_ID"
                     - "https://youtu.be/VIDEO_ID"
        output_dir: Directory to save audio file (default: system temp directory)
    
    Returns:
        Path to downloaded audio file (.mp3), or error message if extraction fails
    """
    try:
        if not output_dir:
            output_dir = tempfile.gettempdir()
        
        audio_path = AudioTranscriber.extract_audio_from_youtube(youtube_url, output_dir)
        
        if audio_path and os.path.exists(audio_path):
            return f"Audio extracted successfully: {os.path.abspath(audio_path)}"
        else:
            return "Failed to extract audio from YouTube. Please check the URL and try again."
    except Exception as e:
        return f"Error extracting YouTube audio: {str(e)}"

@tool
def get_youtube_music_info(youtube_url: str, song_name: Optional[str] = None,
                          artist_name: Optional[str] = None) -> str:
    """
    Get comprehensive music information from a YouTube video.
    
    Use this tool when users:
    - Want detailed information about a YouTube music video
    - Ask about song details, artist info, or album information
    - Need context about a YouTube music video
    
    Args:
        youtube_url: YouTube video URL
        song_name: Optional song name (will try to extract from video title if not provided)
        artist_name: Optional artist name
    
    Returns:
        Formatted string with comprehensive music information including:
        - Song details (title, artist, album, release date, genre)
        - Artist information (background, achievements, style)
        - Song meaning and characteristics
        - Cultural significance and chart performance
    """
    if not _youtube_chatbot_instance:
        return "Error: YouTube chatbot not initialized."
    
    try:
        # Extract video info first
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            video_info = {
                'title': info.get('title', 'Unknown'),
                'uploader': info.get('uploader', 'Unknown'),
                'description': info.get('description', ''),
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', ''),
                'thumbnail': info.get('thumbnail', ''),
            }
    except Exception as e:
        return f"Error extracting video info: {str(e)}"
    
    # Use video title if song_name not provided
    if not song_name:
        song_name = video_info.get('title', 'Unknown')
    
    try:
        music_info = _youtube_chatbot_instance.get_music_info(
            song_name=song_name,
            artist_name=artist_name,
            video_info=video_info
        )
        
        information = music_info.get('information', 'No information available')
        
        # Format response
        response = f"Music Information for YouTube Video:\n"
        response += f"Video Title: {video_info.get('title', 'Unknown')}\n"
        response += f"Channel: {video_info.get('uploader', 'Unknown')}\n\n"
        response += f"{information}"
        
        return response
    except Exception as e:
        return f"Error getting music info: {str(e)}"

@tool
def get_youtube_lyrics(youtube_url: str, song_name: Optional[str] = None,
                      artist_name: Optional[str] = None) -> str:
    """
    Get lyrics for a song from YouTube video and generate PDF.
    
    Use this tool when users:
    - Want lyrics from a YouTube music video
    - Ask for lyrics of a song they found on YouTube
    - Need lyrics based on YouTube video
    
    Args:
        youtube_url: YouTube video URL
        song_name: Optional song name (will extract from video title if not provided)
        artist_name: Optional artist name
    
    Returns:
        JSON string with lyrics text and PDF path:
        {
            "lyrics": "formatted lyrics text",
            "pdf_path": "path/to/lyrics.pdf",
            "song_name": "Song Name",
            "artist_name": "Artist Name"
        }
        Or error message if lyrics not found
    """
    if not _youtube_chatbot_instance:
        return json.dumps({"error": "YouTube chatbot not initialized."})
    
    try:
        # Extract song name and artist from video if not provided
        # Always extract video info to help with parsing
        import yt_dlp
        import re
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            video_title = info.get('title', 'Unknown')
            
            # Clean up common YouTube suffixes/prefixes
            # Remove common suffixes like (Lyrics), [Lyrics], (Official Video), etc.
            title_clean = re.sub(r'\s*\([^)]*(?:Lyrics|Official|Video|Audio|HD|4K|Remastered|MV|Music Video)[^)]*\)', '', video_title, flags=re.IGNORECASE)
            title_clean = re.sub(r'\s*\[[^\]]*(?:Lyrics|Official|Video|Audio|HD|4K|Remastered|MV|Music Video)[^\]]*\]', '', title_clean, flags=re.IGNORECASE)
            title_clean = title_clean.strip()
            
            # Parse title formats: "Artist - Song Name" (most common on YouTube) or "Song Name - Artist"
            if ' - ' in title_clean:
                parts = title_clean.split(' - ', 1)
                part1 = parts[0].strip()
                part2 = parts[1].strip()
                
                # YouTube standard format is "Artist - Song Name"
                # Most reliable: assume first part is artist, second is song
                if not song_name and not artist_name:
                    # Extract both from title: "Artist - Song Name"
                    artist_name = part1
                    song_name = part2
                elif song_name and not artist_name:
                    # User provided song_name, extract artist from title
                    artist_name = part1
                elif artist_name and not song_name:
                    # User provided artist_name, extract song from title
                    song_name = part2
                # If both provided, use user's values (don't override)
            else:
                # No delimiter found, use whole title as song name (if not provided)
                if not song_name:
                    song_name = title_clean
    except Exception as e:
        return json.dumps({"error": f"Error extracting video information: {str(e)}"})
    
    try:
        lyrics = _youtube_chatbot_instance.get_lyrics(song_name, artist_name)
        
        if lyrics:
            # Generate PDF automatically
            pdf_generator = PDFGenerator()
            output_dir = tempfile.gettempdir()
            pdf_filename = f"{song_name.replace(' ', '_').replace('/', '_')}_lyrics.pdf"
            if artist_name:
                pdf_filename = f"{artist_name.replace(' ', '_').replace('/', '_')}_{pdf_filename}"
            pdf_path = os.path.join(output_dir, pdf_filename)
            
            # Create title for PDF
            pdf_title = f"{song_name}"
            if artist_name:
                pdf_title += f" by {artist_name}"
            
            # Generate PDF with well-organized lyrics
            pdf_success = pdf_generator.generate(
                lyrics=lyrics,
                output_path=pdf_path,
                title=pdf_title,
                is_translation=False,
                original_language="Original",
                target_language="Original"
            )
            
            if pdf_success and os.path.exists(pdf_path):
                return json.dumps({
                    "lyrics": lyrics,
                    "pdf_path": os.path.abspath(pdf_path),
                    "song_name": song_name,
                    "artist_name": artist_name or "",
                    "message": f"Lyrics for '{song_name}'" + (f" by {artist_name}" if artist_name else "") + " retrieved and PDF generated successfully."
                }, indent=2)
            else:
                # Return lyrics even if PDF generation fails
                return json.dumps({
                    "lyrics": lyrics,
                    "pdf_path": None,
                    "song_name": song_name,
                    "artist_name": artist_name or "",
                    "message": f"Lyrics for '{song_name}'" + (f" by {artist_name}" if artist_name else "") + " retrieved. PDF generation failed.",
                    "error": "PDF generation failed"
                }, indent=2)
        else:
            return json.dumps({
                "error": f"Could not find lyrics for '{song_name}'" + (f" by {artist_name}" if artist_name else ""),
                "song_name": song_name,
                "artist_name": artist_name or ""
            }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Error getting lyrics: {str(e)}"}, indent=2)

# ============================================
# AUDIO ANALYSIS TOOLS
# ============================================

@tool
def mood_classifier_tool(input_path: str = "sound.wav") -> str:
    """
    Classify the mood and acoustic characteristics of a local audio file.
    
    Use this tool when users:
    - Want to analyze audio characteristics (tempo, mood, timbre, etc.)
    - Need to understand the musical profile of an audio file
    - Want to classify audio for playlist organization
    - Need detailed acoustic analysis
    
    Args:
        input_path: Path to the audio file on disk (default: 'sound.wav')
                   Supports: .wav, .mp3, .m4a, .ogg, .flac
    
    Returns:
        JSON string with:
        - timbre: "dark", "neutral", or "bright"
        - expression: "vocal", "instrumental", "rhythmic", "ambient", "mixed", or "unknown"
        - summary: Dictionary with tempo_bpm, tempo_label, dynamic_profile, 
                   rhythmic_profile, timbre, texture_density, expression
        - tags: List of descriptive tags (e.g., "slow-paced", "rich-texture")
        - features: Dictionary with low-level audio features
    """
    if not os.path.exists(input_path):
        return json.dumps({
            "error": f"File '{input_path}' does not exist.",
            "mood_tags": ["error"],
            "confidence": 0.0
        })
    
    # Infer file format from extension (default to 'wav')
    ext = os.path.splitext(input_path)[1].lower().lstrip(".") or "wav"
    
    try:
        with open(input_path, "rb") as f:
            audio_bytes = f.read()
        
        result = classify_mood(audio_bytes, file_format=ext)
        
        # Return as JSON string so the agent can consume it cleanly
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Error processing audio file: {str(e)}"})

# ============================================
# ADDITIONAL MUSIC RECOGNITION MAIN TOOLS
# (Wrappers around additional/MusicRecognition-main)
# ============================================

def _ensure_additional_singer_agent() -> (Optional["SingerAgent"], str):  # type: ignore[name-defined]
    """
    Lazily initialize and return the SingerAgent from the additional package.

    Returns:
        Tuple of (SingerAgent instance or None, error_message or empty string)
    """
    global _additional_singer_agent

    if not ADDITIONAL_MUSIC_AVAILABLE or _additional_root is None:
        return None, (
            "Additional music_recognition package is not available. "
            "Ensure 'additional/MusicRecognition-main' exists and dependencies are installed."
        )

    if _additional_singer_agent is not None:
        return _additional_singer_agent, ""

    try:
        output_dir = _additional_root / "output"
        _additional_singer_agent = create_singer_agent(  # type: ignore[name-defined]
            output_dir=str(output_dir),
            voice_style="default",
        )
        return _additional_singer_agent, ""
    except Exception as e:  # pragma: no cover - defensive
        return None, f"Failed to initialize SingerAgent from additional package: {e}"


def _ensure_additional_rag_chatbot() -> (Optional["MusicRAGChatbot"], str):  # type: ignore[name-defined]
    """
    Lazily initialize and return the MusicRAGChatbot from the additional package.

    Returns:
        Tuple of (MusicRAGChatbot instance or None, error_message or empty string)
    """
    global _additional_rag_chatbot

    if not ADDITIONAL_MUSIC_AVAILABLE or _additional_root is None:
        return None, (
            "Additional music_recognition package is not available. "
            "Ensure 'additional/MusicRecognition-main' exists and dependencies are installed."
        )

    if _additional_rag_chatbot is not None:
        return _additional_rag_chatbot, ""

    try:
        pdfs_dir = _additional_root / "music_recognition" / "pdfs"
        vector_db_path = _additional_root / "music_recognition" / "vector_db"
        _additional_rag_chatbot = create_rag_chatbot(  # type: ignore[name-defined]
            pdfs_dir=str(pdfs_dir),
            vector_db_path=str(vector_db_path),
        )
        return _additional_rag_chatbot, ""
    except Exception as e:  # pragma: no cover - defensive
        return None, f"Failed to initialize MusicRAGChatbot from additional package: {e}"


@tool
def recognize_and_analyze_song(audio_path: str) -> str:
    """
    Identify a song from an audio file and analyze its audio features using the
    additional MusicRecognition-main package.

    This tool:
    - Converts the input audio to WAV
    - Sends it to the AudD API for song recognition
    - Optionally fetches Spotify metadata (if credentials are configured)
    - Extracts audio features (MFCC, Chroma, ZCR)
    - Provides a simple heuristic mood classification

    Args:
        audio_path: Path to an audio file (.mp3, .wav, .m4a, .ogg, .flac)

    Returns:
        JSON string with keys:
        - recognition: raw AudD recognition result (or error)
        - spotify_metadata: Spotify metadata (if available)
        - features: extracted audio features (if successful)
        - mood: heuristic mood label (if features available)
    """
    if not ADDITIONAL_MUSIC_AVAILABLE or _additional_root is None:
        return json.dumps({
            "error": "Additional music_recognition package is not available. "
                     "Ensure 'additional/MusicRecognition-main' exists and dependencies are installed."
        })

    if not os.path.exists(audio_path):
        return json.dumps({"error": f"Audio file not found: {audio_path}"})

    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        # Convert to WAV bytes using the additional package utilities
        wav_bytes = load_audio_bytes_to_wav_bytes(audio_bytes)  # type: ignore[name-defined]

        # Recognize song with AudD (token is read from environment if not passed)
        recognition_result = recognize_with_audd(wav_bytes, api_token=None)  # type: ignore[name-defined]

        # Try to extract title/artist for optional Spotify metadata
        spotify_metadata: Dict[str, Any] = {}
        try:
            if isinstance(recognition_result, dict) and recognition_result.get("status") == "success":
                result_data = recognition_result.get("result") or {}
                title = result_data.get("title")
                artist = result_data.get("artist")
                if title and artist:
                    spotify_metadata = get_spotify_metadata(  # type: ignore[name-defined]
                        track_name=title,
                        artist=artist,
                    ) or {}
        except Exception as e:
            spotify_metadata = {"error": f"Failed to fetch Spotify metadata: {e}"}

        # Extract audio features and heuristic mood
        features: Dict[str, Any] = {}
        mood: Optional[str] = None
        try:
            features = extract_audio_features_from_wav_bytes(  # type: ignore[name-defined]
                wav_bytes
            ) or {}
            if "error" not in features:
                mood = heuristic_mood_from_features(features)  # type: ignore[name-defined]
        except Exception as e:
            features = {"error": f"Feature extraction failed: {e}"}

        result = {
            "recognition": recognition_result,
            "spotify_metadata": spotify_metadata,
            "features": features,
            "mood": mood,
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Error in recognize_and_analyze_song: {e}"})


@tool
def convert_lyrics_to_singing(lyrics: str, voice_style: str = "default") -> str:
    """
    Convert text/lyrics to singing audio using the SingerAgent from the
    additional MusicRecognition-main package.

    Use this tool when users:
    - Want to hear their lyrics sung in a specific style (pop, rock, jazz, etc.)
    - Need text-to-singing with background music

    Args:
        lyrics: Lyrics or text to sing
        voice_style: Voice style name (e.g., "pop", "rock", "jazz", "classical",
                     "rap", "country", "r&b", or "default")

    Returns:
        JSON string with:
        - audio_path: path to the generated WAV file (if successful)
        - error: error message (if any)
    """
    if not lyrics or not lyrics.strip():
        return json.dumps({"error": "Lyrics cannot be empty."})

    agent, err = _ensure_additional_singer_agent()
    if agent is None:
        return json.dumps({"error": err})

    try:
        audio_path = agent.sing(  # type: ignore[call-arg]
            lyrics=lyrics.strip(),
            voice_style=voice_style,
        )
        return json.dumps({"audio_path": audio_path})
    except Exception as e:
        return json.dumps({"error": f"Error generating singing audio: {e}"})


@tool
def query_music_theory_rag(question: str, top_k: int = 3) -> str:
    """
    Ask a question about music theory, practice, or related concepts using the
    RAG chatbot from the additional MusicRecognition-main package.

    This tool uses:
    - PDF documents in the additional/music_recognition/pdfs folder
    - Sentence-transformers + FAISS for retrieval
    - A local Hugging Face model (FLAN-T5) for answer generation

    Args:
        question: Natural language question about music
        top_k: Number of relevant chunks to retrieve (default: 3)

    Returns:
        JSON string with:
        - answer: generated answer
        - sources: list of source PDF filenames
        - chunks: retrieved context snippets with similarity scores
    """
    if not question or not question.strip():
        return json.dumps({
            "error": "Question cannot be empty. Please provide a music-related question."
        })

    chatbot, err = _ensure_additional_rag_chatbot()
    if chatbot is None:
        return json.dumps({"error": err})

    try:
        result = chatbot.query(question, top_k=top_k)  # type: ignore[call-arg]
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Error querying RAG chatbot: {e}"})

# ============================================
# TOOL REGISTRY
# ============================================

def get_all_tools() -> List:
    """
    Get list of all available tools for the agent.
    
    Returns:
        List of tool objects that can be used by LangChain agent
    """
    tools = [
        # Database & Search
        query_music_database,
        search_music_web,
        
        # Lyrics
        get_song_lyrics,
        translate_lyrics,
        generate_lyrics_pdf,
        
        # Piano Extraction
        extract_piano_from_audio,
        
        # YouTube
        extract_youtube_audio,
        get_youtube_music_info,
        get_youtube_lyrics,
        
        # Audio Analysis
        mood_classifier_tool,

        # Additional MusicRecognition-main tools
        recognize_and_analyze_song,
        convert_lyrics_to_singing,
        query_music_theory_rag,
    ]
    
    return tools

