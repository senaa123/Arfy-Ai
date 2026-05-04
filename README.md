# Arfy AI — Modular Personal Voice Assistant

**Arfy AI** is a modular personal voice assistant designed to work like a local AI companion for desktop productivity, voice interaction, persistent memory, document intelligence, OCR, and retrieval-augmented generation.

The system combines a **desktop voice assistant**, **LLM-powered agent layer**, **long-term memory**, **document ingestion**, **OCR**, and **self-healing RAG** into a service-based architecture. Each major capability runs as an independent module, making the project easier to scale, debug, improve, and extend.

> Arfy is not just a chatbot.  
> It is a voice-first AI assistant that listens, remembers, reasons, retrieves knowledge, and performs actions through tools.

---

## Overview

Arfy AI is built around a simple idea:

**The user should be able to talk naturally, and the assistant should decide whether to answer, remember, retrieve, automate, or act.**

The desktop app handles the user experience, voice input, speech output, and local machine actions. The backend services handle reasoning, memory, document processing, OCR, and retrieval-augmented answers.

This separation keeps the desktop app lightweight while allowing the intelligence layer to grow as independent services.

---

## Key Capabilities

- Voice activation with wake word support
- Speech-to-text using local ASR
- Text-to-speech assistant responses
- PyQt6 desktop chat interface
- Animated assistant orb and waveform UI
- LLM-powered agent reasoning
- LangGraph-based agent workflow
- Plugin/tool registry for extensible actions
- Persistent memory across sessions
- Short-term session history
- Long-term semantic memory using vector search
- Structured memory using SQLite
- Document ingestion and chunking
- OCR for images and scanned documents
- Retrieval-Augmented Generation from uploaded documents
- Self-healing RAG with grounding checks and retry logic
- Local desktop actions such as opening and closing apps
- Spotify control
- Weather lookup
- Web search
- Modular FastAPI microservice architecture

---

## Why This Project Exists

Most assistants are limited because they usually fall into one of these problems:

- they only answer questions,
- they do not remember useful information properly,
- they cannot work with private uploaded documents,
- they are difficult to extend,
- or they place too much logic inside one large application.

Arfy AI was built to explore a more scalable assistant architecture.

Instead of building one oversized Python app, Arfy separates the system into focused services:

- the desktop app handles the user interface and local actions,
- the agent service handles reasoning and tool routing,
- the memory service handles recall and persistence,
- the document service handles ingestion and chunking,
- the OCR service handles text extraction from images,
- and the RAG service handles grounded answers from documents.

This makes the system closer to how real-world AI products are structured.

---

## High-Level Architecture

User
 │
 │ Voice / Text Input
 ▼
Desktop App
PyQt6 UI + Wake Word + ASR + TTS + Local Desktop Actions
 │
 │ Sends request
 ▼
Agent Service
LLM Reasoning + LangGraph Workflow + Tool Routing
 │
 ├── Memory Service
 │   SQLite Structured Memory + Qdrant Vector Memory
 │
 ├── Document Service
 │   File Extraction + Cleaning + Chunking + Metadata Registration
 │   │
 │   └── OCR Service
 │       Image and Scanned Document Text Extraction
 │
 └── RAG Service
     Retrieval + Reranking + Grounded Answer Generation

---

## System Design Philosophy

Arfy follows a modular design philosophy:

> Keep the desktop app lightweight.  
> Move heavy intelligence into separate services.

This helps with:

- easier debugging,
- better separation of responsibilities,
- lower desktop overhead,
- independent service testing,
- future cloud deployment,
- and easier feature expansion.

Each service owns one clear responsibility.

| Layer | Main Responsibility |
|---|---|
| Desktop App | User interface, wake word, ASR, TTS, local desktop actions |
| Agent Service | Reasoning, routing, tool selection, response generation |
| Memory Service | Structured memory, vector memory, sessions, document metadata |
| Document Service | File extraction, cleaning, chunking, persistence |
| OCR Service | Image and scanned document text extraction |
| RAG Service | Retrieval, reranking, grounding, citation-based answers |

---

## Main Pipelines

## 1. Voice Pipeline

The voice pipeline converts the user's speech into an assistant response.

Wake word detected
 → optional owner voice verification
 → record user speech
 → detect speech boundaries
 → transcribe audio with faster-whisper
 → clean transcript
 → send text to agent service
 → agent generates response/action
 → desktop app speaks response with TTS

Technologies used:

- faster-whisper
- VAD / endpointing
- edge-tts
- PyQt6
- wake word detection
- optional resemblyzer voice authentication

---

## 2. Agent Pipeline

The agent service acts as the brain of Arfy.

User request
 → /agent/ask
 → create or continue session
 → store user message in short-term history
 → retrieve memory context
 → build LangGraph state
 → decide whether a tool is needed
 → execute tool if required
 → build final response
 → store assistant response
 → return response/action to desktop app

The agent can decide whether to:

- answer directly,
- use memory,
- search the web,
- check weather,
- control a tool,
- ingest a document,
- ask the RAG service,
- or return a local desktop action.

---

## 3. Memory Pipeline

The memory system allows Arfy to remember useful information across sessions.

Conversation or event
 → classify/save useful memory
 → store exact data in SQLite
 → create embedding for semantic memory
 → store vector in Qdrant
 → retrieve relevant memories when needed

Memory layers:

Session Memory  
Temporary short-term chat context during the active session

Structured Memory  
SQLite database for exact facts, actions, sessions, and document metadata

Semantic Memory  
Qdrant vector database for meaning-based memory retrieval

Example use cases:

- remembering user preferences,
- recalling past conversations,
- storing useful facts,
- tracking previous actions,
- linking documents to future questions,
- retrieving related context by meaning.

---

## 4. Document Ingestion Pipeline

The document service prepares uploaded files for storage and retrieval.

User selects a file
 → document service receives file path
 → detect file type
 → extract text
 → use OCR fallback if needed
 → clean extracted text
 → split text into chunks
 → persist document data locally
 → register document metadata in memory service
 → register chunks in memory service
 → optionally index chunks into vector storage

Supported document types include:

- PDF
- DOCX
- TXT
- Markdown
- code-like text files
- CSV
- images through OCR

---

## 5. OCR Pipeline

The OCR service is separated from the document service so OCR logic stays isolated.

Image or scanned document path
 → OCR service receives request
 → preprocess image if needed
 → run Tesseract OCR
 → return extracted text

This separation keeps the document service clean and avoids mixing file ingestion with heavy image text extraction logic.

---

## 6. RAG Pipeline

The RAG service answers questions using uploaded document evidence.

User question
 → retrieve relevant document chunks
 → expand neighboring chunks
 → rerank evidence
 → build answer from retrieved context
 → check whether answer is grounded
 → retry retrieval if answer is weak
 → return final answer with citations

The self-healing part helps reduce unsupported answers by checking whether the generated response is actually backed by retrieved document chunks.

---

## Services Overview

## desktop_app/

The desktop app is the user-facing layer of Arfy.

It handles:

- PyQt6 desktop UI
- wake word listening
- audio recording
- speech-to-text
- text-to-speech
- chat interface
- animated orb and waveform
- local app control
- Spotify desktop control
- communication with backend services
- active session lifecycle

desktop_app/
├── main.py
├── runtime.py
├── session_state.py
├── ui_bridge.py
├── audio/
│   ├── wakeword.py
│   ├── speech.py
│   ├── tts_engine.py
│   ├── voice_auth.py
│   ├── vad.py
│   └── transcript_postprocess.py
├── clients/
│   ├── agent_client.py
│   ├── memory_client.py
│   └── spotify_client.py
├── integrations/
│   ├── app_control.py
│   └── spotify_desktop.py
├── local_actions/
│   ├── intent_router.py
│   └── action_executor.py
└── ui/
    ├── main_window.py
    ├── chat_widget.py
    ├── orb.py
    ├── waveform.py
    ├── tray.py
    └── styles.py

---

## agent_service/

The agent service is the reasoning and orchestration layer.

It handles:

- incoming user requests,
- session history,
- memory context retrieval,
- LangGraph workflow execution,
- LLM response generation,
- tool routing,
- plugin execution,
- local action decisions,
- and final response creation.

agent_service/
├── main.py
├── brain.py
├── graph.py
├── router.py
├── route_helpers.py
├── session.py
├── safety.py
├── models.py
├── routes/
│   ├── ask.py
│   ├── documents.py
│   ├── sessions.py
│   └── health.py
├── plugins/
│   ├── base.py
│   ├── registry.py
│   ├── builtin_tools.py
│   ├── document_tools.py
│   ├── rag_tools.py
│   └── executor.py
└── tools/
    ├── memory_tool.py
    ├── search.py
    └── weather/

---

## memory_service/

The memory service manages long-term memory, session archives, action history, document metadata, and document chunks.

It handles:

- SQLite structured storage,
- Qdrant vector storage,
- semantic search,
- memory retrieval,
- memory saving,
- action logging,
- session archiving,
- document registration,
- document chunk registration,
- and chunk search for RAG.

memory_service/
├── main.py
├── db.py
├── models.py
├── schemas.py
├── qdrant_store.py
├── summarizer.py
├── routes/
│   ├── memory.py
│   ├── actions.py
│   ├── sessions.py
│   ├── documents.py
│   ├── rag.py
│   └── health.py
└── services/
    ├── structured_store.py
    ├── vector_store.py
    ├── retrieval.py
    ├── linker.py
    └── memory_policy.py

---

## document_service/

The document service owns file ingestion and document preparation.

It handles:

- file type detection,
- PDF extraction,
- DOCX extraction,
- text/code/Markdown extraction,
- CSV extraction,
- OCR fallback,
- text cleaning,
- chunk creation,
- document persistence,
- metadata registration,
- and chunk registration.

document_service/
├── main.py
├── identity.py
├── pdf_pipeline.py
├── storage.py
├── schemas.py
├── routes/
│   ├── documents.py
│   └── health.py
├── workflows/
│   └── ingest.py
├── extractors/
│   ├── pdf.py
│   ├── docx.py
│   ├── text.py
│   ├── csv.py
│   └── image.py
├── chunking/
│   ├── basic.py
│   └── strategies.py
└── clients/
    ├── memory_client.py
    └── ocr_client.py

---

## ocr_service/

The OCR service handles image and scanned document text extraction.

It handles:

- image OCR,
- Tesseract execution,
- preprocessing support,
- and OCR response formatting.

ocr_service/
├── main.py
├── engine.py
├── preprocess.py
├── schemas.py
└── routes/
    ├── ocr.py
    └── health.py

---

## rag_service/

The RAG service is responsible for grounded document-based question answering.

It handles:

- retrieving chunks from memory service,
- expanding neighboring chunks,
- reranking results,
- building prompts from evidence,
- generating answers,
- checking grounding,
- creating citations,
- and retrying when retrieval is weak.

rag_service/
├── main.py
├── config.py
├── schemas.py
├── routes/
│   ├── ask.py
│   └── health.py
├── clients/
│   ├── memory_client.py
│   └── llm_client.py
├── retrieval/
│   ├── retrieve.py
│   └── neighbor_expand.py
├── reranking/
│   └── rank.py
├── generation/
│   └── answer_builder.py
├── grounding/
│   ├── judge.py
│   └── citations.py
├── repair/
│   └── retry.py
└── workflows/
    └── answer.py

---

## Technology Stack

## AI and Agent Layer

- Groq API
- LLaMA models
- LangGraph
- LangChain
- OpenAI-compatible LLM clients
- sentence-transformers

## Backend Services

- Python
- FastAPI
- Uvicorn
- Pydantic
- Requests
- python-dotenv

## Memory and Retrieval

- SQLite
- SQLAlchemy
- Qdrant
- Vector embeddings
- Semantic search

## Desktop and Voice

- PyQt6
- OpenGL
- faster-whisper
- sounddevice
- VAD / endpointing
- edge-tts
- pygame
- wake word detection
- resemblyzer

## Documents and OCR

- PyMuPDF
- pypdf
- python-docx
- pytesseract
- Pillow
- Tesseract OCR

## External Integrations

- Spotify Web API
- OpenWeatherMap API
- DuckDuckGo Search
- Windows app/process control

---

## API Endpoints

## Agent Service

| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Check agent service health |
| POST | /agent/ask | Main chat endpoint |
| POST | /agent/document/ingest | Trigger document ingestion through the agent |
| POST | /agent/reset | Reset an active session |
| POST | /agent/session/end | End and archive a session |

## Memory Service

| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Check memory service health |
| POST | /memory/save | Save a memory |
| POST | /memory/context | Retrieve combined memory context |
| POST | /memory/retrieve | Retrieve relevant memories |
| GET | /memory/all | List stored memories |
| POST | /memory/action | Log an action |
| GET | /memory/history | View action history |
| POST | /session/archive/chunk | Archive a session chunk |
| POST | /session/archive/finalize | Finalize a session archive |
| POST | /documents/register | Register document metadata |
| POST | /documents/chunks/register | Register document chunks |
| GET | /documents/all | List registered documents |
| GET | /documents/{document_id}/chunks | List chunks for a document |
| POST | /memory/search/chunks | Search document chunks for RAG |

## Document Service

| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Check document service health |
| POST | /documents/ingest | Ingest, extract, chunk, and register a document |

## OCR Service

| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Check OCR service health |
| POST | /ocr/image | Extract text from an image |

## RAG Service

| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Check RAG service health |
| POST | /rag/ask | Ask a question using document evidence |

---

## Environment Variables

Create .env files inside the relevant service folders.

Never commit real API keys or .env files to GitHub.

## desktop_app/.env

AGENT_URL=http://127.0.0.1:8001
MEMORY_URL=http://127.0.0.1:8000

GROQ_API_KEY=your_groq_api_key
WEATHER_API_KEY=your_openweathermap_key
PICOVOICE_KEY=your_picovoice_key

SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

## agent_service/.env

GROQ_API_KEY=your_groq_api_key
GROQ_MODEL_MAIN=llama-3.3-70b-versatile
GROQ_MODEL_ROUTER=llama-3.1-8b-instant

MEMORY_SERVICE_URL=http://127.0.0.1:8000
DOCUMENT_SERVICE_URL=http://127.0.0.1:8002
RAG_SERVICE_URL=http://127.0.0.1:8004

WEATHER_API_KEY=your_openweathermap_key
WEATHER_BASE_URL=https://api.openweathermap.org/data/2.5/weather
WEATHER_GEO_URL=http://api.openweathermap.org/geo/1.0/direct
WEATHER_ONECALL_URL=https://api.openweathermap.org/data/3.0/onecall
WEATHER_TIMEMACHINE_URL=https://api.openweathermap.org/data/3.0/onecall/timemachine
WEATHER_FORECAST_DAYS=5
WEATHER_HISTORY_DAYS=5
WEATHER_TIMEZONE=Asia/Colombo

## memory_service/.env

DATABASE_URL=sqlite:///./memory.db
QDRANT_COLLECTION=arfy_memory
QDRANT_PATH=./qdrant_data

## document_service/.env

MEMORY_SERVICE_URL=http://127.0.0.1:8000
OCR_SERVICE_URL=http://127.0.0.1:8003

## ocr_service/.env

TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

## rag_service/.env

RAG_SERVICE_HOST=127.0.0.1
RAG_SERVICE_PORT=8004

MEMORY_SERVICE_BASE_URL=http://127.0.0.1:8000
MEMORY_SEARCH_CHUNKS_PATH=/memory/search/chunks

RAG_LLM_BASE_URL=https://api.groq.com/openai/v1
RAG_LLM_API_KEY=your_groq_api_key
RAG_LLM_MODEL=llama-3.3-70b-versatile

RAG_DEFAULT_TOP_K=8
RAG_DEFAULT_FINAL_K=4
RAG_MIN_GROUNDED_SCORE=0.18
RAG_MIN_CONTEXT_CHARS=200
RAG_ENABLE_REPAIR_RETRY=true
RAG_REPAIR_TOP_K_MULTIPLIER=2
RAG_REPAIR_MAX_TOP_K=16
RAG_REPAIR_FINAL_K_EXTRA=2
RAG_REPAIR_MAX_FINAL_K=6
RAG_NEIGHBOR_EXPANSION_WINDOW=1
RAG_NEIGHBOR_EXPANSION_MAX_CHUNKS=6
RAG_ANSWER_MAX_CONTEXT_CHUNKS=4
RAG_REQUEST_TIMEOUT_SECONDS=30
RAG_MAX_RETURNED_CITATIONS=4
RAG_CITATION_SNIPPET_CHARS=160

---

## Installation

Create a virtual environment:

python -m venv venv

Activate it on Windows PowerShell:

.\venv\Scripts\Activate.ps1

Install dependencies:

pip install fastapi uvicorn python-dotenv requests pydantic sqlalchemy qdrant-client sentence-transformers
pip install langgraph langchain-core langchain-groq groq ddgs
pip install PyQt6 PyOpenGL numpy sounddevice faster-whisper silero-vad edge-tts pygame resemblyzer openwakeword spotipy psutil
pip install pymupdf pypdf python-docx pytesseract pillow

You may also need to install Tesseract OCR separately and set the correct path in ocr_service/.env.

---

## Running Locally

Start each service in a separate terminal from the repository root.

## 1. Start Memory Service

python -m uvicorn memory_service.main:app --host 127.0.0.1 --port 8000 --reload

## 2. Start Agent Service

python -m uvicorn agent_service.main:app --host 127.0.0.1 --port 8001 --reload

## 3. Start Document Service

python -m uvicorn document_service.main:app --host 127.0.0.1 --port 8002 --reload

## 4. Start OCR Service

python -m uvicorn ocr_service.main:app --host 127.0.0.1 --port 8003 --reload

## 5. Start RAG Service

python -m uvicorn rag_service.main:app --host 127.0.0.1 --port 8004 --reload

## 6. Start Desktop App

python -m desktop_app.main

---

## Health Checks

After starting the services, test them with:

curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8002/health
curl http://127.0.0.1:8003/health
curl http://127.0.0.1:8004/health

Expected response:

{
  "status": "ok",
  "service": "service_name"
}

---

## Example API Usage

## Ask the Agent

curl -X POST http://127.0.0.1:8001/agent/ask -H "Content-Type: application/json" -d "{\"session_id\":\"test-session-001\",\"text\":\"What can you do?\"}"

## Ingest a Document

curl -X POST http://127.0.0.1:8002/documents/ingest -H "Content-Type: application/json" -d "{\"file_path\":\"C:/Users/YourName/Documents/sample.pdf\",\"enable_ocr\":true,\"persist\":true,\"pdf_ocr_min_chars\":30,\"chunk_size\":1200,\"chunk_overlap\":200,\"index_chunks_to_vector\":true}"

## Ask from Uploaded Documents

curl -X POST http://127.0.0.1:8004/rag/ask -H "Content-Type: application/json" -d "{\"question\":\"Summarize the key points from my uploaded document.\",\"top_k\":8,\"final_k\":4,\"session_id\":\"test-session-001\"}"

---

## Recommended Repository Structure

Arfy-AI/
├── README.md
├── desktop_app/
├── agent_service/
├── memory_service/
├── document_service/
├── ocr_service/
├── rag_service/
└── .gitignore

---

## Recommended .gitignore

.env
*.env

__pycache__/
*.pyc

venv/
.venv/

qdrant_data/
*.db
*.sqlite
*.sqlite3

document_service/data/

.DS_Store

---

## Current Project Status

Arfy AI is currently a local modular AI assistant system with working foundations for:

- voice interaction,
- desktop UI,
- agent routing,
- memory,
- document ingestion,
- OCR,
- RAG,
- and local tool execution.

The project is actively evolving from a personal voice assistant into a modular AI assistant platform.

---

## Future Improvements

Planned improvements include:

- Docker Compose for one-command startup
- Separate requirements.txt per service
- Automated test suite for each microservice
- Full end-to-end pipeline tests
- Service gateway for cleaner routing
- Automation service for email, calendar, Notion, Sheets, and job alerts
- Better model selection per task
- Cloud-ready deployment profiles
- Improved UI for document upload and RAG chat
- More advanced memory summarization and preference extraction

---

## About This Project

Arfy AI is a personal AI assistant project focused on building a practical, modular, and expandable AI system.

It brings together:

- voice AI,
- desktop automation,
- LLM reasoning,
- persistent memory,
- document intelligence,
- OCR,
- and retrieval-augmented generation.

The long-term goal is to build an assistant architecture where new capabilities can be added as independent services without rewriting the entire system.
