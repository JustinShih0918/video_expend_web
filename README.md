# GAN Video Outpainting Web App

This is a video extension application platform based on Generative Adversarial Networks (GANs). This project aims to automatically repair and extend the peripheral vision of video frames using deep learning models, providing a modern web interface for users to upload, process, and view real-time "Original vs. Extended" synchronized comparisons.

you can find our model training project at here: [imageExtend](https://github.com/JustinShih0918/imageExtend.git)

## Features

  * **AI Video Outpainting**: Uses UNet-based GAN models to perform outpainting on every frame, expanding 192x192 input to 256x256 output.
  * **Automated Pipeline**: The backend automatically handles frame extraction, inference, synthesis, and H.264 transcoding via FFmpeg.
  * **Hardware Acceleration Support**:
      * **macOS**: Supports **MPS (Metal Performance Shaders)** acceleration (M1/M2/M3).
      * **Windows/Linux**: Supports **NVIDIA CUDA** acceleration.
      * **CPU**: Automatic fallback support.
  * **Flexible Processing**:
      * Frame sampling support for reduced output file size
      * Aspect ratio restoration option
      * Configurable input/output sizes
  * **Synchronized Player**: Supports side-by-side synchronized playback, pausing, and seeking for the original and extended videos.

## Tech Stack

  * **Frontend**: React 18, Vite
  * **Backend**: Python FastAPI, Uvicorn
  * **Core Logic**: PyTorch (Inference), OpenCV, FFmpeg
  * **Deployment**: Docker & Local Scripts

-----

## Quick Start

We provide two methods for starting the application: **Local Deployment** and **Docker Container**.

### Option A: Local Deployment (Recommended for Dev)

This method allows direct access to local GPU resources (e.g., Mac MPS or Windows CUDA) for the best performance.

#### 1\. Prerequisites

Ensure your computer has the following installed:

  * **Python 3.9+**
  * **Node.js 18+** (LTS)
  * **FFmpeg** (Must be added to the system PATH)
      * *Mac*: `brew install ffmpeg`
      * *Windows*: [Download FFmpeg](https://ffmpeg.org/download.html) and configure PATH.

#### 2\. Place Model Weights

Place your trained UNetGenerator model checkpoint (e.g., `G_epoch_010.pt`) in the following path:
`backend/checkpoints/G_epoch_010.pt`

**Model Architecture:**
- Input: 192x192 RGB frames (automatically resized)
- Processing: Frames placed in 256x256 canvas with masked borders
- Model: UNetGenerator (4 input channels: 3 RGB + 1 mask, 3 output channels)
- Output: 256x256 expanded frames

#### 3\. Install & Run

We provide a one-click script that automatically creates the virtual environment and installs npm dependencies.

**Mac / Linux / Windows (Git Bash):**

```bash
# 1. Grant execution permissions (Run once)
chmod +x scripts/install.sh scripts/run.sh

# 2. Install Environment (Run once)
./scripts/install.sh

# 3. Start Services (Run every time you develop)
./scripts/run.sh
```

After startup, access:

  * **Frontend Interface**: [http://localhost:5173](https://www.google.com/search?q=http://localhost:5173)
  * **Backend API Docs**: [http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs)

-----

### Option B: Docker Quick Start

Suitable for quick previews or server deployment without manually configuring Python/Node environments.

#### 1\. Prerequisites

  * Install **Docker Desktop**.

#### 2\. Place Model Weights

Similarly, place `G_epoch_010.pt` into `backend/checkpoints/`.

#### 3\. Start Container

Run the following command in the project root:

```bash
docker compose up --build
```

After startup, access:

  * **Frontend Interface**: [http://localhost](https://www.google.com/search?q=http://localhost) (Docker maps to Port 80)

> **Note**: Docker Desktop on Mac currently cannot directly access MPS GPUs. Therefore, running Docker on a Mac will default to **CPU mode**, which is significantly slower. Mac users are strongly advised to use **Option A (Local Deployment)**.

-----

## API Usage

The backend provides additional parameters for advanced video processing:

### Basic Upload
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@video.mp4"
```

### Frame Sampling (Reduce Output FPS)
Process only N frames per second (useful for faster processing and smaller output):
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@video.mp4" \
  -F "frames_count=1"
```

### Restore Original Aspect Ratio
By default, output is square (256x256). Enable this to restore original video proportions:
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@video.mp4" \
  -F "restore_size=true"
```

### Combined Parameters
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@video.mp4" \
  -F "frames_count=1" \
  -F "restore_size=true"
```

**API Documentation**: Visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API docs.

-----

## Project Structure

```text
.
├── backend/
│   ├── checkpoints/       # [Important] Place model weights here (G_epoch_010.pt)
│   ├── models/            # UNetGenerator model architecture
│   │   ├── generator.py   # Model definition
│   │   └── __init__.py
│   ├── utils/             # Utility functions
│   │   ├── mask_utils.py  # Mask processing utilities
│   │   └── __init__.py
│   ├── uploads/           # Temporary upload storage
│   ├── results/           # Processed video storage (Cleared on restart)
│   ├── main.py            # FastAPI Entry point
│   ├── core_logic.py      # Core logic (UNetGenerator Inference + FFmpeg)
│   └── requirements.txt   # Backend dependencies
├── frontend/
│   ├── src/               # React Source code
│   └── vite.config.js     # Frontend config (Includes API Proxy)
├── scripts/
│   ├── install.sh         # Cross-platform Setup Script
│   └── run.sh             # Cross-platform Launcher Script
├── docker-compose.yml     # Docker config
└── README.md
```

## FAQ

1.  **Uploaded video cannot play (Black screen)?**

      * This is usually because browsers do not support OpenCV's default `mp4v` codec. This project uses FFmpeg to transcode to H.264 (`libx264`) automatically. Please ensure FFmpeg is correctly installed on your system.

2.  **Cannot find `G_epoch_010.pt`?**

      * Due to file size limits, `.pt` files are not included in the Git repository. Please obtain the weight file from your team members and place it in `backend/checkpoints/`. The model uses UNetGenerator architecture trained for image outpainting (192x192 → 256x256).

3.  **How to collaborate?**

      * After cloning the project, simply need to run `./install.sh`. This script will automatically restore the development environment (including `node_modules` and `.venv`).

-----

© 2025 AI Video Expansion Project