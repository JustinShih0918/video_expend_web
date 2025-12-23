# GAN Video Outpainting Web App

This is a video extension application platform based on Generative Adversarial Networks (GANs). This project aims to automatically repair and extend the peripheral vision of video frames using deep learning models, providing a modern web interface for users to upload, process, and view real-time "Original vs. Extended" synchronized comparisons.

**Note**: This is a web application built from the [imageExtend](https://github.com/JustinShih0918/imageExtend.git) project.

-----

## Quick Start

We provide two methods for starting the application. **Docker deployment is recommended** for ease of setup and consistency across different platforms.

### Option A: Docker Deployment (Recommended)

This method provides a consistent environment without manually configuring Python/Node dependencies.

#### 1. Prerequisites

  * Install **Docker Desktop** (includes Docker Compose)

#### 2. Download & Place Model Weights

Download the pretrained model and place it in the checkpoints directory:

1. **Download the pretrained model**: [G_epoch_063.pt](https://drive.google.com/file/d/1bRubCe_ZZlu8Vu95C4BUnEU45e_mm0FO/view?usp=drive_link)
2. **Place it here**: \`backend/checkpoints/G_epoch_063.pt\`

> The training code and process for this model can be found in the [imageExtend](https://github.com/JustinShih0918/imageExtend.git) repository.

#### 3. Start Container

Run the following command in the project root:

\`\`\`bash
docker compose up --build
\`\`\`

After startup, access:

  * **Frontend Interface**: [http://localhost](http://localhost) (Docker maps to Port 80)
  * **Backend API Docs**: [http://localhost/docs](http://localhost/docs)

> **Note**: Docker Desktop on Mac currently cannot directly access MPS GPUs. Therefore, running Docker on a Mac will default to **CPU mode**, which is significantly slower. Mac users seeking better performance should consider **Option B (Local Deployment)**.

-----

### Option B: Local Deployment

This method allows direct access to local GPU resources (e.g., Mac MPS or Windows CUDA) for better performance on supported hardware.

#### 1. Prerequisites

Ensure your computer has the following installed:

  * **Python 3.9+**
  * **Node.js 18+** (LTS)
  * **FFmpeg** (Must be added to the system PATH)
      * *Mac*: \`brew install ffmpeg\`
      * *Windows*: [Download FFmpeg](https://ffmpeg.org/download.html) and configure PATH.

#### 2. Download & Place Model Weights

Download the pretrained model checkpoint and place it in the checkpoints directory:

1. **Download the pretrained model**: [G_epoch_063.pt](https://drive.google.com/file/d/1bRubCe_ZZlu8Vu95C4BUnEU45e_mm0FO/view?usp=drive_link)
2. **Place it here**: \`backend/checkpoints/G_epoch_063.pt\`

> The training code and process for this model can be found in the [imageExtend](https://github.com/JustinShih0918/imageExtend.git) repository.

**Model Architecture:**
- Input: 192x192 RGB frames (automatically resized)
- Processing: Frames placed in 256x256 canvas with masked borders
- Model: UNetGenerator (4 input channels: 3 RGB + 1 mask, 3 output channels)
- Output: 256x256 expanded frames

#### 3. Install & Run

We provide a one-click script that automatically creates the virtual environment and installs npm dependencies.

**Mac / Linux / Windows (Git Bash):**

\`\`\`bash
# 1. Grant execution permissions (Run once)
chmod +x scripts/install.sh scripts/run.sh

# 2. Install Environment (Run once)
./scripts/install.sh

# 3. Start Services (Run every time you develop)
./scripts/run.sh
\`\`\`

After startup, access:

  * **Frontend Interface**: [http://localhost:5173](http://localhost:5173)
  * **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

-----

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

## API Usage

The backend provides additional parameters for advanced video processing:

### Basic Upload
\`\`\`bash
curl -X POST "http://localhost:8000/upload" \\
  -F "file=@video.mp4"
\`\`\`

### Frame Sampling (Reduce Output FPS)
Process only N frames per second (useful for faster processing and smaller output):
\`\`\`bash
curl -X POST "http://localhost:8000/upload" \\
  -F "file=@video.mp4" \\
  -F "frames_count=1"
\`\`\`

### Restore Original Aspect Ratio
By default, output is square (256x256). Enable this to restore original video proportions:
\`\`\`bash
curl -X POST "http://localhost:8000/upload" \\
  -F "file=@video.mp4" \\
  -F "restore_size=true"
\`\`\`

### Combined Parameters
\`\`\`bash
curl -X POST "http://localhost:8000/upload" \\
  -F "file=@video.mp4" \\
  -F "frames_count=1" \\
  -F "restore_size=true"
\`\`\`

**API Documentation**: Visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API docs.

-----

## Project Structure

\`\`\`text
.
├── backend/
│   ├── checkpoints/       # [Important] Place model weights here (download G_epoch_063.pt)
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
\`\`\`

-----

## About This Repository

### Completeness & Organization

This repository contains a **complete, production-ready web application** with:

**All Relevant Code**
- Full-stack implementation (React frontend + FastAPI backend)
- GAN inference pipeline with UNetGenerator model architecture
- Video processing utilities and FFmpeg integration
- Docker configuration for containerized deployment

**Dataset & Model Access**
- **Pretrained Model**: Download the trained GAN model checkpoint here:
  - [Download G_epoch_063.pt](https://drive.google.com/file/d/1bRubCe_ZZlu8Vu95C4BUnEU45e_mm0FO/view?usp=drive_link)
  - Place in \`backend/checkpoints/\` directory
- **Training Code & Dataset**: See the original [imageExtend](https://github.com/JustinShih0918/imageExtend.git) repository for model training code and dataset information

**Results & Demonstrations**
- Processed videos are stored in \`backend/results/\` after processing
- Side-by-side comparison viewer for evaluating results
- Interactive API documentation at \`/docs\` endpoint

### Repository Structure

The repository is organized intuitively with clear separation of concerns:

**Navigation is straightforward:**
- \`backend/\` for all server-side code
- \`frontend/\` for all client-side code
- \`scripts/\` for development automation
- Root-level configs for deployment

### Reproducibility

**Complete instructions are provided for reproducing results:**

1. **Setup Instructions**: Automated scripts (\`install.sh\`) handle all dependencies
2. **Multiple Deployment Options**: Local development and Docker deployment both documented
3. **Model Download Instructions**: Clear guidance on obtaining and placing the pretrained model
4. **API Documentation**: Interactive Swagger/OpenAPI docs for programmatic access
5. **Configuration Options**: Documented parameters for frame sampling, aspect ratio restoration, etc.
6. **Hardware Acceleration**: Instructions for MPS (Mac), CUDA (Windows/Linux), and CPU fallback

**Time to Reproduce**: With the pretrained model, results can be reproduced in under 5 minutes using the provided scripts.

-----

© 2025 AI Video Expansion Project
