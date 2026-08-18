# Local-Multi-Model-Audio-AI-Assistant-LLM-STT-Pipeline-
The application accepts audio through direct browser recording or existing-file upload. Flask orchestrates the workflow.  faster-whisper runs Whisper large-v3 locally for speech-to-text. The transcript is then sent through HTTP to llama.cpp's local  server, which runs the Qwen3-4B GGUF model for summarization and other language tasks.
