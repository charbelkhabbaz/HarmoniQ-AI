"""
Lyrics Extraction Module - OpenRouter DeepSeek Version
Fetches song lyrics using OpenRouter DeepSeek model based on song name.
No audio transcription needed - just provide song name and get lyrics!
"""

import os
import re
from typing import Optional
import requests


class AudioTranscriber:
    """
    Lyrics fetcher using OpenRouter DeepSeek model.
    Simply provide song name and artist, get structured lyrics back.
    """
    
    def __init__(self, api_key: Optional[str] = None, openrouter_url: Optional[str] = None, model: str = "deepseek/deepseek-chat-v3.1"):
        """
        Initialize the Lyrics Fetcher.
        
        Args:
            api_key: OpenRouter API key
            openrouter_url: OpenRouter API URL
            model: Model name to use (default: deepseek/deepseek-chat-v3.1)
        """
        self.api_key = api_key
        self.openrouter_url = openrouter_url or "https://openrouter.ai/api/v1/chat/completions"
        self.model = model
        
        if not self.api_key:
            print("⚠️  OpenRouter API key not set")
    
    def set_translation_api(self, api_key: str, openrouter_url: str, model: str):
        """
        Set OpenRouter API credentials.
        
        Args:
            api_key: OpenRouter API key
            openrouter_url: OpenRouter API URL
            model: Model name to use
        """
        self.api_key = api_key
        self.openrouter_url = openrouter_url
        self.model = model
    
    def get_lyrics_by_name(self, song_name: str, artist_name: Optional[str] = None) -> Optional[str]:
        """
        Get song lyrics using OpenRouter DeepSeek model based on song name.
        
        Args:
            song_name: Name of the song
            artist_name: Optional artist name for better accuracy
            
        Returns:
            Structured lyrics or None if error
        """
        if not self.api_key or not self.openrouter_url:
            print("✗ OpenRouter API not configured")
            return None
        
        try:
            print(f"🎵 Fetching lyrics for: {song_name}" + (f" by {artist_name}" if artist_name else ""))
            
            # Build query
            query = f"Song: {song_name}"
            if artist_name:
                query += f"\nArtist: {artist_name}"
            
            system_prompt = """You are an expert music lyrics database. Your task is to provide accurate, complete song lyrics when given a song name and optionally an artist name.

INSTRUCTIONS:
1. **Find the Lyrics**: Search your knowledge for the exact lyrics of the requested song
2. **Provide Complete Lyrics**: Include all verses, choruses, bridges, and any other sections
3. **Structure Professionally**: Format the lyrics with clear section labels:
   - "INTRO" for opening section
   - "VERSE 1", "VERSE 2", etc. for verses
   - "CHORUS" for repeated chorus/refrain sections
   - "BRIDGE" for bridge sections (if present)
4. **Format Rules**:
   - Use section headers in ALL CAPS (e.g., "INTRO", "VERSE 1", "CHORUS")
   - Add blank lines between sections
   - Keep original words exactly as written
   - Make it visually appealing like published lyrics
5. **If Song Not Found**: If you cannot find the exact lyrics, say "Lyrics not found for [song name]"
6. **Language Support**: Support both Arabic and English songs

OUTPUT FORMAT:
- Start with song name and artist (if provided)
- Then provide structured lyrics with section labels
- Use proper spacing and line breaks
- Return ONLY the lyrics, no explanations or markdown code blocks"""
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "Music Chatbot"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Please provide the complete lyrics for:\n\n{query}"}
                ]
            }
            
            response = requests.post(self.openrouter_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            lyrics = result['choices'][0]['message']['content']
            
            # Clean up response
            lyrics = lyrics.strip()
            
            # Remove markdown code blocks if present
            if lyrics.startswith("```"):
                lines = lyrics.split('\n')
                lyrics = '\n'.join([line for line in lines if not line.strip().startswith('```')])
                lyrics = lyrics.strip()
            
            print(f"✓ Lyrics fetched successfully! (Length: {len(lyrics)} characters)")
            
            return lyrics
            
        except Exception as e:
            print(f"✗ Error fetching lyrics: {e}")
            if "api_key" in str(e).lower() or "authentication" in str(e).lower():
                print("  Check your OpenRouter API key is correct")
            elif "rate_limit" in str(e).lower():
                print("  Rate limit exceeded - please wait and try again")
            import traceback
            traceback.print_exc()
            return None
    
    def transcribe(self, audio_path: str = None, song_name: str = None, artist_name: str = None, language: Optional[str] = None) -> Optional[str]:
        """
        Get lyrics - supports both song name (new method) and audio path (legacy).
        
        Args:
            audio_path: Legacy parameter (not used, kept for compatibility)
            song_name: Name of the song (new preferred method)
            artist_name: Optional artist name
            language: Language code (optional, for future use)
            
        Returns:
            Structured lyrics or None if error
        """
        # New method: Get lyrics by song name
        if song_name:
            return self.get_lyrics_by_name(song_name, artist_name)
        
        # Legacy method: If audio_path provided, prompt user to use song name instead
        if audio_path:
            print("⚠️  Audio transcription is no longer supported.")
            print("   Please use song name instead: get_lyrics_by_name(song_name, artist_name)")
            return None
        
        return None
    
    @staticmethod
    def extract_audio_from_youtube(youtube_url: str, output_dir: str = ".") -> Optional[str]:
        """
        Download and extract the audio track from a YouTube link using yt-dlp.
        (Kept for compatibility, but lyrics are now fetched by song name)
        
        Args:
            youtube_url: The YouTube link to extract audio from
            output_dir: Directory to save the extracted file
            
        Returns:
            Path to the downloaded audio file (mp3) or None if error
        """
        try:
            import yt_dlp
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }], 
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                filename = ydl.prepare_filename(info)
                base, _ = os.path.splitext(filename)
                mp3_file = base + ".mp3"
                if os.path.isfile(mp3_file):
                    return mp3_file
                else:
                    return None
        except Exception as e:
            print(f"✗ YouTube audio extraction error: {e}")
            return None
