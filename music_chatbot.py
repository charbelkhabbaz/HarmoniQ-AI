import mysql.connector
import requests
import json
from typing import Optional, Dict, Any, Tuple, List
import sys
import os
from ddgs import DDGS

# Import new feature modules
from audio_transcription import AudioTranscriber
from lyrics_translation import LyricsTranslator
from pdf_generator import PDFGenerator


class MusicChatbot:
    def __init__(self, db_config: Dict[str, Any], api_key: str, model: str = "deepseek/deepseek-chat-v3.1"):
        """
        Initialize the Music Chatbot.
        
        Args:
            db_config: Database configuration dictionary
            api_key: OpenRouter API key
            model: OpenRouter model to use
        """
        self.db_config = db_config
        self.api_key = api_key
        self.model = model
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.connection = None
        self.cursor = None
        self.conversation_history = []  # Track conversation for context
        self.current_lyrics = None  # Store current lyrics for translation/PDF
        self.current_translation = None  # Store current translation
        
        # Initialize feature modules
        # Use OpenRouter DeepSeek to get lyrics by song name
        self.audio_transcriber = AudioTranscriber(api_key=api_key, openrouter_url=self.openrouter_url, model=model)
        self.audio_transcriber.set_translation_api(api_key, self.openrouter_url, model)
        self.lyrics_translator = LyricsTranslator(api_key, self.openrouter_url, model)
        self.pdf_generator = PDFGenerator()
        
        # Database schema for context
        self.schema_context = """
-- Artists Table
CREATE TABLE artists (
    artist_id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    nationality VARCHAR(100),
    birth_year INT(4),
    description TEXT,
    spotify_id CHAR(22) UNIQUE,
    youtube_channel VARCHAR(255)
);

-- Albums Table
CREATE TABLE albums (
    album_id INT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    artist_id INT NOT NULL,
    release_year INT(4),
    cover_url VARCHAR(512),
    FOREIGN KEY (artist_id) REFERENCES artists(artist_id) ON DELETE CASCADE
);

-- Songs Table
CREATE TABLE songs (
    song_id INT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    artist_id INT NOT NULL,
    album_id INT NOT NULL,
    release_year INT(4),
    genre VARCHAR(100),
    bpm SMALLINT,
    key_signature VARCHAR(50),
    duration_seconds SMALLINT,
    mood VARCHAR(100),
    language VARCHAR(50),
    spotify_id CHAR(22) UNIQUE,
    youtube_id CHAR(11) UNIQUE,
    audio_url VARCHAR(512),
    FOREIGN KEY (artist_id) REFERENCES artists(artist_id) ON DELETE CASCADE,
    FOREIGN KEY (album_id) REFERENCES albums(album_id) ON DELETE CASCADE
);

-- Lyrics Table
CREATE TABLE lyrics (
    lyric_id INT PRIMARY KEY,
    song_id INT UNIQUE NOT NULL,
    lyric_text TEXT,
    language VARCHAR(50),
    source VARCHAR(100),
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- Song Features Table
CREATE TABLE song_features (
    feature_id INT PRIMARY KEY,
    song_id INT UNIQUE NOT NULL,
    danceability FLOAT(5, 3),
    energy FLOAT(5, 3),
    valence FLOAT(5, 3),
    acousticness FLOAT(5, 3),
    instrumentalness FLOAT(5, 3),
    liveness FLOAT(5, 3),
    speechiness FLOAT(5, 3),
    mode TINYINT,
    loudness FLOAT(5, 2),
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- Music Notes Table
CREATE TABLE music_notes (
    note_id INT PRIMARY KEY,
    song_id INT UNIQUE NOT NULL,
    midi_data VARCHAR(255),
    sheet_music TEXT,
    key_signature VARCHAR(50),
    chord_progression VARCHAR(100),
    scale VARCHAR(50),
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- Audio Fingerprints Table
CREATE TABLE audio_fingerprints (
    fingerprint_id INT PRIMARY KEY,
    song_id INT UNIQUE NOT NULL,
    fingerprint_hash CHAR(64),
    algorithm VARCHAR(100),
    created_at DATETIME,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- Lyric Translations Table
CREATE TABLE lyric_translations (
    translation_id INT PRIMARY KEY,
    song_id INT NOT NULL,
    target_language VARCHAR(50),
    translated_text TEXT,
    translator_agent VARCHAR(100),
    date_created DATETIME,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- User Requests Table
CREATE TABLE user_requests (
    request_id INT PRIMARY KEY,
    user_input TEXT,
    detected_intent VARCHAR(255),
    agent_used VARCHAR(100),
    song_id INT NOT NULL,
    response_summary TEXT,
    timestamp DATETIME,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);

-- Recommendations Log Table
CREATE TABLE recommendations_log (
    rec_id INT PRIMARY KEY,
    user_id VARCHAR(50),
    song_id INT NOT NULL,
    reason VARCHAR(255),
    confidence_score FLOAT(4, 3),
    timestamp DATETIME,
    FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
);
"""
    
    def connect_db(self):
        """Connect to MySQL database."""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            self.cursor = self.connection.cursor(dictionary=True)
            print("✓ Connected to MySQL database")
            return True
        except mysql.connector.Error as err:
            print(f"✗ Database connection error: {err}")
            return False
    
    def disconnect_db(self):
        """Disconnect from MySQL database."""
        if self.cursor:
            self.cursor.close()
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("✓ Disconnected from MySQL database")
    
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
            response = requests.post(self.openrouter_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            print(f"✗ OpenRouter API error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"  Error details: {error_detail}")
                except:
                    print(f"  Response: {e.response.text}")
            return None
    
    def natural_language_to_sql(self, user_question: str) -> Optional[str]:
        """
        Convert natural language question to SQL query with enhanced understanding.
        
        Args:
            user_question: Natural language question
            
        Returns:
            SQL query string or None if error
        """
        # Add conversation context for better understanding
        context = ""
        if self.conversation_history:
            recent_context = self.conversation_history[-4:]
            context = "\n\nRecent conversation context:\n"
            for msg in recent_context:
                if msg['role'] == 'user':
                    context += f"User: {msg['content']}\n"
                else:
                    context += f"Assistant: {msg['content'][:200]}...\n"
        
        system_prompt = """You are an expert SQL query generator with deep understanding of natural language and music databases. 
        Your task is to intelligently interpret user questions and convert them into precise MySQL SQL queries.

Database Schema:
""" + self.schema_context + """

Key Abilities:
- Understand intent: Recognize what users really want even if phrased differently
- Handle ambiguity: Make reasonable assumptions based on context
- Recognize patterns: Identify common query types (lists, counts, comparisons, aggregations)
- Understand relationships: Know how tables connect (artists → albums → songs)
- Handle variations: Understand synonyms ("songs", "tracks", "music"), comparative language ("high", "low", "top", "best"), and quantity requests ("some", "few", "many", "all")

Query Generation Rules:
1. **CRITICAL SECURITY RULE: Generate ONLY SELECT queries. NEVER generate DELETE, DROP, UPDATE, INSERT, ALTER, CREATE, TRUNCATE, or any data modification queries.**
2. Generate ONLY the SQL query, no explanations or markdown
3. Do NOT include ```sql or ``` blocks
4. Use proper JOIN syntax to connect related tables when needed
5. Use appropriate WHERE, ORDER BY, GROUP BY, HAVING, LIMIT clauses
6. For "high/low" comparisons: Use > 0.7 for "high", < 0.3 for "low"
7. For "top N" or "best N": Use ORDER BY with LIMIT
8. For counts: Use COUNT() with appropriate grouping
9. For aggregations: Use SUM, AVG, MAX, MIN when requested
10. Default to reasonable limits (LIMIT 50) for large result sets unless specified
11. If truly unclear or cannot answer with schema, return "ERROR: Cannot generate valid SQL"

Common Patterns:
- "Show me all/List all" → SELECT * FROM table;
- "How many" → SELECT COUNT(*) FROM table WHERE...;
- "What are the top/best N" → SELECT * FROM ... ORDER BY ... DESC LIMIT N;
- "Find songs with high X" → SELECT ... JOIN song_features WHERE X > 0.7;
- "Tell me about artist Y" → SELECT * FROM artists WHERE name LIKE '%Y%' OR artist_id = Y;
- "Songs by X" → SELECT s.* FROM songs s JOIN artists a ON s.artist_id = a.artist_id WHERE a.name LIKE '%X%';

Examples:
- "Show me all artists" → SELECT * FROM artists LIMIT 50;
- "What songs are by artist with id 1?" → SELECT * FROM songs WHERE artist_id = 1;
- "How many songs have high energy?" → SELECT COUNT(*) FROM songs s JOIN song_features sf ON s.song_id = sf.song_id WHERE sf.energy > 0.7;
- "Find the top 10 most energetic songs" → SELECT s.*, sf.energy FROM songs s JOIN song_features sf ON s.song_id = sf.song_id ORDER BY sf.energy DESC LIMIT 10;
- "List albums released in 2020" → SELECT * FROM albums WHERE release_year = 2020;
- "What are songs with high danceability?" → SELECT s.* FROM songs s JOIN song_features sf ON s.song_id = sf.song_id WHERE sf.danceability > 0.7 LIMIT 50;"""

        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # Add context if available
        if context:
            messages.append({"role": "system", "content": context})
        
        messages.append({"role": "user", "content": user_question})
        
        sql_query = self.call_openrouter(messages)
        
        if sql_query:
            # Clean up the response - remove markdown code blocks if present
            sql_query = sql_query.strip()
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.startswith("```"):
                sql_query = sql_query[3:]
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            sql_query = sql_query.strip()
            # Remove trailing semicolon if present (we'll add it ourselves)
            if sql_query.endswith(';'):
                sql_query = sql_query[:-1]
        
        return sql_query
    
    def validate_sql_security(self, sql_query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that SQL query only contains SELECT statements for security.
        
        Args:
            sql_query: SQL query string to validate
            
        Returns:
            Tuple of (is_valid: bool, error_message: str or None)
        """
        if not sql_query or not sql_query.strip():
            return False, "Empty SQL query"
        
        # Normalize the query for checking
        query_upper = sql_query.strip().upper()
        
        # List of forbidden SQL keywords that modify data
        forbidden_keywords = [
            'DELETE', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 
            'UPDATE', 'REPLACE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE',
            'CALL', 'MERGE', 'LOCK', 'UNLOCK', 'COMMIT', 'ROLLBACK'
        ]
        
        # Check for forbidden keywords
        for keyword in forbidden_keywords:
            # Use word boundaries to avoid false positives (e.g., "SELECT" in "SELECTED")
            if f' {keyword} ' in f' {query_upper} ' or query_upper.startswith(f'{keyword} '):
                return False, f"Security violation: '{keyword}' statements are not allowed. Only SELECT queries are permitted."
        
        # Must start with SELECT
        if not query_upper.startswith('SELECT'):
            return False, "Only SELECT queries are allowed. Data modification operations are not permitted."
        
        # Check for semicolons that might allow multiple statements
        if sql_query.count(';') > 1:
            return False, "Multiple statements are not allowed. Only single SELECT queries are permitted."
        
        # Additional check: ensure no subqueries with forbidden operations
        # This is a basic check - more sophisticated parsing could be added
        for keyword in ['DELETE', 'DROP', 'INSERT', 'UPDATE']:
            if keyword in query_upper:
                return False, f"Security violation: '{keyword}' detected in query. Only SELECT queries are permitted."
        
        return True, None
    
    def execute_sql(self, sql_query: str) -> Tuple[Optional[list], Optional[str]]:
        """
        Execute SQL query on the database with security validation.
        
        Args:
            sql_query: SQL query string
            
        Returns:
            Tuple of (results list or None, error message or None)
        """
        if not self.connection or not self.connection.is_connected():
            return None, "Database not connected"
        
        # Security validation: Only allow SELECT queries
        is_valid, security_error = self.validate_sql_security(sql_query)
        if not is_valid:
            return None, security_error
        
        try:
            self.cursor.execute(sql_query)
            
            # Since we validated it's SELECT, fetch results
            results = self.cursor.fetchall()
            return results, None
                
        except mysql.connector.Error as err:
            return None, str(err)
    
    def _analyze_query_intent(self, question: str) -> Dict[str, Any]:
        """
        Analyze the intent and type of the user's question for better understanding.
        
        Args:
            question: User question
            
        Returns:
            Dictionary with intent analysis
        """
        system_prompt = """Analyze this music-related question to understand the user's intent. Return a JSON object with:
- "query_type": "database_lookup" | "web_search" | "both" | "conversational"
- "needs_db": true/false
- "needs_web": true/false
- "question_category": "list", "count", "comparison", "search", "info", "trend", "other"
- "entities": list of artist names, song titles, or keywords mentioned
- "confidence": 0.0-1.0

Respond ONLY with valid JSON, no other text."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
        
        response = self.call_openrouter(messages)
        
        if response:
            try:
                # Extract JSON from response
                if "{" in response and "}" in response:
                    json_start = response.find("{")
                    json_end = response.rfind("}") + 1
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except:
                pass
        
        # Default fallback
        return {
            "query_type": "database_lookup",
            "needs_db": True,
            "needs_web": False,
            "question_category": "other",
            "entities": [],
            "confidence": 0.5
        }
    
    def should_search_web(self, question: str, db_results: Optional[list] = None) -> Tuple[bool, Optional[str]]:
        """
        Determine if web search is needed and generate search query.
        
        Args:
            question: User question
            db_results: Results from database query (if any)
            
        Returns:
            Tuple of (should_search: bool, search_query: str or None)
        """
        system_prompt = """You are an intelligent assistant that determines whether a user's music-related question needs additional web search information.

Consider web search if the question asks about:
- Latest music trends, charts, or news
- Recent releases or updates about artists/albums
- Music theory, genres, or cultural context
- Artist biographies, achievements, or background
- Album reviews, ratings, or critical reception
- Music events, concerts, or tours
- Similar artists or recommendations based on external knowledge
- Music industry information or statistics

Do NOT search if:
- Question can be fully answered with database data alone
- Question is about database structure or queries
- Results already provide comprehensive information

If web search is needed, generate a concise search query (2-4 words).
Respond in JSON format: {"search_needed": true/false, "search_query": "query or null"}"""

        context = f"Database results available: {len(db_results) if db_results else 0} records\n"
        if db_results and len(db_results) > 0:
            context += f"Sample data: {str(db_results[0])[:200]}\n"
        
        user_message = f"""User question: {question}

{context}

Should I search the web for additional music information? If yes, what search query should I use?"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        response = self.call_openrouter(messages)
        
        if not response:
            return False, None
        
        try:
            # Try to parse JSON response
            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                return result.get("search_needed", False), result.get("search_query")
            else:
                # Fallback: check if response indicates search needed
                if "true" in response.lower() or "yes" in response.lower():
                    # Try to extract search query
                    if "search_query" in response.lower():
                        # Simple extraction
                        return True, question[:50]  # Use question as fallback
                    return True, None
        except:
            pass
        
        return False, None
    
    def search_web(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """
        Search the web for music-related information.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of search result dictionaries with 'title', 'body', and 'href'
        """
        try:
            with DDGS() as ddgs:
                # Add music context to query
                music_query = f"music {query}"
                results = []
                for result in ddgs.text(music_query, max_results=max_results):
                    results.append({
                        'title': result.get('title', ''),
                        'body': result.get('body', ''),
                        'href': result.get('href', '')
                    })
                return results
        except Exception as e:
            print(f"Web search error: {e}")
            return []
    
    def synthesize_response(self, user_question: str, db_results: Optional[list], 
                           sql_query: Optional[str], web_results: Optional[List[Dict]] = None) -> Optional[str]:
        """
        Synthesize a comprehensive response combining database and web information with natural, human-like language.
        
        Args:
            user_question: Original user question
            db_results: Results from database query
            sql_query: SQL query that was executed
            web_results: Results from web search
            
        Returns:
            Natural language response combining all information
        """
        system_prompt = """You are a friendly, knowledgeable music expert assistant who loves talking about music in a natural, conversational way. You help users understand their music database and provide insights about music in general.

Your Personality:
- Warm, enthusiastic, and engaging - like talking to a music-loving friend
- Use natural speech patterns: contractions ("I've", "you'll", "it's"), casual expressions, and conversational flow
- Show genuine interest in music and helpfulness to users
- Avoid robotic or overly formal language
- Use varied sentence structures - mix short punchy statements with longer explanatory ones

Response Guidelines:
1. **Start Naturally**: Begin with a friendly acknowledgment or direct answer to their question
2. **Primary Source**: Base your answer primarily on database results when available
3. **Web Enhancement**: Weave in web information naturally when it adds valuable context (trends, recent info, explanations)
4. **Blend Seamlessly**: Don't say "From the database..." or "According to web search..." - just present information naturally
5. **Numbers Matter**: When presenting data, make numbers meaningful ("10 energetic songs" not just "10 songs")
6. **Highlight Interesting**: Point out interesting patterns or standout items naturally
7. **Use Examples**: When listing items, mention 2-3 key examples before saying "and X more"
8. **Conversational Transitions**: Use natural connectors like "On another note...", "Interestingly...", "By the way..."
9. **Handle Empty Results**: If no data found, acknowledge it warmly and offer alternatives or suggestions
10. **Formatting**: Use bullet points for lists, line breaks for readability, but keep it natural

Tone Examples:
- "I found some great energetic tracks for you!"
- "Looking at your collection, I see..."
- "That's an interesting question! Let me check..."
- "Unfortunately, I don't see any results for that, but..."

Be conversational, engaging, and helpful - like a knowledgeable friend helping someone explore their music collection."""

        # Format SQL info (hidden from user, used for context)
        sql_info = f"SQL Query executed: {sql_query}" if sql_query else ""
        
        # Format database results in a more contextual way
        db_context = ""
        if db_results is not None:
            if len(db_results) == 0:
                db_context = "DATABASE: No results found. The query returned empty."
            else:
                # Include summary info
                result_summary = f"Found {len(db_results)} result(s)"
                if len(db_results) == 1:
                    result_summary = "Found 1 result"
                
                # Extract key fields for context
                sample_data = db_results[:15]  # Show more for better context
                db_context = f"DATABASE RESULTS ({len(db_results)} total):\n{result_summary}\n\nData:\n{json.dumps(sample_data, indent=2, default=str)}"
                
                if len(db_results) > 15:
                    db_context += f"\n(Showing first 15 of {len(db_results)} total results)"
                
                # Add helpful metadata hints
                if db_results and isinstance(db_results[0], dict):
                    key_fields = list(db_results[0].keys())[:5]
                    db_context += f"\n\nKey fields in results: {', '.join(key_fields)}"
        else:
            db_context = "DATABASE: No query was executed (question may not require database lookup)."

        # Format web results more naturally
        web_context = ""
        if web_results and len(web_results) > 0:
            web_context = "\n\nWEB SEARCH RESULTS (for additional context):\n"
            for i, result in enumerate(web_results, 1):
                title = result.get('title', 'No title')
                body = result.get('body', 'No description')[:400]  # More context
                web_context += f"\n[{i}] {title}\n{body}...\n"
        else:
            web_context = "\n\nWEB SEARCH: Not performed (question can be answered from database alone)."

        # Build user message with better structure
        user_message = f"""USER QUESTION: "{user_question}"

{sql_info if sql_query else ""}

{db_context}
{web_context}

INSTRUCTIONS:
Based on the user's question and the data above, provide a natural, conversational response that:
- Directly answers their question in a friendly, human way
- Uses the database results as your primary source
- Naturally incorporates relevant web information if it enhances the answer
- Sounds like you're a knowledgeable music friend helping them out
- Uses varied, natural language - not robotic or formal
- Makes numbers and data meaningful and interesting
- If no results, offer helpful alternatives or explain why

Remember: Write like you're talking to a friend about music, not like a database reporting tool!"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Add conversation history for context
        if self.conversation_history:
            messages = self.conversation_history[-3:] + messages
        
        response = self.call_openrouter(messages)
        
        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_question})
        if response:
            self.conversation_history.append({"role": "assistant", "content": response})
        
        # Keep history manageable (last 10 messages)
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        
        return response
    
    def ask(self, question: str) -> Dict[str, Any]:
        """
        Main method to process a user question with enhanced intelligence.
        
        Args:
            question: Natural language question
            
        Returns:
            Dictionary with 'answer', 'sql_query', 'db_results', 'web_results', 'used_web_search'
        """
        result = {
            'answer': None,
            'sql_query': None,
            'db_results': None,
            'web_results': None,
            'used_web_search': False,
            'error': None
        }
        
        print(f"\n🔍 Question: {question}")
        
        # Step 0: Analyze query intent first (for better understanding)
        query_intent = self._analyze_query_intent(question)
        print(f"🎯 Query intent: {query_intent.get('query_type', 'unknown')} - {query_intent.get('question_category', 'other')}")
        
        # Step 1: Convert to SQL (only if needed based on intent)
        sql_query = None
        db_results = None
        error = None
        
        if query_intent.get('needs_db', True):
            print("🔄 Converting to SQL...")
            sql_query = self.natural_language_to_sql(question)
            result['sql_query'] = sql_query
            
            # Only execute SQL if a valid query was generated
            if sql_query and not sql_query.startswith("ERROR"):
                print(f"📝 Generated SQL: {sql_query}")
                
                # Step 2: Execute SQL
                print("⚡ Executing SQL query...")
                db_results, error = self.execute_sql(sql_query)
                result['db_results'] = db_results
                
                if error:
                    result['error'] = f"SQL Error: {error}"
            else:
                result['error'] = "Could not generate valid SQL query"
                error = result['error']
        else:
            print("ℹ️  Skipping SQL generation based on query intent")
        
        # Step 3: Determine if web search is needed (use intent analysis for smarter decisions)
        print("🌐 Analyzing if web search is needed...")
        should_search = query_intent.get('needs_web', False)
        search_query = None
        
        # Still use the detailed analysis, but give weight to intent analysis
        if should_search or query_intent.get('query_type') == 'web_search':
            should_search, search_query = self.should_search_web(question, db_results)
        elif db_results is None or (isinstance(db_results, list) and len(db_results) == 0):
            # If no DB results, check if web search would help
            should_search, search_query = self.should_search_web(question, db_results)
        
        web_results = None
        if should_search and search_query:
            print(f"🔍 Searching web for: {search_query}")
            web_results = self.search_web(search_query)
            result['web_results'] = web_results
            result['used_web_search'] = True
            if web_results:
                print(f"✓ Found {len(web_results)} web results")
        else:
            print("ℹ️  Web search not needed or no query generated")
        
        # Step 4: Synthesize comprehensive response
        print("💬 Synthesizing comprehensive response...")
        answer = self.synthesize_response(question, db_results, sql_query, web_results)
        
        if not answer:
            # Fallback response
            if db_results:
                answer = f"Here are the results from the database:\n{json.dumps(db_results[:5], indent=2, default=str)}"
            elif web_results:
                answer = f"I found some information online:\n{web_results[0].get('body', '')[:500]}"
            else:
                answer = "I couldn't find information to answer your question. Please try rephrasing or check if the data is available."
        
        result['answer'] = answer
        return result
    
    def get_lyrics_by_name(self, song_name: str, artist_name: Optional[str] = None) -> Optional[str]:
        """
        Get song lyrics by song name using OpenRouter DeepSeek.
        
        Args:
            song_name: Name of the song
            artist_name: Optional artist name for better accuracy
            
        Returns:
            Lyrics text or None if error
        """
        lyrics = self.audio_transcriber.get_lyrics_by_name(song_name, artist_name)
        if lyrics:
            self.current_lyrics = lyrics
            self.current_translation = None  # Reset translation
        return lyrics
    
    def transcribe_audio(self, audio_path: str = None, song_name: str = None, artist_name: Optional[str] = None) -> Optional[str]:
        """
        Get lyrics - supports song name (preferred) or audio path (legacy).
        
        Args:
            audio_path: Legacy parameter (not used)
            song_name: Name of the song (preferred method)
            artist_name: Optional artist name
            
        Returns:
            Lyrics text or None if error
        """
        if song_name:
            return self.get_lyrics_by_name(song_name, artist_name)
        else:
            print("⚠️  Please provide song name instead of audio file")
            return None
    
    def translate_lyrics(self, lyrics: Optional[str] = None, target_language: str = "Spanish") -> Optional[str]:
        """
        Translate lyrics to target language using OpenRouter API.
        
        Args:
            lyrics: Lyrics to translate (uses current_lyrics if None)
            target_language: Target language name (e.g., "Spanish", "French", "Japanese")
            
        Returns:
            Translated lyrics or None if error
        """
        if lyrics is None:
            lyrics = self.current_lyrics
        
        if not lyrics:
            return None
        
        translated = self.lyrics_translator.translate(lyrics, target_language)
        if translated:
            self.current_translation = translated
        return translated
    
    def generate_lyrics_pdf(self, lyrics: str, output_path: str, title: str = "Song Lyrics", 
                           is_translation: bool = False, original_language: str = "Original",
                           target_language: str = "Translated") -> bool:
        """
        Generate a PDF file with lyrics.
        
        Args:
            lyrics: Lyrics text to include in PDF
            output_path: Path where PDF will be saved
            title: Title for the PDF
            is_translation: Whether this is a translation
            original_language: Original language name
            target_language: Target language name (if translation)
            
        Returns:
            True if successful, False otherwise
        """
        return self.pdf_generator.generate(
            lyrics=lyrics,
            output_path=output_path,
            title=title,
            is_translation=is_translation,
            original_language=original_language,
            target_language=target_language
        )
    
    def interactive_mode(self):
        """Run the chatbot in interactive mode."""
        print("\n" + "="*60)
        print("🎵 Music Database Chatbot")
        print("="*60)
        print("Type your questions about the music database.")
        print("\n📝 New Features:")
        print("  • Get lyrics: 'lyrics <song_name>' or 'lyrics <song_name> by <artist>' to get song lyrics")
        print("  • Translate: 'translate <language>' to translate current lyrics (e.g., 'translate Spanish')")
        print("  • Download PDF: 'download <filename>' to save lyrics as PDF")
        print("  • Show lyrics: 'show lyrics' to display current lyrics")
        print("\nType 'exit', 'quit', or 'bye' to stop.\n")
        
        if not self.connect_db():
            print("Failed to connect to database. Exiting.")
            return
        
        try:
            while True:
                question = input("\nYou: ").strip()
                
                if not question:
                    continue
                
                if question.lower() in ['exit', 'quit', 'bye']:
                    print("\n👋 Goodbye!")
                    break
                
                # Handle new features
                question_lower = question.lower().strip()
                
                # Get lyrics by song name
                if question_lower.startswith('lyrics '):
                    song_input = question[7:].strip()
                    # Parse "song by artist" format
                    if ' by ' in song_input.lower():
                        parts = song_input.rsplit(' by ', 1)
                        song_name = parts[0].strip()
                        artist_name = parts[1].strip()
                    else:
                        song_name = song_input
                        artist_name = None
                    
                    lyrics = self.get_lyrics_by_name(song_name, artist_name)
                    if lyrics:
                        print(f"\n🎵 Lyrics for: {song_name}" + (f" by {artist_name}" if artist_name else ""))
                        print("="*60)
                        print(lyrics)
                        print("="*60)
                        print(f"\n✓ Lyrics fetched successfully! ({len(lyrics)} characters)")
                        print("💡 You can now:")
                        print("   • Translate: 'translate <language>'")
                        print("   • Download PDF: 'download <filename>.pdf'")
                    else:
                        print("\n✗ Failed to fetch lyrics. Please check the song name and try again.")
                    continue
                
                # Translate lyrics
                if question_lower.startswith('translate '):
                    if not self.current_lyrics:
                        print("\n⚠️  No lyrics available. Please upload an audio file first using 'upload <file_path>'")
                        continue
                    
                    target_lang = question[10:].strip()
                    if not target_lang:
                        target_lang = "Spanish"  # Default
                    
                    translated = self.translate_lyrics(target_language=target_lang)
                    if translated:
                        print(f"\n🌐 Translation ({target_lang}):\n")
                        print("="*60)
                        print(translated)
                        print("="*60)
                        print(f"\n✓ Translation completed!")
                        print("💡 Download PDF: 'download <filename>.pdf'")
                    else:
                        print("\n✗ Translation failed. Please try again.")
                    continue
                
                # Download PDF
                if question_lower.startswith('download '):
                    filename = question[9:].strip().strip('"').strip("'")
                    if not filename:
                        filename = "lyrics.pdf"
                    
                    # Ensure .pdf extension
                    if not filename.endswith('.pdf'):
                        filename += '.pdf'
                    
                    # Determine what to save
                    if self.current_translation and self.current_lyrics:
                        # Save both original and translation
                        success = self.pdf_generator.generate_combined(
                            original_lyrics=self.current_lyrics,
                            translated_lyrics=self.current_translation,
                            output_path=filename,
                            title="Song Lyrics",
                            original_language="Original",
                            target_language="Translated"
                        )
                        if success:
                            print(f"\n✓ PDF with original and translation saved: {os.path.abspath(filename)}")
                    elif self.current_translation:
                        # Save translation only
                        success = self.generate_lyrics_pdf(
                            lyrics=self.current_translation,
                            output_path=filename,
                            title="Song Lyrics - Translation",
                            is_translation=True,
                            original_language="Original",
                            target_language="Translated"
                        )
                        if success:
                            print(f"\n✓ Translation PDF saved: {os.path.abspath(filename)}")
                    elif self.current_lyrics:
                        # Save original only
                        success = self.generate_lyrics_pdf(
                            lyrics=self.current_lyrics,
                            output_path=filename,
                            title="Song Lyrics",
                            is_translation=False,
                            original_language="Original"
                        )
                        if success:
                            print(f"\n✓ Lyrics PDF saved: {os.path.abspath(filename)}")
                    else:
                        print("\n⚠️  No lyrics available. Please upload an audio file first.")
                    continue
                
                # Show current lyrics
                if question_lower in ['show lyrics', 'lyrics', 'show']:
                    if self.current_translation:
                        print(f"\n🌐 Current Translation:\n")
                        print("="*60)
                        print(self.current_translation)
                        print("="*60)
                    elif self.current_lyrics:
                        print(f"\n🎵 Current Lyrics:\n")
                        print("="*60)
                        print(self.current_lyrics)
                        print("="*60)
                    else:
                        print("\n⚠️  No lyrics available. Please upload an audio file first.")
                    continue
                
                # Regular chatbot question
                result = self.ask(question)
                if result and result.get('answer'):
                    print(f"\n🤖 Bot: {result['answer']}")
                    if result.get('error'):
                        print(f"⚠️  Note: {result['error']}")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        finally:
            self.disconnect_db()

from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("OPENROUTER_MODEL")

def main():
    # Database configuration - use environment variables
    db_config = {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT")),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME")
    }
    
    # OpenRouter configuration
    api_key = API_KEY
    model = MODEL
    
    # Create and run chatbot
    chatbot = MusicChatbot(db_config, api_key, model)
    
    # Check if question provided as command line argument
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        if not chatbot.connect_db():
            print("Failed to connect to database.")
            return
        result = chatbot.ask(question)
        if result and result.get('answer'):
            print(f"\n🤖 Bot: {result['answer']}")
            if result.get('error'):
                print(f"⚠️  Note: {result['error']}")
        chatbot.disconnect_db()
    else:
        # Run in interactive mode
        chatbot.interactive_mode()


if __name__ == "__main__":
    main()

