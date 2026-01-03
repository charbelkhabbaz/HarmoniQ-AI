# YouTube Lyrics Tool - Technical Explanation

## Overview

The YouTube Lyrics tool is an integrated feature within HarmoniQ AI that automatically extracts song lyrics from YouTube video URLs. The tool retrieves video metadata, intelligently parses song and artist information from video titles, fetches complete lyrics using AI-powered language models, and automatically generates formatted PDF documents for user download.

## Architecture & Workflow

The YouTube Lyrics tool operates through a multi-stage processing pipeline that transforms a YouTube URL into formatted lyrics with an accompanying PDF document.

### Stage 1: Video Metadata Extraction

**Technology:** `yt_dlp` (YouTube Downloader Library)

When a user provides a YouTube URL, the tool first extracts video metadata without downloading the video content:

1. **Video Information Retrieval:**
   - Uses `yt_dlp.YoutubeDL()` with quiet mode to extract video metadata
   - Retrieves video title, uploader, description, duration, view count, and other metadata
   - Performs this operation in non-download mode for efficiency

2. **Title Cleaning Process:**
   - Applies regular expressions to remove common YouTube suffixes and prefixes
   - Eliminates metadata tags such as "(Lyrics)", "[Official Video]", "(HD)", "(4K)", "(Remastered)", "(MV)", etc.
   - Normalizes the title for accurate parsing
   - Example: "Adele - Skyfall (Lyrics)" → "Adele - Skyfall"

### Stage 2: Intelligent Title Parsing

**Technology:** Regular Expressions + String Processing

The tool implements sophisticated parsing logic to extract song name and artist from video titles:

1. **Format Recognition:**
   - Recognizes the standard YouTube format: "Artist - Song Name"
   - Handles edge cases where format might differ or information is incomplete
   - Supports titles with or without delimiters

2. **Parsing Algorithm:**
   - Splits title by " - " delimiter to separate artist and song
   - Assumes first part is artist name and second part is song name (YouTube standard)
   - Handles cases where user provides partial information (only song name or only artist)
   - Falls back to entire title as song name if no delimiter is found

3. **Flexible Input Handling:**
   - Users can optionally provide song name and/or artist name
   - System prioritizes user input when provided, supplementing missing information from video title
   - Smart merging of user input with extracted metadata

### Stage 3: Lyrics Retrieval via AI

**Technology:** DeepSeek LLM via OpenRouter API

The core lyrics retrieval is powered by an AI language model:

1. **API Integration:**
   - Uses OpenRouter as an API gateway to access DeepSeek chat model (v3.1)
   - Implements RESTful API calls with authentication headers
   - Maintains conversation history for context (limited to last 10 messages)

2. **Prompt Engineering:**
   - Constructs specialized system prompts that instruct the model to act as an expert lyrics database
   - Enforces strict formatting requirements:
     - Section labels in ALL CAPS (INTRO, VERSE 1, VERSE 2, CHORUS, BRIDGE, OUTRO)
     - Proper spacing between sections
     - Complete lyrics including all verses, choruses, and bridges
     - Support for both Arabic and English songs

3. **Query Construction:**
   - Formats query as "Song: [song_name]\nArtist: [artist_name]"
   - Sends structured request to ensure accurate results
   - Handles cases where artist name is optional

4. **Response Processing:**
   - Cleans AI response by removing markdown code blocks if present
   - Strips leading/trailing whitespace
   - Validates that lyrics were actually returned (not error messages)

### Stage 4: PDF Generation

**Technology:** PDFGenerator class (ReportLab-based)

Upon successful lyrics retrieval, the tool automatically generates a formatted PDF document:

1. **File Management:**
   - Creates unique filename based on song name and artist
   - Sanitizes filenames by replacing spaces with underscores and removing special characters
   - Stores PDF in system temporary directory

2. **PDF Generation Process:**
   - Uses PDFGenerator class with ReportLab library
   - Applies professional formatting:
     - Title header with song name and artist
     - Well-structured layout with proper margins
     - Organized section headers matching the lyrics format
     - Clean, readable typography

3. **Output Structure:**
   - Title format: "[Song Name] by [Artist Name]"
   - Preserves lyrics formatting from AI response
   - Creates publication-quality document

### Stage 5: Response Formatting & Delivery

**Technology:** JSON serialization + Streamlit UI

The tool returns structured JSON containing all relevant information:

1. **JSON Response Structure:**
   ```json
   {
       "lyrics": "formatted lyrics text",
       "pdf_path": "absolute/path/to/lyrics.pdf",
       "song_name": "Song Name",
       "artist_name": "Artist Name",
       "message": "Success message"
   }
   ```

2. **Error Handling:**
   - Returns error JSON with descriptive messages if any stage fails
   - Handles YouTube extraction errors, API failures, and PDF generation issues
   - Provides user-friendly error messages

3. **User Interface Integration:**
   - Displayed in Streamlit chat interface with formatted markdown
   - Shows lyrics with proper section headers
   - Provides PDF download button
   - Displays song title and artist information prominently

## Key Technologies Used

1. **yt_dlp**: Python library for YouTube metadata extraction
2. **DeepSeek LLM**: Large language model accessed via OpenRouter API for lyrics retrieval
3. **OpenRouter API**: API gateway providing access to various LLM models
4. **ReportLab (PDFGenerator)**: Python library for PDF document generation
5. **Regular Expressions (re)**: Pattern matching for title cleaning and parsing
6. **JSON**: Data serialization for structured responses

## Technical Features

### 1. Robust Error Handling
- Handles invalid YouTube URLs gracefully
- Manages API timeouts and failures
- Provides meaningful error messages to users

### 2. Smart Parsing
- Adapts to various YouTube title formats
- Handles missing or partial information
- Validates and corrects extracted data

### 3. Automatic PDF Generation
- No manual user intervention required
- Professional document formatting
- Immediate availability for download

### 4. Multi-language Support
- Supports English and Arabic lyrics
- Handles various character sets and formatting styles

### 5. Efficient Processing
- Metadata-only extraction (doesn't download video)
- Fast API calls with timeout management
- Optimized PDF generation

## Use Cases

1. **Music Discovery**: Users find a song on YouTube and want lyrics
2. **Educational**: Music students need lyrics for learning purposes
3. **Personal Use**: Creating personal lyric collections
4. **Reference**: Quick access to lyrics while listening to music

## Limitations & Considerations

1. **Copyright**: Lyrics are retrieved from AI knowledge base, respecting copyright concerns
2. **Accuracy**: Depends on AI model's training data and knowledge
3. **API Dependency**: Requires active internet connection and API access
4. **Title Parsing**: May occasionally misparse complex or non-standard title formats

## Future Enhancements

Potential improvements could include:
- Real-time lyrics synchronization with video playback
- Multiple language translations
- Lyrics search functionality
- Integration with music databases for enhanced metadata
- Batch processing for multiple videos

---

*This tool demonstrates the integration of video metadata extraction, AI-powered content retrieval, and automated document generation to provide a seamless user experience for accessing song lyrics from YouTube videos.*

