# Local Qwen Audio Assistant

## Overview
A fully local Windows AI application that accepts audio by browser recording or existing-file upload, transcribes it with faster-whisper/Whisper large-v3, and sends the transcript to a local Qwen3-4B model for summarization and other text tasks.

## Architecture

Browser
  |
  v
Flask :5000
  |
  +--> Record / Upload Audio
  |
  v
faster-whisper/Whisper large-v3
  |
  v
Transcript
  |
  v
requests HTTP client
  |
  v
llama.cpp llama-server :8080
  |
  v
Qwen3-4B-Q4_K_M.gguf
  |
  v
Summary / AI response
  |
  v
Browser

## Components

### Flask
Flask is the web/application layer. It provides the browser interface and orchestrates audio input, transcription, Qwen requests, and result display. The project uses Flask, not FastAPI.

### faster-whisper
Python package/runtime used to run Whisper transcription locally. It converts audio into text.

### Whisper large-v3
The speech-recognition model used by faster-whisper. Its job is **Audio -> Text**, not summarization.

Cached model location:
`E:\AI\hf-cache\hub\models--Systran--faster-whisper-large-v3`

### Qwen3-4B
The local language model used for summarization, question answering, rewriting, extraction, and other NLP tasks.

Model:
`E:\AI\models\qwen\Qwen3-4B-Q4_K_M.gguf`

### llama.cpp / llama-server
The runtime that loads the Qwen GGUF model and exposes it as an HTTP API.

Executable:
`E:\AI\llama.cpp\llama-server.exe`

API:
`http://127.0.0.1:8080/v1/chat/completions`

Health:
`http://127.0.0.1:8080/health`

### requests
Python HTTP client used by Flask to communicate with llama-server.


## Python Environment

Virtual environment:
`E:\AI\venv`

Verified Python:
`Python 3.12.10`

Verified packages:
- Flask
- requests
- faster-whisper

## Requirements

Recommended `requirements.txt`:

```text
Flask>=3.1,<3.2
requests>=2.34,<3
faster-whisper>=1.2,<2
```

The requirements file installs Python packages only. The Qwen GGUF, Whisper model assets, and llama.cpp executable are separate local dependencies.

## Startup

### 1. Start Qwen / llama-server in PowerShell

```powershell
E:\AI\llama.cpp\llama-server.exe `
  -m "E:\AI\models\qwen\Qwen3-4B-Q4_K_M.gguf" `
  -c 8192 `
  -t 8 `
  --host 127.0.0.1 `
  --port 8080
```

Successful output includes `model loaded` and `listening on http://127.0.0.1:8080`.

### 2. Verify Qwen

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health
```

Expected:

```text
status
------
ok
```

### 3. Start Flask

```powershell
E:\AI\venv\Scripts\python.exe C:\Users\M_Hamza\local_qwen_web_fixed.py
```

Expected:

```text
Loading Whisper model...
Whisper ready.
Running on http://127.0.0.1:5000
```

### 4. Open the UI

`http://127.0.0.1:5000`

## End-to-End Workflow

1. User records audio or uploads an audio file.
2. Flask receives the audio.
3. faster-whisper/Whisper transcribes it.
4. Flask obtains the transcript.
5. Flask sends the transcript to llama-server.
6. llama-server runs Qwen3-4B.
7. Qwen generates a summary or other requested response.
8. Flask displays the transcript and generated result.

## Why Two AI Models?

Whisper and Qwen solve different problems:

```text
Speech --> Whisper --> Text --> Qwen --> Summary
```

Whisper specializes in speech recognition. Qwen specializes in language understanding and generation.

## Why llama.cpp?

The Qwen model is stored as a GGUF file. llama.cpp loads and executes that model. `llama-server` exposes the inference capability through HTTP, allowing Flask to use Qwen without implementing model inference itself.

## Directory Structure

```text
E:\AI\
├── llama.cpp\
│   └── llama-server.exe
├── models\
│   ├── qwen\
│   │   └── Qwen3-4B-Q4_K_M.gguf
│   └── whisper\
├── hf-cache\
│   └── hub\
│       └── models--Systran--faster-whisper-large-v3
└── venv\
    ├── Scripts\python.exe
    └── Lib\site-packages\
        ├── faster_whisper
        ├── flask
        └── requests
```
Application:
`C:\Users\M_Hamza\local_qwen_web.py`



## Technical Description

> A local multi-model AI audio assistant built with Flask, faster-whisper, Whisper large-v3, Qwen3-4B, and llama.cpp. It supports both browser-based recording and existing audio-file uploads. faster-whisper performs local speech-to-text transcription, while Qwen3-4B performs natural-language processing and summarization through the llama.cpp OpenAI-compatible HTTP server. Flask orchestrates the complete workflow and provides the browser interface.
