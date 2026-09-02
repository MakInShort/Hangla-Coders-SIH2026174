# BAS Experiment Assistant

An AI-powered autonomous experiment execution and validation assistant for human spaceflight, built for the SIH 2026 ISRO problem statement: *"AI Human Activity Recognition for On-board BAS Experiments."*

The system watches an astronaut perform a predefined experiment protocol through a camera, recognizes which step is being performed using hand tracking, object detection, and a trained classifier, validates it against the expected sequence using a deterministic FSM, and guides/records the outcome. It follows the loop: **Observe → Understand → Predict → Validate → Guide → Record**.

> This is **protocol-aware** step recognition, not generic activity recognition. The system asks: *"What experiment step is happening now, is it valid at this point, and what should happen next?"*

---

## Features

- Protocol-aware step recognition using MediaPipe hand landmarks + YOLO object features + XGBoost classifier
- Deterministic FSM sequence validation with skip, repeat, and out-of-sequence detection
- Wireless microphone experiment protocol (M0–M6) with G1/G2 LED verification gates
- PySide6 mission-control dashboard: live annotated video, full protocol progression,
  verification-gate panel (G1/G2 badges, receiver LED indicators, receiver detection),
  telemetry chips, color-coded event log, and START/PAUSE/STOP/RESET session control
- JSONL session logging for recorded runs
- Offline/no-camera smoke testing via dummy video sources
- Camera diagnostics for backend and frame-rate verification

---

## Project Structure

```
bas-assistant/
├── configs/default.yaml          # Typed Pydantic config
├── data/                         # raw/, processed/, samples/
├── docs/                         # ADRs, architecture, runbooks, GPU guides
├── models/                       # Trained artifacts (.task/.json)
├── runs/                         # Model training checkpoints & evaluation curves
├── scripts/                      # Entry points (run_pipeline, run_demo, run_dashboard)
├── src/bas_assistant/            # Main core package
│   ├── pipeline/                 # Frame processing orchestration
│   ├── video/                    # Video source handling
│   ├── detection/                # Person & object detection (YOLO)
│   ├── tracking/                 # Person tracking
│   ├── pose/                     # Hand tracking (MediaPipe Hands)
│   ├── features/                 # Spatial + temporal feature extraction
│   ├── classification/           # Step classifier (Dummy / XGBoost)
│   ├── validation/               # Deterministic FSM sequence validation
│   ├── events/                   # Event manager
│   ├── storage/                  # JSONL session logs
│   ├── ui/                       # Presentation layers (PySide6 Desktop & Streamlit)
│   │   ├── dashboard.py          # PySide6 Mission Control desktop UI
│   │   └── streamlit/            # Streamlit web presentation components & tabs
│   └── utils/                    # Shared visualization & logging utilities
├── tests/                        # Unit + integration tests (114 passing)
├── weights/                      # Base pretrained model weights (.pt)
├── streamlit_app.py              # Streamlit Web Mission Control app entrypoint
├── requirements.txt              # Cloud deployment dependencies
└── pyproject.toml                # Build config (hatchling)
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Package Manager | `uv` (recommended) or `pip` |
| Hand tracking | MediaPipe Hands (pretrained, frozen) |
| Step Classifier | XGBoost (scikit-learn) |
| Sequence Validation | Deterministic FSM (hand-rolled) |
| GUI | PySide6 |
| Config | PyYAML + Pydantic Settings |
| Session Logs | JSONL (SQLite reserved for future) |
| Testing | pytest |
| Linting | Ruff, Black |
| CI | GitHub Actions (Ubuntu) |

---

## Prerequisites (All OS)

- **Git** — [git-scm.com](https://git-scm.com)
- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **uv** (recommended) — or use `pip` as fallback
- A webcam is optional; `--source dummy` works without hardware

---

## Windows Setup

### 1. Install prerequisites

```powershell
# Check versions
python --version
git --version

# Install uv (recommended)
winget install --id=astral-sh.uv -e
```

Restart PowerShell after installing `uv`. If you prefer not to use `uv`, skip to the pip fallback below.

### 2. Clone and install

```powershell
git clone https://github.com/Hangla-Coders/SIH2026174.git
cd SIH2026174

# Using uv (recommended)
uv sync --all-extras

# --- OR using pip (fallback) ---
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[all]"
```

### 3. Review config

```powershell
notepad configs\default.yaml
```

Key settings: `camera.device` (webcam index), `pose.model` (`mediapipe` or `dummy`), `classifier.model_type` (`dummy` or `xgboost`).

Environment overrides:

```powershell
$env:BAS_CAMERA__DEVICE = "0"
$env:BAS_CLASSIFIER__MODEL_TYPE = "dummy"
```

### 4. Run

```powershell
# Headless pipeline (no camera needed)
python scripts\run_pipeline.py --source dummy --pose dummy --max-frames 300

# Interactive demo (no camera needed)
python scripts\run_demo.py --source dummy --pose dummy --max-frames 300

# Live webcam demo
python scripts\run_demo.py --source 0

# Dashboard
python scripts\run_dashboard.py --source 0              # webcam 0
python scripts\run_dashboard.py --source path\video.mp4 # recorded video
python scripts\run_dashboard.py --source dummy          # offline smoke test
```

### Dashboard

The PySide6 dashboard is fully wired to the live pipeline — all displayed state
(steps, gates, LEDs, receiver, protocol completion) comes from the backend via
public pipeline properties; the UI derives nothing on its own.

Panels:

| Panel | Backend source |
|---|---|
| Live video feed | Annotated frame (`utils/visualization.annotate_frame`) |
| Telemetry chips (status / FPS / persons / latency / events) | `FrameResult` |
| Protocol progression (M0–M6 + G1/G2 rows: done / active / pending) | FSM `done_steps`, `expected_next`, `gate_status` |
| Verification gates (G1/G2 badges, left/right LED lamps, receiver status) | `pipeline.gate_status`, `pipeline.led_observation` |
| Step confidence gauge | XGBoost classification confidence |
| Activity log (color-coded events incl. gate events) | `EventManager` events |
| START / PAUSE / STOP / RESET | Pipeline session lifecycle (`start_session`/`end_session` resets FSM, votes, LED history) |

```bash
# Offline dashboard smoke test (no camera, no models needed)
uv run python scripts/run_dashboard.py --source dummy --pose dummy --classifier dummy
```

### Streamlit Web Dashboard (Browser & Cloud)

The Streamlit dashboard (`streamlit_app.py`) provides a web-deployable version of the Space Mission Control UI with live video playback, WebRTC browser streaming, training evaluation curves, and interactive FSM architecture diagrams:

```bash
# Run local Streamlit web dashboard
uv run streamlit run streamlit_app.py
```

For full cloud, Docker, and WebRTC setup instructions, refer to the [Streamlit Deployment Guide](docs/streamlit-deployment-guide.md).

### 5. Verify

```powershell
python -m pytest
python -m ruff check .
python -m black --check src scripts tests
```

### Windows Troubleshooting

- **Camera blocked?** Use `--source dummy`.
- **MediaPipe import fails?** Ensure dependencies are installed in the same active Python environment.
- **Low FPS?** Check `camera.format: MJPG` in config and run `python scripts\camera_diagnostic.py`.
- **Execution policy error?** Run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.

---

## Linux Setup

### 1. Install prerequisites

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip curl

# Install uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc   # or ~/.zshrc
```

### 2. Clone and install

```bash
git clone https://github.com/Hangla-Coders/SIH2026174.git
cd SIH2026174

# Using uv (recommended)
uv sync --all-extras

# --- OR using pip (fallback) ---
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[all]"
```

### 3. Review config

```bash
nano configs/default.yaml
```

Environment overrides:

```bash
export BAS_CAMERA__DEVICE=0
export BAS_CLASSIFIER__MODEL_TYPE=dummy
```

### 4. Run

```bash
# Headless pipeline (no camera needed)
uv run python scripts/run_pipeline.py --source dummy --pose dummy --max-frames 300

# Interactive demo (no camera needed)
uv run python scripts/run_demo.py --source dummy --pose dummy --max-frames 300

# Live webcam demo
uv run python scripts/run_demo.py --source 0

# Dashboard
uv run python scripts/run_dashboard.py --source 0
```

### 5. Verify

```bash
uv run pytest
uv run ruff check .
uv run black --check src scripts tests
```

### Linux Troubleshooting

- **Camera not available?** Use `--source dummy`, or check permissions with `v4l2-ctl --list-devices`.
- **Low FPS?** The UVC driver may throttle to ~17 fps under auto-exposure. Set `camera.disable_dynamic_framerate: true` in config (requires `v4l2-ctl`).
- **XDG errors?** Ensure your user has video group access: `sudo usermod -aG video $USER` (re-login required).

---

## macOS Setup

### 1. Install prerequisites

```bash
# Xcode Command Line Tools
xcode-select --install

# Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python, Git, uv
brew install python git
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc
```

### 2. Clone and install

```bash
git clone https://github.com/Hangla-Coders/SIH2026174.git
cd SIH2026174

# Using uv (recommended)
uv sync --all-extras

# --- OR using pip (fallback) ---
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[all]"
```

### 3. Review config

```bash
nano configs/default.yaml
```

Environment overrides:

```bash
export BAS_CAMERA__DEVICE=0
export BAS_CLASSIFIER__MODEL_TYPE=dummy
```

### 4. Run

```bash
# Headless pipeline (no camera needed)
uv run python scripts/run_pipeline.py --source dummy --pose dummy --max-frames 300

# Interactive demo (no camera needed)
uv run python scripts/run_demo.py --source dummy --pose dummy --max-frames 300

# Live webcam demo
uv run python scripts/run_demo.py --source 0

# Dashboard
uv run python scripts/run_dashboard.py --source 0
```

### 5. Verify

```bash
uv run pytest
uv run ruff check .
uv run black --check src scripts tests
```

### macOS Troubleshooting

- **Camera fails?** Grant camera permission to Terminal/Python in System Settings → Privacy & Security → Camera. Or use `--source dummy`.
- **Homebrew Python shadows system Python?** Use `python3` explicitly.
- **Package install fails?** Recreate the environment: `rm -rf .venv && uv sync --all-extras`.

---

## Project Commands Reference

| Command | Description |
|---|---|
| `uv sync --all-extras` | Install all dependencies |
| `uv run python scripts/run_pipeline.py --source dummy --pose dummy` | Run headless pipeline |
| `uv run python scripts/run_demo.py --source dummy --pose dummy` | Run interactive demo |
| `uv run python scripts/run_demo.py --source 0` | Run with live webcam |
| `uv run python scripts/run_dashboard.py --source 0` | Launch PySide6 dashboard (webcam) |
| `uv run python scripts/run_dashboard.py --source <video.mp4>` | Dashboard on a recorded video |
| `uv run python scripts/run_dashboard.py --source dummy` | Dashboard offline smoke test |
| `uv run python scripts/camera_diagnostic.py` | Camera diagnostics |
| `uv run python scripts/download_mediapipe_models.py` | Download MediaPipe models |
| `uv run pytest` | Run tests |
| `uv run ruff check .` | Lint check |
| `uv run black --check src scripts tests` | Format check |

---

## Environment Variables

All config can be overridden via `BAS_`-prefixed environment variables (double underscore for nesting):

| Variable | Purpose | Default |
|---|---|---|
| `BAS_CAMERA__DEVICE` | Camera index or video file path | `0` |
| `BAS_CAMERA__WIDTH` | Capture width | `1280` |
| `BAS_CAMERA__HEIGHT` | Capture height | `720` |
| `BAS_CAMERA__FPS` | Capture frame rate | `30` |
| `BAS_POSE__MODEL` | Pose model: `mediapipe` or `dummy` | `mediapipe` |
| `BAS_CLASSIFIER__MODEL_TYPE` | Classifier: `dummy` or `xgboost` | `dummy` |
| `BAS_DATABASE__URL` | SQLite connection string | `sqlite:///data/project.db` |

No API keys or secrets are required.

---

## Architecture

```
Camera / Video Source
        ↓
Person Detection (stub)
        ↓
Person Tracking (stub)
        ↓
Hand Tracking (MediaPipe Hands or dummy)
        ↓
Pose Normalization (translation + scale)
        ↓
Feature Extraction (spatial + temporal)
        ↓
Step Classifier (XGBoost or dummy)
        ↓
FSM Sequence Validation
        ↓
Event Manager
        ↓
JSONL Session Log / PySide6 Dashboard
```

Each stage is behind a protocol-based interface and is independently replaceable.

---

## License

MIT License. See [LICENSE](LICENSE).

---

## Acknowledgments

Built by [Hangla Coders](https://github.com/Hangla-Coders) for SIH 2026 — ISRO Problem Statement on AI Human Activity Recognition for On-board BAS Experiments.
