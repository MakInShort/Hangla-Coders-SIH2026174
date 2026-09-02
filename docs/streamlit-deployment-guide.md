# Streamlit Deployment Guide

This guide outlines how to deploy the **BAS Experiment Assistant** Streamlit web dashboard across different environments: **Streamlit Community Cloud**, **Local Network / On-Premises**, and **Docker**.

---

## 1. Streamlit Community Cloud (Recommended for Demos)

Streamlit Community Cloud allows free public deployment directly linked to your GitHub repository.

### Prerequisites in Repository Root
Ensure the following files are present in the root directory:
* [`streamlit_app.py`](../streamlit_app.py): The web app entrypoint.
* [`requirements.txt`](../requirements.txt): Minimal cloud Python dependencies using `opencv-python-headless`.

### Step-by-Step Cloud Deployment

1. **Push Changes to GitHub**:
   Ensure all changes are committed and pushed to your remote repository branch:
   ```bash
   git push origin main
   ```

2. **Access Streamlit Cloud**:
   * Navigate to [share.streamlit.io](https://share.streamlit.io/) and log in with GitHub.
   * Click **"New app"** (or **"Create app"**).

3. **Configure the App**:
   * **Repository**: Select `24f2007601/Hangla-Coders-SIH2026174` (or your repo name).
   * **Branch**: `main`
   * **Main file path**: `streamlit_app.py`
   * **Custom subdomain** *(optional)*: e.g. `isro-bas-assistant.streamlit.app`

4. **Deploy**:
   * Click **"Deploy!"**.
   * Streamlit Cloud will automatically install Python packages from `requirements.txt`, and start the app.
   * On first boot, the app will automatically download the MediaPipe hand landmarker task file (`models/hand_landmarker.task`) from Google Storage.

> [!NOTE]
> **Browser Webcam Permissions**: Users accessing the cloud app must allow browser camera access when using the **Browser Webcam (WebRTC)** mode.

---

## 2. Local & On-Premises Deployment

To run the Streamlit dashboard on your local machine or local area network:

```powershell
# Run using uv in virtual environment
uv run streamlit run streamlit_app.py

# Or with activated venv:
streamlit run streamlit_app.py
```

### Exposing to Local Network (LAN)
To allow other devices (laptops, tablets) on the same Wi-Fi/network to access the dashboard:
```powershell
uv run streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```
Access the dashboard from another device at `http://<YOUR_LOCAL_IP>:8501`.

---

## 3. Docker Deployment

For self-hosted Linux servers or enterprise Kubernetes/Docker clusters:

### 1. Dockerfile
Create a `Dockerfile` in the root directory:

```dockerfile
FROM python:3.11-slim

# Install system dependencies for OpenCV and MediaPipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code and model weights
COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 2. Build & Run
```bash
# Build the Docker image
docker build -t bas-assistant-streamlit .

# Run container on port 8501
docker run -p 8501:8501 bas-assistant-streamlit
```

---

## 4. Architecture & Troubleshooting

### Why `opencv-python-headless` is Used
Standard `opencv-python` requires a graphical display server (X11). In containerized and cloud environments (Streamlit Cloud, Docker), this causes import crashes. `opencv-python-headless` provides full computer vision functionality without display-server dependencies.

### MediaPipe Model Initialization
The app's `get_pipeline()` function includes self-healing logic:
```python
if settings.pose.model == "mediapipe" and not model_path.exists():
    urllib.request.urlretrieve(model_url, model_path)
```
If the environment cannot connect to external URLs (air-gapped networks), the pipeline gracefully falls back to `settings.pose.model = "dummy"` to prevent downtime.

### Video Source Options in Cloud
* **Demo Video (`data/raw/`)**: Analyzes preloaded videos directly on the server.
* **Upload Video File**: Upload `.mp4`, `.avi`, or `.mov` files up to 200MB.
* **Browser Webcam (WebRTC)**: Streams user client webcams to the server over WebRTC.
* **Simulated Feed**: 100-frame synthetic source for smoke tests without media hardware.
