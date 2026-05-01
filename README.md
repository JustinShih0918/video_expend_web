# GAN Video Outpainting Web App

Full-stack AI video outpainting application that extends the visible area around uploaded videos using a trained GAN model. The app provides a React interface, FastAPI backend, PyTorch inference pipeline, FFmpeg video transcoding, Docker deployment, and synchronized before/after playback for visual comparison.

This repository productizes the model training work from [imageExtend](https://github.com/JustinShih0918/imageExtend).

## Resume Summary

Built a full-stack AI video expansion platform that accepts uploaded videos, processes frames through a UNet-based GAN outpainting model, reconstructs H.264 playback videos with FFmpeg, and displays synchronized original-vs-extended comparisons in a modern web UI. The system supports Docker deployment, local GPU acceleration through CUDA or macOS MPS, frame sampling, aspect-ratio restoration, progress tracking, and interactive FastAPI documentation.

## Key Features

- **AI video outpainting**: expands 192x192 input frames into 256x256 generated frames using a trained UNetGenerator.
- **End-to-end video pipeline**: extracts frames, runs PyTorch inference, writes processed videos, and transcodes output to browser-friendly H.264.
- **Full-stack web app**: React frontend communicates with a FastAPI backend for upload, processing status, and result playback.
- **Synchronized comparison viewer**: original and expanded videos can be played, paused, and scrubbed together.
- **Progress tracking**: backend exposes task progress while video processing runs in the background.
- **Flexible processing controls**: supports frame sampling and optional aspect-ratio restoration.
- **Hardware-aware inference**: automatically selects CUDA, macOS MPS, or CPU depending on the local environment.
- **Deployment options**: Docker Compose for repeatable setup and local scripts for GPU-accessible development.

## Architecture

```text
React + Vite frontend
  -> Upload video and processing options
  -> FastAPI backend
  -> Background processing task
  -> OpenCV frame extraction and resizing
  -> PyTorch UNetGenerator inference
  -> FFmpeg H.264 transcoding
  -> Static results served by FastAPI
  -> Synchronized original vs expanded playback
```

## Model Architecture

- Input frame is resized to `192x192`.
- The frame is placed in the center of a `256x256` canvas.
- A binary mask marks the outpainting area.
- The UNetGenerator receives 4 channels: RGB image plus mask.
- The model predicts expanded RGB content for the masked region.
- The final output combines generated borders with the preserved center frame.

## Tech Stack

| Area | Tools |
| --- | --- |
| Frontend | React 19, Vite |
| Backend | FastAPI, Uvicorn |
| ML Inference | PyTorch, TorchVision, UNetGenerator |
| Video Processing | OpenCV, FFmpeg |
| Deployment | Docker Compose, shell scripts |
| Hardware Acceleration | CUDA, macOS MPS, CPU fallback |

## Quick Start

Docker deployment is recommended for the simplest setup. Local deployment is recommended when you want GPU acceleration on supported hardware.

### Option A: Docker Deployment

#### 1. Prerequisites

- Docker Desktop with Docker Compose

#### 2. Download Model Weights

Download the pretrained model and place it in the backend checkpoint directory:

1. Download [G_epoch_063.pt](https://drive.google.com/file/d/1bRubCe_ZZlu8Vu95C4BUnEU45e_mm0FO/view?usp=drive_link)
2. Place it at `backend/checkpoints/G_epoch_063.pt`

#### 3. Start the App

```bash
docker compose up --build
```

After startup:

- Frontend: [http://localhost](http://localhost)
- Backend API docs: [http://localhost/docs](http://localhost/docs)

Docker Desktop on macOS usually runs this in CPU mode. For MPS acceleration on Apple Silicon, use local deployment.

### Option B: Local Deployment

#### 1. Prerequisites

- Python 3.9+
- Node.js 18+
- FFmpeg available on PATH

```bash
# macOS
brew install ffmpeg
```

#### 2. Download Model Weights

Download [G_epoch_063.pt](https://drive.google.com/file/d/1bRubCe_ZZlu8Vu95C4BUnEU45e_mm0FO/view?usp=drive_link) and place it at:

```text
backend/checkpoints/G_epoch_063.pt
```

#### 3. Install and Run

```bash
chmod +x scripts/install.sh scripts/run.sh
./scripts/install.sh
./scripts/run.sh
```

After startup:

- Frontend: [http://localhost:5173](http://localhost:5173)
- Backend API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## API Usage

### Basic Upload

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@video.mp4"
```

### Frame Sampling

Process only `N` frames per second and output at the same FPS:

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@video.mp4" \
  -F "frames_count=1"
```

### Restore Original Aspect Ratio

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@video.mp4" \
  -F "restore_size=true"
```

### Check Task Status

```bash
curl "http://localhost:8000/status/<task_id>"
```

### List Processed Videos

```bash
curl "http://localhost:8000/videos/list"
```

Interactive API documentation is available at `/docs` when the backend is running.

## Project Structure

```text
.
├── backend/
│   ├── checkpoints/          # Place G_epoch_063.pt here
│   ├── models/               # UNetGenerator architecture
│   ├── utils/                # Mask utilities
│   ├── uploads/              # Temporary uploaded videos
│   ├── results/              # Processed output videos
│   ├── main.py               # FastAPI routes and background tasks
│   ├── core_logic.py         # PyTorch inference + OpenCV/FFmpeg video pipeline
│   └── requirements.txt
├── frontend/
│   ├── src/                  # React application
│   └── vite.config.js
├── scripts/
│   ├── install.sh            # Local setup helper
│   └── run.sh                # Local launcher
├── docker-compose.yml
└── README.md
```

## Relationship to `imageExtend`

- [`imageExtend`](https://github.com/JustinShih0918/imageExtend) contains the model training, dataset preprocessing, image/video inference scripts, generator, discriminator, losses, and metrics.
- This repository wraps the trained model in a deployable full-stack application for real user workflows.

## Reproducibility Notes

With the pretrained checkpoint in place, the app can be run through Docker or local scripts. The generated videos are stored under `backend/results/`, while uploaded files are staged under `backend/uploads/`. Because model weights are large, they are downloaded separately from Google Drive instead of committed to Git.

## Good Next Improvements

- Add a short demo video or GIF to the README.
- Add `.env.example` files for frontend/backend configuration.
- Move hard-coded localhost URLs into environment variables.
- Add automated smoke tests for upload, status polling, and result listing.
- Add queue management for multiple concurrent video processing jobs.
