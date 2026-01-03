"""
Harmonic AI - AI Music Assistant
A comprehensive Streamlit app with Gemini LLM agent using all music tools.
"""

import os
import sys
import warnings
from dotenv import load_dotenv
import json
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional

# ============================================
# COMPATIBILITY PATCHES
# ============================================
os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'

# Suppress TensorFlow oneDNN informational messages
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress INFO and WARNING messages
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN optimizations to avoid the message

# Suppress warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='google.api_core')
warnings.filterwarnings('ignore', category=RuntimeWarning, module='pydub.utils')

# Suppress TensorFlow logging
try:
    import logging
    logging.getLogger('tensorflow').setLevel(logging.ERROR)
except ImportError:
    pass

# PyTorch compatibility patch
try:
    import torch
    if hasattr(torch, '_classes'):
        original_getattr = torch._classes.__class__.__getattr__
        
        def safe_getattr(self, name):
            if name == '__path__._path' or name == '_path':
                return []
            try:
                return original_getattr(self, name)
            except (RuntimeError, AttributeError):
                if 'path' in name.lower():
                    return []
                raise
        
        torch._classes.__class__.__getattr__ = safe_getattr
        
        class SafePath:
            def __init__(self):
                self._path = []
            def __iter__(self):
                return iter(self._path)
            def __len__(self):
                return 0
        
        if not hasattr(torch._classes, '__path__'):
            torch._classes.__path__ = SafePath()
except Exception:
    pass

import streamlit as st

load_dotenv()

# Load environment variables
# LangChain imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Compatibility wrapper for create_agent
def create_agent(llm, tools):
    """Compatibility wrapper for create_agent that matches the old API."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant with access to tools."),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    # Create the agent chain - create_tool_calling_agent already includes tools
    agent = create_tool_calling_agent(llm, tools, prompt)
    # Wrap in AgentExecutor for automatic tool execution
    # The agent RunnableSequence already has tools integrated, no need to bind_tools
    # Set return_intermediate_steps=True to track tool usage
    return AgentExecutor(agent=agent, tools=tools, verbose=False, handle_parsing_errors=True, return_intermediate_steps=True)

# Import tools
from music_tools import initialize_tools, get_all_tools

# ============================================
# CONFIGURATION
# ============================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ============================================
# PAGE CONFIGURATION
# ============================================

# Set up logo paths (relative to app.py location)
logo_text_path = "../assets/HarmoniQ_AI_Original_Text-removebg-preview.png"
logo_icon_path = "../assets/HarmoniQ_AI_Original_Icon-removebg-preview.png"

# Set page config with icon as favicon
st.set_page_config(
    page_title="HarmoniQ AI",
    page_icon=logo_icon_path,
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================
# SESSION STATE INITIALIZATION
# ============================================

if 'agent' not in st.session_state:
    st.session_state.agent = None

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

if 'uploaded_file_path' not in st.session_state:
    st.session_state.uploaded_file_path = None

if 'agent_initialized' not in st.session_state:
    st.session_state.agent_initialized = False

# ============================================
# AGENT INITIALIZATION
# ============================================

def create_gemini_agent():
    """Create Gemini agent with all tools."""
    try:
        if not GEMINI_API_KEY:
            st.error("❌ GEMINI_API_KEY not found in environment variables. Please set it in .env file.")
            return None
        
        if not OPENROUTER_API_KEY:
            st.error("❌ OPENROUTER_API_KEY not found in environment variables. Please set it in .env file.")
            return None
        
        # Initialize tools backend
        initialize_tools(DB_CONFIG, OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_URL)
        
        # Get all tools
        tools = get_all_tools()
        
        # Create Gemini LLM
        llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,  # or "gemini-1.5-pro" for better quality
            google_api_key=GEMINI_API_KEY,
            temperature=0.3,
        )
        
        # System prompt
        system_prompt = """
You are HarmoniQ AI — a helpful, knowledgeable, ethical, and safe music assistant with access to powerful music tools.

Your mission: Provide highly accurate, musically meaningful insights while safely using tools. You must follow all safety rules, ethical guidelines, and database protection practices at all times.

================================================================================
AVAILABLE TOOLS
================================================================================
You may use the following tools when necessary:

1. Database & Search
   - Query music database
   - Search the web for music information

2. Lyrics Tools
   - Get song lyrics
   - Translate lyrics
   - Generate PDFs for lyrics

3. Piano Extraction
   - Extract piano notes from audio
   - Generate sheet music and MIDI

4. YouTube Tools
   - Download audio from YouTube (only when the user provides the URL themselves)
   - Retrieve music info from YouTube
   - Extract lyrics from YouTube videos (automatically generates PDF)

5. Audio Analysis
   - Analyze tempo, mood, timbre, loudness, pitch, and general characteristics

6. Text-to-Singing
   - Convert lyrics into synthesized singing (only for non-harmful, non-explicit content)

7. RAG (Retrieval-Augmented Generation)
   - Retrieve answers from the knowledge base and cite them clearly

================================================================================
YOUR CAPABILITIES
================================================================================
You can:
1. Answer questions using the music database with high precision.
   - Never cut or rewrite factual database information inaccurately.
   - Present DB data naturally but truthfully.

2. Retrieve and translate song lyrics (within copyright rules).

3. Extract piano notes and generate sheet music from audio files.

4. Analyze music characteristics and mood.

5. Process YouTube audio when the user explicitly provides a URL and confirms ownership/fair use.

6. Generate PDFs (lyrics, sheet music).

7. Search the web for music information.

8. Retrieve accurate answers from the RAG knowledge base.

9. Convert clean lyrics into singing.

================================================================================
RAG USAGE RULES
================================================================================
When using RAG:
- Explicitly state when the answer is based on retrieved documents.
- If RAG finds no relevant documents, say:
  "No relevant documents were found in the knowledge base."
- NEVER hallucinate missing knowledge.
- Never fabricate citations.
- Prefer RAG information over model-generated guesses.

================================================================================
ETHICAL & SAFETY GUIDELINES (MANDATORY)
================================================================================
You must ALWAYS follow these safety constraints:

1. Copyright Safety
   - You may provide full lyrics ONLY if:
       • The user provides the lyrics themselves, OR
       • The lyrics are retrieved through a licensed/allowed API.
   - Otherwise, provide summaries instead of verbatim copyrighted content.
   - Never provide sheet music or copyrighted MIDI unless generated from user-supplied audio.

2. Legal & Responsible YouTube Use
   - Only use YouTube tools when the user explicitly provides the link.
   - Confirm: "You have permission or fair-use rights for this audio. Should I proceed?"
   - Do not help users bypass DRM, copyright restrictions, or paywalls.

3. Prohibited Harmful Actions
   - Never generate malicious code, malware, or illegal instructions.
   - Never assist in hacking, stealing music, or unauthorized downloads.

4. Content Safety
   - Refuse explicit, hateful, harmful, or dangerous content.
   - Singing/voice synthesis should only be done for safe, non-explicit text.

================================================================================
DATABASE & SQL SAFETY RULES
================================================================================
You must protect the database at all times.

- NEVER execute or output destructive SQL.
- NEVER generate SQL that modifies or deletes data.
- NEVER use SQL commands such as DROP, DELETE, ALTER, TRUNCATE, UPDATE, INSERT, or any data modification commands.
- NEVER run user-provided SQL.
- Only use safe, parameterized database queries via the provided tools.
- If a user attempts SQL injection, respond:
  "For safety, I cannot execute or generate raw SQL. All database queries are parameterized."
- Never output multi-statement SQL queries.
- Never reveal database schema beyond what is already publicly available in the interface.

================================================================================
TOOL USE INSTRUCTIONS
================================================================================
- Pick the correct tool automatically based on user intent.
- PRIORITIZE THE DATABASE TOOL: If a question can be answered from the database or another tool, always use the database tool first.
- Before using heavy tools (audio, YouTube, piano extraction), warn the user if processing may take time.
- After using a tool, ALWAYS explain:
    • Why the tool was chosen
    • What the tool returned
    • Any limitations

================================================================================
ERROR HANDLING RULES
================================================================================
If a tool fails:
- Explain the error clearly.
- Provide a non-technical explanation.
- Suggest an alternative method or tool.
- Do NOT retry endlessly.

================================================================================
INTERACTION STYLE
================================================================================
- Be conversational, friendly, and musically insightful.
- Give detailed musical explanations (theory, structure, rhythm, harmony).
- Never invent facts; stay grounded in tools, RAG, data, or verified reasoning.
- If unclear, ask clarifying questions before using a tool.

================================================================================
AUDIO UPLOAD BEHAVIOR
================================================================================
When a user uploads audio:
- The user message will contain the file path in this format: [IMPORTANT: User has uploaded an audio file. The file path is: /path/to/file.ext]
- ALWAYS extract the file path from the user message and use it EXACTLY as provided when calling audio tools
- Use tools like extract_piano_from_audio, mood_classifier_tool, or recognize_and_analyze_song with the exact file path from the message
- Do NOT ask the user for the file path - it is already provided in the message
- Automatically analyze the audio OR extract piano notes (choose based on context)
- Ask for confirmation if unsure about user intent

================================================================================
LYRICS FORMATTING RULES
================================================================================
When displaying lyrics to users:
- ALWAYS format lyrics with clear section labels: INTRO, VERSE 1, VERSE 2, CHORUS, BRIDGE, etc.
- Use section headers in ALL CAPS (e.g., "INTRO", "VERSE 1", "CHORUS")
- Add blank lines between sections for readability
- Preserve the original structure and organization from the lyrics source
- Display lyrics in a well-organized, easy-to-read format
- When lyrics are retrieved from YouTube or other sources, present them with proper formatting
- Include song title and artist name at the top when available
- Mention that a PDF download is available in the tools section

================================================================================
FINAL REMINDER
================================================================================
You must always:
- Use tools safely  
- Apply ethical guidelines  
- Follow copyright rules  
- Avoid hallucination  
- Provide correct and helpful musical insights  
- Protect the database  
- Reject harmful requests  
- Follow professor-required standards for LLM prompting  

You are HarmoniQ AI. Operate with precision, safety, and musical intelligence.
"""
        
        # Create agent with tools (llm must be positional, not keyword)
        agent = create_agent(llm, tools=tools)
        
        # Store system prompt in agent for later use during invocation
        agent._system_prompt = system_prompt
        
        return agent
        
    except Exception as e:
        st.error(f"❌ Failed to create agent: {str(e)}")
        return None

def initialize_agent():
    """Initialize or reinitialize agent."""
    try:
        with st.spinner("🔌 Initializing agent..."):
            agent = create_gemini_agent()
            if agent:
                st.session_state.agent = agent
                st.session_state.agent_initialized = True
                return True
            return False
    except Exception as e:
        st.error(f"❌ Failed to initialize agent: {str(e)}")
        return False

# ============================================
# AGENT EXECUTION
# ============================================

def format_response(response_text: str, tool_calls: List[Dict] = None) -> str:
    """
    Format response text to display lyrics nicely with sections, or piano extraction results.
    Detects if lyrics or piano extraction results are present and formats them appropriately.
    """
    # Check if this response contains piano extraction results
    if tool_calls:
        for tool_call in tool_calls:
            if tool_call.get('name') == 'extract_piano_from_audio':
                try:
                    result_json = tool_call.get('full_result') or tool_call.get('result', '{}')
                    result_data = json.loads(result_json)
                    if not result_data.get('error'):
                        # Format piano extraction results as the main response
                        notes_count = result_data.get('notes_count', 0)
                        piano_audio = result_data.get('piano_audio', '')
                        midi = result_data.get('midi', '')
                        pdf = result_data.get('pdf', '')
                        
                        formatted_response = f"### 🎹 Piano Extraction Complete!\n\n"
                        formatted_response += f"✅ Successfully extracted **{notes_count} notes** from the audio file.\n\n"
                        formatted_response += "**Generated Files:**\n"
                        
                        if piano_audio and os.path.exists(piano_audio):
                            formatted_response += f"• 🎵 Piano Audio: `{os.path.basename(piano_audio)}`\n"
                        if midi and os.path.exists(midi):
                            formatted_response += f"• 🎼 MIDI File: `{os.path.basename(midi)}`\n"
                        if pdf and os.path.exists(pdf):
                            formatted_response += f"• 📄 Sheet Music PDF: `{os.path.basename(pdf)}`\n"
                        
                        formatted_response += "\n**Download your files below:**"
                        
                        # Return formatted response - download buttons will be rendered separately
                        return formatted_response
                except (json.JSONDecodeError, KeyError, AttributeError) as e:
                    # If parsing fails, continue with original response
                    pass
    
    # Check if this response contains lyrics from YouTube lyrics tool
    if tool_calls:
        for tool_call in tool_calls:
            if tool_call.get('name') == 'get_youtube_lyrics':
                try:
                    result_json = tool_call.get('full_result') or tool_call.get('result', '{}')
                    result_data = json.loads(result_json)
                    lyrics = result_data.get('lyrics', '')
                    song_name = result_data.get('song_name', '')
                    artist_name = result_data.get('artist_name', '')
                    
                    if lyrics and not result_data.get('error'):
                        # Format lyrics nicely with sections - well organized
                        formatted_lyrics = f"### 🎵 {song_name}"
                        if artist_name:
                            formatted_lyrics += f" by **{artist_name}**"
                        formatted_lyrics += "\n\n---\n\n"
                        
                        # Split lyrics into lines and format sections with better organization
                        lines = lyrics.split('\n')
                        in_section = False
                        
                        for line in lines:
                            line_stripped = line.strip()
                            if not line_stripped:
                                # Empty line - add spacing
                                if in_section:
                                    formatted_lyrics += "\n"
                                continue
                            elif line_stripped.isupper() and any(keyword in line_stripped for keyword in ['INTRO', 'VERSE', 'CHORUS', 'BRIDGE', 'OUTRO', 'PRE-CHORUS', 'HOOK', 'REFRAIN']):
                                # Section header - make it prominent with better styling
                                if in_section:
                                    formatted_lyrics += "\n"  # Extra space before new section
                                formatted_lyrics += f"#### {line_stripped}\n\n"
                                in_section = True
                            else:
                                # Regular lyrics line
                                formatted_lyrics += f"{line}\n"
                                in_section = True
                        
                        formatted_lyrics += "\n---\n\n"
                        formatted_lyrics += "📄 **A PDF version of these lyrics is available in the Tools Used section below.**"
                        
                        # Always return only the formatted lyrics to avoid duplication
                        # The agent might include lyrics in its response, but we want to show only our formatted version
                        intro = f"I found the lyrics for **{song_name}**"
                        if artist_name:
                            intro += f" by **{artist_name}**"
                        intro += ":"
                        return f"{intro}\n\n{formatted_lyrics}"
                except (json.JSONDecodeError, KeyError, AttributeError) as e:
                    # If parsing fails, continue with original response
                    pass
    
    # If no special formatting needed, return original response
    return response_text

def run_agent(user_message: str, file_path: Optional[str] = None) -> Dict[str, Any]:
    """Execute agent with user message."""
    if not st.session_state.agent:
        return {
            "response": "Error: Agent not initialized. Please check your API keys.",
            "tool_calls": [],
            "error": True
        }
    
    try:
        # Prepare message with file context if available
        full_message = user_message
        if file_path:
            # Convert to absolute path if it's not already
            abs_file_path = os.path.abspath(file_path) if file_path else None
            # Include the file path in the message so the agent can see it
            full_message += f"\n\n[IMPORTANT: User has uploaded an audio file. The file path is: {abs_file_path}. Use this exact path when calling audio-related tools like extract_piano_from_audio, mood_classifier_tool, or recognize_and_analyze_song. The file path is: {abs_file_path}]"
        
        # Add to conversation history
        st.session_state.conversation_history.append(
            HumanMessage(content=full_message)
        )
        
        # Get system prompt from agent if available
        system_prompt = getattr(st.session_state.agent, '_system_prompt', None)
        
        # Prepare messages (keep last 10 messages for context)
        messages = st.session_state.conversation_history[-10:]
        
        # AgentExecutor expects "input" key, not "messages"
        # Include the full message with file path so agent can see it
        agent_input = full_message
        
        # Invoke agent with input key (AgentExecutor format)
        result = st.session_state.agent.invoke({"input": agent_input})
        
        # AgentExecutor returns a dict with "output" and "intermediate_steps" keys
        response_text = None
        tool_calls = []
        intermediate_steps = []
        
        if isinstance(result, dict):
            # Get the output (final response)
            if "output" in result:
                output = result["output"]
                if isinstance(output, str):
                    response_text = output
                else:
                    response_text = str(output)
            
            # Get intermediate steps (tool executions)
            if "intermediate_steps" in result:
                intermediate_steps = result["intermediate_steps"]
            
            # Extract tool calls from intermediate_steps
            for step in intermediate_steps:
                if len(step) >= 2:
                    # step is a tuple: (AgentAction, observation)
                    agent_action = step[0]
                    observation = step[1]
                    
                    # Extract tool name and input from AgentAction
                    tool_name = getattr(agent_action, "tool", "unknown")
                    tool_input = getattr(agent_action, "tool_input", {})
                    
                    # Convert tool_input to dict if it's not already
                    if not isinstance(tool_input, dict):
                        tool_input = {"input": str(tool_input)} if tool_input else {}
                    
                    # Get tool result (observation)
                    tool_result = str(observation) if observation else ""
                    
                    # For query_music_database, always extract SQL query from result
                    if tool_name == "query_music_database":
                        # Extract SQL query from result if present
                        if "[SQL Query:" in tool_result:
                            try:
                                sql_start = tool_result.find("[SQL Query:") + len("[SQL Query:")
                                sql_end = tool_result.find("]", sql_start)
                                if sql_end > sql_start:
                                    sql_query = tool_result[sql_start:sql_end].strip()
                                    # Add SQL query to input for display
                                    tool_input["sql_query"] = sql_query
                            except:
                                pass
                        # Ensure question is in tool_input
                        if "question" in tool_input:
                            # Already have it
                            pass
                        elif isinstance(tool_input, dict) and len(tool_input) > 0:
                            # Try to get question from the first value if it's a simple dict
                            first_key = list(tool_input.keys())[0]
                            if first_key != "sql_query":
                                tool_input["question"] = tool_input.get(first_key, "")
                    
                    # Track tool usage
                    # Store full result for tools that return JSON (like piano extraction)
                    # but truncate for display
                    full_result = tool_result
                    display_result = tool_result[:200] + "..." if len(tool_result) > 200 else tool_result
                    
                    tool_calls.append({
                        "name": tool_name,
                        "input": tool_input,
                        "result": display_result,
                        "full_result": full_result  # Store full result for JSON parsing
                    })
        
        # If no response text yet, try to get it from result
        if not response_text:
            if isinstance(result, dict):
                if "output" in result:
                    response_text = str(result["output"])
                else:
                    response_text = "No response generated"
            else:
                response_text = str(result)
        
        # Also try to extract from messages if available (for compatibility)
        messages_result = []
        if isinstance(result, dict):
            if "messages" in result:
                messages_result = result["messages"]
        
        # Extract additional tool info from messages if available
        tool_call_info = {}  # Map tool_call_id to {name, input}
        
        for msg in messages_result:
            if msg.type == "ai":
                # Get final response
                content = msg.content
                if isinstance(content, str):
                    response_text = content
                elif isinstance(content, list):
                    # Extract text from content blocks
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            text_parts.append(item["text"])
                        elif isinstance(item, str):
                            text_parts.append(item)
                    response_text = "\n".join(text_parts)
                
                # Extract tool calls from AI message (THIS IS WHERE INPUT ARGUMENTS ARE!)
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        # Get tool call ID (used to match with ToolMessage)
                        tool_call_id = None
                        if hasattr(tool_call, "id"):
                            tool_call_id = tool_call.id
                        elif isinstance(tool_call, dict):
                            tool_call_id = tool_call.get("id")
                        
                        # Get tool name and arguments
                        tool_name = "unknown"
                        tool_args = {}
                        
                        if hasattr(tool_call, "name"):
                            tool_name = tool_call.name
                        elif isinstance(tool_call, dict):
                            tool_name = tool_call.get("name", "unknown")
                        
                        if hasattr(tool_call, "args"):
                            tool_args = tool_call.args if tool_call.args else {}
                        elif isinstance(tool_call, dict):
                            tool_args = tool_call.get("args", {})
                        elif hasattr(tool_call, "kwargs"):
                            # Some versions use kwargs instead of args
                            tool_args = tool_call.kwargs if tool_call.kwargs else {}
                        
                        # Store tool call info
                        if tool_call_id:
                            tool_call_info[tool_call_id] = {
                                "name": tool_name,
                                "input": tool_args
                            }
                        else:
                            # If no ID, use name as key (fallback)
                            tool_call_info[tool_name] = {
                                "name": tool_name,
                                "input": tool_args
                            }
            
            elif msg.type == "tool":
                # Get tool result and match with AI tool call
                tool_name = getattr(msg, "name", "unknown")
                tool_result = str(msg.content)
                
                # Try to get tool_call_id to match with AI message
                tool_call_id = None
                if hasattr(msg, "tool_call_id"):
                    tool_call_id = msg.tool_call_id
                elif hasattr(msg, "id"):
                    tool_call_id = msg.id
                
                # Get input arguments from stored tool call info
                tool_input = {}
                if tool_call_id and tool_call_id in tool_call_info:
                    tool_input = tool_call_info[tool_call_id].get("input", {})
                    tool_name = tool_call_info[tool_call_id].get("name", tool_name)
                elif tool_name in tool_call_info:
                    # Fallback: match by name
                    tool_input = tool_call_info[tool_name].get("input", {})
                
                # For query_music_database, try to extract SQL query from result
                if tool_name == "query_music_database" and "[SQL Query:" in tool_result:
                    # Extract SQL query from result
                    try:
                        sql_start = tool_result.find("[SQL Query:") + len("[SQL Query:")
                        sql_end = tool_result.find("]", sql_start)
                        if sql_end > sql_start:
                            sql_query = tool_result[sql_start:sql_end].strip()
                            # Add SQL query to input for display
                            tool_input["sql_query"] = sql_query
                            # Also show the original question
                            if "question" in tool_input:
                                tool_input["question"] = tool_input["question"]
                    except:
                        pass
                
                # Only add if not already in tool_calls (avoid duplicates from intermediate_steps)
                tool_already_tracked = any(
                    tc.get("name") == tool_name and 
                    tc.get("input") == tool_input 
                    for tc in tool_calls
                )
                if not tool_already_tracked:
                    # Store full result for tools that return JSON (like piano extraction)
                    # but truncate for display
                    full_result = tool_result
                    display_result = tool_result[:200] + "..." if len(tool_result) > 200 else tool_result
                    
                    tool_calls.append({
                        "name": tool_name,
                        "input": tool_input,
                        "result": display_result,
                        "full_result": full_result  # Store full result for JSON parsing
                    })
        
        # Format response if it contains lyrics or piano extraction
        formatted_response = format_response(response_text, tool_calls)
        
        # Add agent response to conversation history
        if formatted_response:
            st.session_state.conversation_history.append(
                AIMessage(content=formatted_response)
            )
        
        return {
            "response": formatted_response or "No response generated",
            "tool_calls": tool_calls,
            "error": False
        }
        
    except Exception as e:
        return {
            "response": f"Error: {str(e)}",
            "tool_calls": [],
            "error": True
        }

# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    # App Name/Logo (using PNG from assets) - Centered
    # Logo paths are already defined above, reuse them
    col_logo = st.columns([1, 1, 1])
    with col_logo[1]:
        st.image(logo_icon_path, width=80)
    
    st.divider()
    

    
    # Chat Controls
    st.subheader("💬 Chat Controls")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.session_state.conversation_history = []
        st.success("Chat history cleared!")
        st.rerun()
    
    st.divider()
    
    # Session Activity
    st.subheader("📊 Session Activity")
    total_messages = len(st.session_state.chat_history)
    
    # Collect tools used in this session
    tools_used = set()
    for chat in st.session_state.chat_history:
        if 'tool_calls' in chat and chat['tool_calls']:
            for tool_call in chat['tool_calls']:
                tool_name = tool_call.get('name', 'unknown')
                if tool_name != 'unknown':
                    tools_used.add(tool_name)
    
    # Show active session indicator and tools used
    if total_messages > 0:
        st.success("🟢 Session Active")
        if tools_used:
            st.markdown("**🛠️ Tools Used:**")
            for tool in sorted(tools_used):
                # Format tool names nicely
                tool_display = tool.replace('_', ' ').title()
                st.markdown(f"• {tool_display}")
        else:
            st.info("💡 No tools used yet")
    else:
        st.info("💡 Start a conversation to begin")
    
    st.divider()
    
    # Quick Tips
    st.subheader("💡 Quick Tips")
    with st.expander("How to use HarmoniQ AI"):
        st.markdown("""
        
        **📊 Database Search**
        - Query the music database for information
        - Search for artists, songs, and more

        **📝 Lyrics Tools**
        - Ask for song lyrics or translations
        - Generate PDFs of lyrics
        
        **🎹 Piano Extraction**
        - Upload an audio file and ask to extract piano notes
        - Get MIDI, PDF sheet music, and audio files
        
        **🎵 Audio Analysis**
        - Upload audio to analyze mood, tempo, and characteristics
        """)
    
    st.divider()

# ============================================
# MAIN INTERFACE
# ============================================

# Display logo instead of title
st.image(logo_text_path, width=300)



# Initialize agent on first load
if not st.session_state.agent_initialized:
    initialize_agent()

# Featured Tools Panel (only show on startup, before first message)
if len(st.session_state.chat_history) == 0:
    st.markdown("---")
    st.subheader("✨ Featured Tools")
    st.markdown("Discover what HarmoniQ AI can do for you:")
    
    # Add CSS for theme-aware styling and proper spacing
    st.markdown("""
    <style>
    .feature-tool-card {
        padding: 20px 15px;
        border-radius: 10px;
        text-align: center;
        min-height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        margin-bottom: 10px;
        background-color: rgba(38, 39, 48, 1);
        border: 1px solid rgba(128, 128, 128, 0.2);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    /* Dark mode support */
    [data-theme="dark"] .feature-tool-card {
        background-color: rgba(38, 39, 48, 1);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    @media (prefers-color-scheme: dark) {
        .feature-tool-card {
            background-color: rgba(38, 39, 48, 1);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
    }
    .feature-tool-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    [data-theme="dark"] .feature-tool-card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    .feature-tool-icon {
        font-size: 2.5em;
        margin: 0 0 10px 0;
        line-height: 1;
        display: block;
        min-height: 40px;
    }
    .feature-tool-title {
        margin: 5px 0;
        font-weight: bold;
        font-size: 1em;
        color: inherit;
    }
    .feature-tool-desc {
        margin: 0;
        font-size: 0.85em;
        opacity: 0.8;
        line-height: 1.3;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create a grid layout for featured tools
    col1, col2, col3, col4 = st.columns(4)
    
    with col3:
        st.markdown("""
        <div class="feature-tool-card">
            <div class="feature-tool-icon">🎹</div>
            <p class="feature-tool-title">Piano Extraction</p>
            <p class="feature-tool-desc">Extract piano notes from audio</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-tool-card">
            <div class="feature-tool-icon">📝</div>
            <p class="feature-tool-title">Lyrics Tools</p>
            <p class="feature-tool-desc">Get song lyrics</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col1:
        st.markdown("""
        <div class="feature-tool-card">
            <div class="feature-tool-icon">📊</div>
            <p class="feature-tool-title">Database Search</p>
            <p class="feature-tool-desc">Query music database</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="feature-tool-card">
            <div class="feature-tool-icon">📺</div>
            <p class="feature-tool-title">YouTube</p>
            <p class="feature-tool-desc">Process YouTube videos</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Second row
    col5, col6, col7 = st.columns(3)
    
    with col5:
        st.markdown("""
        <div class="feature-tool-card">
            <div class="feature-tool-icon">🎵</div>
            <p class="feature-tool-title">Audio Analysis</p>
            <p class="feature-tool-desc">Analyze audio features</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col6:
        st.markdown("""
        <div class="feature-tool-card">
            <div class="feature-tool-icon">🎤</div>
            <p class="feature-tool-title">Text-to-Singing</p>
            <p class="feature-tool-desc">Convert lyrics to singing</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col7:
        st.markdown("""
        <div class="feature-tool-card">
            <div class="feature-tool-icon">📚</div>
            <p class="feature-tool-title">Music Theory</p>
            <p class="feature-tool-desc">Learn music theory</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")

# File Upload Section (Collapsible)
with st.expander("📁 Upload Audio File (Optional)", expanded=False):
    uploaded_file = st.file_uploader(
        "Upload audio file (.wav, .mp3, .m4a, .ogg, .flac)",
        type=['wav', 'mp3', 'm4a', 'ogg', 'flac'],
        help="Upload an audio file to extract piano, analyze characteristics, or process",
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.getvalue())
            st.session_state.uploaded_file_path = tmp.name
        
        st.success(f"✅ File uploaded: {uploaded_file.name}")
        
        # Audio player
        st.audio(st.session_state.uploaded_file_path)

# Chat Interface
st.markdown("---")

# Display chat history
for chat in st.session_state.chat_history:
    if chat['role'] == 'user':
        with st.chat_message("user"):
            st.write(chat['content'])
            if 'file_path' in chat:
                st.caption(f"📎 File: {os.path.basename(chat['file_path'])}")
    else:
        with st.chat_message("assistant"):
            # Check if content contains formatted lyrics (has section headers)
            content = chat['content']
            if '#### INTRO' in content or '#### VERSE' in content or '#### CHORUS' in content or '**INTRO**' in content or '**VERSE' in content or '**CHORUS**' in content:
                # Render as markdown for better formatting with organized lyrics
                # Add custom CSS for better lyrics display
                st.markdown("""
                <style>
                .lyrics-container {
                    background-color: rgba(38, 39, 48, 0.1);
                    padding: 15px;
                    border-radius: 8px;
                    margin: 10px 0;
                }
                .lyrics-section-header {
                    color: #1f77b4;
                    font-weight: bold;
                    margin-top: 15px;
                    margin-bottom: 8px;
                }
                </style>
                """, unsafe_allow_html=True)
                st.markdown(content)
            else:
                st.markdown(content)
            
            # Check for piano extraction results and display download buttons in main response
            if 'tool_calls' in chat and chat['tool_calls']:
                for tool_call in chat['tool_calls']:
                    if tool_call.get('name') == 'extract_piano_from_audio' and ('result' in tool_call or 'full_result' in tool_call):
                        try:
                            result_json = tool_call.get('full_result') or tool_call.get('result', '{}')
                            result_data = json.loads(result_json)
                            if not result_data.get('error'):
                                st.markdown("---")
                                # Display download buttons in main response
                                col1, col2, col3 = st.columns(3)
                                
                                # 1. Download Piano Audio
                                with col1:
                                    piano_audio_path = result_data.get('piano_audio')
                                    if piano_audio_path and os.path.exists(piano_audio_path):
                                        with open(piano_audio_path, 'rb') as f:
                                            piano_audio_bytes = f.read()
                                        st.download_button(
                                            label="🎵 Download Piano Audio",
                                            data=piano_audio_bytes,
                                            file_name=os.path.basename(piano_audio_path),
                                            mime='audio/wav',
                                            use_container_width=True
                                        )
                                        st.audio(piano_audio_path)
                                    else:
                                        st.info("Piano audio not available")
                                
                                # 2. Download MIDI
                                with col2:
                                    midi_path = result_data.get('midi')
                                    if midi_path and os.path.exists(midi_path):
                                        with open(midi_path, 'rb') as f:
                                            midi_bytes = f.read()
                                        st.download_button(
                                            label="🎼 Download MIDI",
                                            data=midi_bytes,
                                            file_name=os.path.basename(midi_path),
                                            mime='audio/midi',
                                            use_container_width=True
                                        )
                                    else:
                                        st.info("MIDI file not available")
                                
                                # 3. Download PDF Notes
                                with col3:
                                    pdf_path = result_data.get('pdf')
                                    if pdf_path and os.path.exists(pdf_path):
                                        with open(pdf_path, 'rb') as f:
                                            pdf_bytes = f.read()
                                        st.download_button(
                                            label="📄 Download PDF Notes",
                                            data=pdf_bytes,
                                            file_name=os.path.basename(pdf_path),
                                            mime='application/pdf',
                                            use_container_width=True
                                        )
                                    else:
                                        st.info("PDF not available")
                        except (json.JSONDecodeError, KeyError) as e:
                            pass  # Silently fail if parsing error
            
            # Show tool usage if available
            if 'tool_calls' in chat and chat['tool_calls']:
                with st.expander("🔧 Tools Used", expanded=False):
                    for i, tool_call in enumerate(chat['tool_calls'], 1):
                        tool_name = tool_call.get('name', 'unknown')
                        tool_input = tool_call.get('input', {})
                        
                        st.markdown(f"**{i}. {tool_name}**")
                        
                        # Special formatting for query_music_database
                        if tool_name == "query_music_database":
                            # Always show question if available
                            if "question" in tool_input:
                                st.markdown(f"**Question:** `{tool_input['question']}`")
                            elif tool_input:
                                # If question not explicitly set, show the input
                                question_val = tool_input.get("question") or (list(tool_input.values())[0] if tool_input else None)
                                if question_val and question_val != tool_input.get("sql_query"):
                                    st.markdown(f"**Question:** `{question_val}`")
                            
                            # Always show SQL query if available
                            if "sql_query" in tool_input:
                                st.markdown(f"**SQL Query:**")
                                st.code(tool_input['sql_query'], language="sql")
                            else:
                                # Try to extract SQL query from result if not in input
                                tool_result = tool_call.get('result', '')
                                if "[SQL Query:" in str(tool_result):
                                    try:
                                        sql_start = str(tool_result).find("[SQL Query:") + len("[SQL Query:")
                                        sql_end = str(tool_result).find("]", sql_start)
                                        if sql_end > sql_start:
                                            sql_query = str(tool_result)[sql_start:sql_end].strip()
                                            st.markdown(f"**SQL Query:**")
                                            st.code(sql_query, language="sql")
                                    except:
                                        pass
                            
                            # Show other input if any
                            if tool_input and len(tool_input) > 0:
                                remaining_input = {k: v for k, v in tool_input.items() if k not in ["question", "sql_query"]}
                                if remaining_input:
                                    st.code(f"Additional Input: {json.dumps(remaining_input, indent=2)}")
                            elif not tool_input or len(tool_input) == 0:
                                st.info("No input parameters captured")
                        else:
                            # For other tools, show input normally
                            if tool_input:
                                st.code(f"Input: {json.dumps(tool_input, indent=2)}")
                            else:
                                st.info("No input parameters captured")
                        
                        # Special handling for convert_lyrics_to_singing - display audio player
                        if tool_name == "convert_lyrics_to_singing" and ('result' in tool_call or 'full_result' in tool_call):
                            try:
                                # Use full_result if available (not truncated), otherwise use result
                                result_json = tool_call.get('full_result') or tool_call.get('result', '{}')
                                result_data = json.loads(result_json)
                                if result_data.get('audio_path') and os.path.exists(result_data['audio_path']):
                                    st.markdown("**🎧 Generated Singing Audio:**")
                                    st.audio(result_data['audio_path'])
                                    st.caption(f"Audio saved at: {result_data['audio_path']}")
                                elif result_data.get('error'):
                                    st.error(f"Error: {result_data['error']}")
                                else:
                                    st.caption(f"Result: {tool_call['result'][:100]}...")
                            except (json.JSONDecodeError, KeyError):
                                # Fallback if result is not JSON
                                st.caption(f"Result: {tool_call['result'][:100]}...")
                        # Special handling for extract_piano_from_audio - show file paths in Tools Used
                        elif tool_name == "extract_piano_from_audio" and ('result' in tool_call or 'full_result' in tool_call):
                            try:
                                # Use full_result if available (not truncated), otherwise use result
                                result_json = tool_call.get('full_result') or tool_call.get('result', '{}')
                                result_data = json.loads(result_json)
                                if result_data.get('error'):
                                    st.error(f"❌ Error: {result_data['error']}")
                                else:
                                    # Show tool details and file paths (download buttons are in main response)
                                    if result_data.get('notes_count'):
                                        st.info(f"📊 Extracted {result_data['notes_count']} notes")
                                    
                                    # Show file paths
                                    st.markdown("**Generated Files:**")
                                    file_info = []
                                    if result_data.get('piano_audio'):
                                        file_info.append(f"🎵 Piano Audio: `{result_data['piano_audio']}`")
                                    if result_data.get('midi'):
                                        file_info.append(f"🎼 MIDI: `{result_data['midi']}`")
                                    if result_data.get('pdf'):
                                        file_info.append(f"📄 PDF: `{result_data['pdf']}`")
                                    if result_data.get('synthesized_audio'):
                                        file_info.append(f"🔊 Synthesized Audio: `{result_data['synthesized_audio']}`")
                                    
                                    if file_info:
                                        for info in file_info:
                                            st.caption(info)
                            except (json.JSONDecodeError, KeyError) as e:
                                # Fallback if result is not JSON or parsing fails
                                st.caption(f"Result: {tool_call['result'][:200]}...")
                                st.warning(f"Could not parse piano extraction results: {e}")
                        # Special handling for get_youtube_lyrics - display lyrics and PDF download
                        elif tool_name == "get_youtube_lyrics" and ('result' in tool_call or 'full_result' in tool_call):
                            try:
                                # Use full_result if available (not truncated), otherwise use result
                                result_json = tool_call.get('full_result') or tool_call.get('result', '{}')
                                result_data = json.loads(result_json)
                                
                                if result_data.get('error'):
                                    st.error(f"❌ Error: {result_data['error']}")
                                else:
                                    st.markdown("**🎵 YouTube Lyrics Results:**")
                                    
                                    # Display song info
                                    song_name = result_data.get('song_name', 'Unknown')
                                    artist_name = result_data.get('artist_name', '')
                                    if song_name:
                                        title_text = f"**{song_name}**"
                                        if artist_name:
                                            title_text += f" by {artist_name}"
                                        st.markdown(title_text)
                                    
                                    # Display lyrics
                                    lyrics = result_data.get('lyrics', '')
                                    if lyrics:
                                        st.markdown("**Lyrics:**")
                                        # Display lyrics in a scrollable text area for better organization
                                        st.text_area("", value=lyrics, height=300, disabled=True, label_visibility="collapsed")
                                    
                                    # Display PDF download button
                                    pdf_path = result_data.get('pdf_path')
                                    if pdf_path and os.path.exists(pdf_path):
                                        st.markdown("**📄 Download Lyrics PDF:**")
                                        with open(pdf_path, 'rb') as f:
                                            pdf_bytes = f.read()
                                        st.download_button(
                                            label="📥 Download PDF",
                                            data=pdf_bytes,
                                            file_name=os.path.basename(pdf_path),
                                            mime='application/pdf',
                                            use_container_width=True
                                        )
                                    elif result_data.get('message'):
                                        st.info(result_data['message'])
                            except (json.JSONDecodeError, KeyError) as e:
                                # Fallback if result is not JSON or parsing fails
                                st.caption(f"Result: {tool_call['result'][:200]}...")
                                st.warning(f"Could not parse YouTube lyrics results: {e}")
                        elif 'result' in tool_call:
                            st.caption(f"Result: {tool_call['result'][:100]}...")


# Chat input
user_input = st.chat_input("Message HarmoniQ AI...")

if user_input:
    if not st.session_state.agent:
        st.error("❌ Agent not initialized. Please check your API keys in the sidebar.")
        st.stop()
    
    # Add user message to chat history
    chat_entry = {
        'role': 'user',
        'content': user_input,
        'timestamp': datetime.now().isoformat()
    }
    if st.session_state.uploaded_file_path:
        chat_entry['file_path'] = st.session_state.uploaded_file_path
    
    st.session_state.chat_history.append(chat_entry)
    
    # Get agent response
    with st.spinner("🤔 Thinking..."):
        result = run_agent(
            user_input,
            st.session_state.uploaded_file_path
        )
    
    # Add bot response to chat history
    bot_entry = {
        'role': 'assistant',
        'content': result['response'],
        'timestamp': datetime.now().isoformat(),
        'tool_calls': result.get('tool_calls', [])
    }
    st.session_state.chat_history.append(bot_entry)
    
    # Clear uploaded file after processing
    if st.session_state.uploaded_file_path:
        try:
            if os.path.exists(st.session_state.uploaded_file_path):
                os.unlink(st.session_state.uploaded_file_path)
        except:
            pass
        st.session_state.uploaded_file_path = None
    
    st.rerun()

# Welcome message if no chat history
if len(st.session_state.chat_history) == 0:
    st.info("💡 Start a conversation by typing a message below. You can ask about music, upload audio files, or request lyrics!")

