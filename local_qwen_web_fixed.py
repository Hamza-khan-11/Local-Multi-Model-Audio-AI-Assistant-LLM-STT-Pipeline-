from flask import Flask, request, jsonify, render_template_string
from faster_whisper import WhisperModel
import requests
import tempfile
import os
import threading

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB

# -----------------------------
# Settings
# -----------------------------
QWEN_URL = "http://127.0.0.1:8080/v1/chat/completions"

# Bypass the Windows corporate proxy for localhost Qwen requests.
qwen_session = requests.Session()
qwen_session.trust_env = False

# Good CPU starting point.
# "tiny" = fastest, "base" = better accuracy, "small" = better but slower.
WHISPER_SIZE = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE = "int8"

print("Loading Whisper model...")
whisper_model = WhisperModel(
    WHISPER_SIZE,
    device=WHISPER_DEVICE,
    compute_type=WHISPER_COMPUTE,
    cpu_threads=8,
)
print("Whisper ready.")

# -----------------------------
# Web UI
# -----------------------------
HTML = r"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Local AI Audio Assistant</title>
<style>
    * { box-sizing: border-box; }
    body {
        margin: 0;
        font-family: Arial, sans-serif;
        background: #101114;
        color: #f5f5f5;
    }
    .container {
        max-width: 1000px;
        margin: 35px auto;
        padding: 20px;
    }
    h1 { margin-bottom: 6px; }
    .subtitle { color: #aaa; margin-bottom: 25px; }
    .card {
        background: #191b20;
        border: 1px solid #30333a;
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 18px;
    }
    .buttons {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
    }
    button, .file-label {
        border: 0;
        border-radius: 10px;
        padding: 13px 18px;
        font-size: 15px;
        cursor: pointer;
        background: #2d6cdf;
        color: white;
        display: inline-block;
    }
    button:hover, .file-label:hover { opacity: .9; }
    button.stop { background: #b83232; }
    button.secondary { background: #444850; }
    input[type=file] { display: none; }
    #timer {
        font-size: 25px;
        margin: 15px 0;
        font-family: monospace;
    }
    #fileName {
        margin-top: 12px;
        color: #bfc5d2;
    }
    #status {
        margin-top: 15px;
        color: #79b8ff;
        white-space: pre-wrap;
    }
    .result {
        background: #111216;
        border: 1px solid #2c2f36;
        border-radius: 10px;
        padding: 18px;
        line-height: 1.6;
        white-space: pre-wrap;
        min-height: 80px;
    }
    .hidden { display: none; }
    .recording {
        color: #ff6565;
        font-weight: bold;
    }
</style>
</head>
<body>
<div class="container">
    <h1>🎙 Local AI Audio Assistant</h1>
    <div class="subtitle">
        Record or upload audio → local Whisper transcription → local Qwen summary
    </div>

    <div class="card">
        <h2>1. Choose audio</h2>

        <div class="buttons">
            <button id="startBtn" onclick="startRecording()">🎙 Start Recording</button>
            <button id="stopBtn" class="stop hidden" onclick="stopRecording()">⏹ Stop Recording</button>

            <label class="file-label">
                📁 Upload Audio
                <input id="audioFile" type="file"
                       accept="audio/*,.mp3,.wav,.m4a,.webm,.ogg,.flac"
                       onchange="fileSelected()">
            </label>

            <button class="secondary" onclick="clearAudio()">🗑 Clear</button>
        </div>

        <div id="timer">00:00</div>
        <div id="fileName">No audio selected.</div>
        <div id="status"></div>
    </div>

    <div class="card">
        <h2>2. Process audio</h2>
        <button id="processBtn" onclick="processAudio()">🚀 Transcribe & Summarize</button>
    </div>

    <div class="card">
        <h2>📝 Transcript</h2>
        <div id="transcript" class="result">Nothing transcribed yet.</div>
    </div>

    <div class="card">
        <h2>🧠 Summary</h2>
        <div id="summary" class="result">Nothing summarized yet.</div>
    </div>
</div>

<script>
let mediaRecorder = null;
let audioChunks = [];
let recordedBlob = null;
let timerInterval = null;
let startTime = null;

function setStatus(text) {
    document.getElementById("status").textContent = text;
}

function formatTime(seconds) {
    const m = String(Math.floor(seconds / 60)).padStart(2, "0");
    const s = String(seconds % 60).padStart(2, "0");
    return `${m}:${s}`;
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({audio: true});

        audioChunks = [];
        recordedBlob = null;

        let options = {};
        if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
            options.mimeType = "audio/webm;codecs=opus";
        }

        mediaRecorder = new MediaRecorder(stream, options);

        mediaRecorder.ondataavailable = e => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
            recordedBlob = new Blob(audioChunks, {
                type: mediaRecorder.mimeType || "audio/webm"
            });

            stream.getTracks().forEach(track => track.stop());

            document.getElementById("fileName").textContent =
                "🎙 Recorded audio (" +
                Math.round(recordedBlob.size / 1024) + " KB)";

            setStatus("Recording ready. Click Transcribe & Summarize.");
        };

        mediaRecorder.start();

        document.getElementById("startBtn").classList.add("hidden");
        document.getElementById("stopBtn").classList.remove("hidden");
        document.getElementById("audioFile").value = "";

        startTime = Date.now();
        document.getElementById("timer").textContent = "00:00";

        timerInterval = setInterval(() => {
            const seconds = Math.floor((Date.now() - startTime) / 1000);
            document.getElementById("timer").textContent = formatTime(seconds);
        }, 1000);

        setStatus("🔴 Recording...");
        document.querySelector(".subtitle").classList.add("recording");

    } catch (err) {
        setStatus("Microphone error: " + err.message);
    }
}

function stopRecording() {
    if (!mediaRecorder || mediaRecorder.state === "inactive") return;

    mediaRecorder.stop();

    clearInterval(timerInterval);

    document.getElementById("startBtn").classList.remove("hidden");
    document.getElementById("stopBtn").classList.add("hidden");
    document.querySelector(".subtitle").classList.remove("recording");

    setStatus("Recording stopped.");
}

function fileSelected() {
    const input = document.getElementById("audioFile");

    if (!input.files.length) return;

    recordedBlob = null;

    const file = input.files[0];

    document.getElementById("fileName").textContent =
        "📁 " + file.name + " (" +
        Math.round(file.size / 1024) + " KB)";

    setStatus("File selected. Click Transcribe & Summarize.");
}

function clearAudio() {
    recordedBlob = null;
    document.getElementById("audioFile").value = "";
    document.getElementById("fileName").textContent = "No audio selected.";
    document.getElementById("transcript").textContent = "Nothing transcribed yet.";
    document.getElementById("summary").textContent = "Nothing summarized yet.";
    document.getElementById("timer").textContent = "00:00";
    setStatus("");
}

async function processAudio() {
    const input = document.getElementById("audioFile");

    if (!recordedBlob && !input.files.length) {
        setStatus("Please record audio or choose an audio file first.");
        return;
    }

    const form = new FormData();

    if (recordedBlob) {
        form.append("audio", recordedBlob, "recording.webm");
    } else {
        form.append("audio", input.files[0]);
    }

    const processBtn = document.getElementById("processBtn");
    processBtn.disabled = true;
    processBtn.textContent = "⏳ Processing...";
    setStatus("Transcribing audio with local Whisper...");

    try {
        const response = await fetch("/process", {
            method: "POST",
            body: form
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Processing failed.");
        }

        document.getElementById("transcript").textContent = data.transcript;
        setStatus("Transcript complete. Qwen is creating the summary...");
        document.getElementById("summary").textContent = data.summary;

        setStatus("✅ Complete. Audio was processed locally.");

    } catch (err) {
        setStatus("❌ " + err.message);
    } finally {
        processBtn.disabled = false;
        processBtn.textContent = "🚀 Transcribe & Summarize";
    }
}
</script>
</body>
</html>
"""

# -----------------------------
# Qwen summarizer
# -----------------------------
def summarize_with_qwen(transcript):
    if not transcript.strip():
        return "No speech was detected."

    prompt = f"""Summarize the following transcript clearly.

Use this format:

SUMMARY:
A short paragraph summarizing the main topic.

KEY POINTS:
- Important point
- Important point
- Important point

ACTION ITEMS:
- Task, if any
- Task, if any

IMPORTANT DETAILS:
- Dates, names, decisions, numbers, or other useful details

If a section has no information, write "None".

Transcript:
{transcript}
"""

    body = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful local AI assistant. "
                    "Summarize transcripts accurately. "
                    "Do not invent facts that are not present in the transcript."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "max_tokens": 700,
        "reasoning_effort": "none"
    }

    r = qwen_session.post(QWEN_URL, json=body, timeout=300)
    r.raise_for_status()

    data = r.json()
    return data["choices"][0]["message"].get("content", "").strip()

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/process", methods=["POST"])
def process():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file received."}), 400

    uploaded = request.files["audio"]

    if not uploaded.filename:
        return jsonify({"error": "Audio filename is empty."}), 400

    suffix = os.path.splitext(uploaded.filename)[1].lower()
    if not suffix:
        suffix = ".webm"

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_path = tmp.name
            uploaded.save(temp_path)

        print("Transcribing:", uploaded.filename)

        segments, info = whisper_model.transcribe(
            temp_path,
            beam_size=5,
            vad_filter=True,
        )

        transcript = " ".join(
            segment.text.strip()
            for segment in segments
            if segment.text.strip()
        ).strip()

        if not transcript:
            return jsonify({
                "error": "Whisper could not detect any speech in the audio."
            }), 400

        print("Transcript length:", len(transcript))

        print("Sending transcript to local Qwen...")
        summary = summarize_with_qwen(transcript)

        return jsonify({
            "transcript": transcript,
            "summary": summary,
            "language": info.language,
            "language_probability": info.language_probability
        })

    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": (
                "Could not reach Qwen at 127.0.0.1:8080. "
                "Make sure llama-server.exe is still running. "
                f"Details: {e}"
            )
        }), 502

    except Exception as e:
        print("ERROR:", repr(e))
        return jsonify({"error": str(e)}), 500

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

if __name__ == "__main__":
    print()
    print("==========================================")
    print(" Local Qwen Audio Assistant")
    print("==========================================")
    print("Open: http://127.0.0.1:5000")
    print()
    app.run(host="127.0.0.1", port=5000, debug=False)
