"""
Music Chatbot for YouTube Music Interactions
Handles music-related questions using DeepSeek via OpenRouter.
Specialized for answering questions about songs, artists, lyrics, and music information.
"""

import requests
from typing import Optional, Dict, Any, List
import json


class MusicChatbotYouTube:
    """
    Specialized music chatbot for YouTube music interactions.
    Uses DeepSeek model via OpenRouter to answer music-related questions.
    """
    
    def __init__(self, api_key: str, openrouter_url: str, model: str = "deepseek/deepseek-chat-v3.1"):
        """
        Initialize the Music Chatbot for YouTube.
        
        Args:
            api_key: OpenRouter API key
            openrouter_url: OpenRouter API URL
            model: Model name to use (default: deepseek/deepseek-chat-v3.1)
        """
        self.api_key = api_key
        self.openrouter_url = openrouter_url
        self.model = model
        self.conversation_history = []  # Track conversation for context
    
    def call_openrouter(self, messages: list) -> Optional[str]:
        """
        Call OpenRouter API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            
        Returns:
            Response text or None if error
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": self.model,
            "messages": messages
        }
        
        try:
            response = requests.post(self.openrouter_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            print(f"✗ OpenRouter API error: {e}")
            return None
    
    def get_music_info(self, song_name: str, artist_name: Optional[str] = None, 
                      video_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Get comprehensive music information using DeepSeek.
        
        Args:
            song_name: Name of the song
            artist_name: Optional artist name
            video_info: Optional YouTube video info (title, description, etc.)
            
        Returns:
            Dictionary with music information
        """
        # Build context from video info if available
        context = ""
        if video_info:
            context = f"""
YouTube Video Information:
- Title: {video_info.get('title', 'Unknown')}
- Channel: {video_info.get('uploader', 'Unknown')}
- Description: {video_info.get('description', '')[:500]}...
- Duration: {video_info.get('duration', 0)} seconds
"""
        
        query = f"Song: {song_name}"
        if artist_name:
            query += f"\nArtist: {artist_name}"
        
        system_prompt = """You are an expert music information assistant. Your task is to provide comprehensive, accurate information about songs, artists, and music.

When given a song name and optionally an artist name, provide detailed information including:

1. **Song Details**:
   - Full song title
   - Artist/band name
   - Album name (if known)
   - Release date/year (if known)
   - Genre
   - Duration (if available)

2. **Artist Information**:
   - Artist name and background
   - Notable achievements
   - Other popular songs
   - Musical style/genre

3. **Song Information**:
   - Song meaning/theme
   - Musical characteristics
   - Cultural significance
   - Chart performance (if notable)

4. **Lyrics** (if requested or if part of the query):
   - Complete, accurate lyrics
   - Structured with sections (Intro, Verse, Chorus, Bridge)
   - Properly formatted

Format your response in a clear, organized manner. If you don't have specific information, say so honestly rather than making it up.

Return the information in a structured format that's easy to read."""
        
        user_message = f"""Please provide comprehensive information about this music:

{query}

{context}

Provide detailed information including song details, artist information, and any other relevant music information."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Add conversation history for context
        if self.conversation_history:
            messages = self.conversation_history[-3:] + messages
        
        response = self.call_openrouter(messages)
        
        if response:
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Keep history manageable
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
        
        return {
            "song_name": song_name,
            "artist_name": artist_name,
            "information": response,
            "video_info": video_info
        }
    
    def get_lyrics(self, song_name: str, artist_name: Optional[str] = None) -> Optional[str]:
        """
        Get song lyrics using DeepSeek.
        
        Args:
            song_name: Name of the song
            artist_name: Optional artist name
            
        Returns:
            Lyrics text or None if error
        """
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

Return ONLY the lyrics, no explanations or markdown code blocks."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please provide the complete lyrics for:\n\n{query}"}
        ]
        
        response = self.call_openrouter(messages)
        
        if response:
            # Clean up response
            lyrics = response.strip()
            if lyrics.startswith("```"):
                lines = lyrics.split('\n')
                lyrics = '\n'.join([line for line in lines if not line.strip().startswith('```')])
                lyrics = lyrics.strip()
            
            return lyrics
        
        return None
    
    def chat_about_music(self, question: str, song_context: Optional[Dict] = None) -> Optional[str]:
        """
        Chat about music - answer questions about songs, artists, lyrics, etc.
        
        Args:
            question: User's question about the music
            song_context: Optional context about the current song (name, artist, video info)
            
        Returns:
            Response text or None if error
        """
        # Build context
        context = ""
        if song_context:
            song_name = song_context.get('song_name', '')
            artist_name = song_context.get('artist_name', '')
            video_info = song_context.get('video_info', {})
            
            context = f"""
Current Song Context:
- Song: {song_name}
- Artist: {artist_name if artist_name else 'Unknown'}
"""
            if video_info:
                context += f"- Video Title: {video_info.get('title', 'Unknown')}\n"
                context += f"- Channel: {video_info.get('uploader', 'Unknown')}\n"
        
        system_prompt = """You are a knowledgeable and friendly music expert assistant. You help users understand songs, artists, lyrics, and music in general.

Your capabilities:
- Explain song meanings and themes
- Discuss artist backgrounds and careers
- Analyze lyrics and their interpretations
- Provide music information and trivia
- Answer questions about music history, genres, and culture
- Help users understand musical concepts

Be conversational, informative, and engaging. Use the provided context about the current song when relevant, but you can also answer general music questions."""
        
        user_message = question
        if context:
            user_message = f"{context}\n\nUser Question: {question}"
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history for context
        if self.conversation_history:
            messages.extend(self.conversation_history[-3:])
        
        messages.append({"role": "user", "content": user_message})
        
        response = self.call_openrouter(messages)
        
        if response:
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Keep history manageable
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
        
        return response
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

