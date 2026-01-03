"""
Lyrics Translation Module
Handles translation of lyrics to different languages using OpenRouter API.
"""

import requests
from typing import Optional


class LyricsTranslator:
    """Handles translation of lyrics to different languages."""
    
    def __init__(self, api_key: str, openrouter_url: str, model: str):
        """
        Initialize the Lyrics Translator.
        
        Args:
            api_key: OpenRouter API key
            openrouter_url: OpenRouter API URL
            model: Model name to use
        """
        self.api_key = api_key
        self.openrouter_url = openrouter_url
        self.model = model
    
    def translate(self, lyrics: str, target_language: str = "Spanish") -> Optional[str]:
        """
        Translate lyrics to target language using OpenRouter API.
        
        Args:
            lyrics: Lyrics to translate
            target_language: Target language name (e.g., "Spanish", "French", "Japanese")
            
        Returns:
            Translated lyrics or None if error
        """
        if not lyrics:
            return None
        
        system_prompt = """You are a professional music translator. Your task is to translate song lyrics from one language to another while preserving:
1. The meaning and emotion of the original lyrics
2. The poetic structure and flow
3. The line breaks and verse structure
4. Cultural nuances when possible

Return ONLY the translated lyrics, maintaining the same formatting structure as the original."""
        
        user_message = f"""Translate the following song lyrics to {target_language}. Maintain the verse/chorus structure and formatting:

{lyrics}"""
        
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
                {"role": "user", "content": user_message}
            ]
        }
        
        try:
            print(f"🌐 Translating lyrics to {target_language}...")
            response = requests.post(self.openrouter_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            translated = result['choices'][0]['message']['content']
            
            if translated:
                return translated.strip()
        except requests.exceptions.RequestException as e:
            print(f"✗ Translation error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"  Error details: {error_detail}")
                except:
                    print(f"  Response: {e.response.text}")
        
        return None

