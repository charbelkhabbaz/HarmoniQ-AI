# LLM Project - Harmonic AI

AI Music Assistant built with Streamlit and Gemini LLM.

## Quick Start

### 1. Install Dependencies

```bash
cd code
pip install -r requirements.txt
```

### 2. Create .env File

**Important:** You must create a `.env` file before running the app.

Copy the example environment file:

```bash
cd code
copy env.example .env
```

Edit the `.env` file and add your API keys:
- `GEMINI_API_KEY` - **Required** (get from [Google AI Studio](https://aistudio.google.com/app/apikey))
- `OPENROUTER_API_KEY` - Optional
- Database credentials if using database features

The `.env` file should be located in the `code/` directory.

### 3. Run the Application

```bash
cd code
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Project Structure

- `code/app.py` - Main Streamlit application (entry point)
- `code/requirements.txt` - Python dependencies
- `code/env.example` - Environment variables template
- `code/.env` - Your environment variables (create this file from env.example)
- `additional/` - Additional music recognition modules

## Features

- Music transcription and analysis
- Lyrics translation
- Mood classification
- Audio processing tools
- Music theory chatbot with RAG

## Requirements

- Python 3.8+
- See `code/requirements.txt` for full dependency list
