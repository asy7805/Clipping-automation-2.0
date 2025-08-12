# Setup Instructions

## Prerequisites

### Install ffmpeg (Required for WhisperX and yt-dlp)

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use Chocolatey:
```bash
choco install ffmpeg
```

## Quick Setup

Run the automated setup script:
```bash
./setup.sh
```

## Manual Setup

### Core Environment (API + Orchestration)
```bash
# Create and activate core environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -U pip
pip install -r requirements.txt
```

### ML Environment (WhisperX + Audio Processing)
```bash
# Create and activate ML environment
python -m venv .venv-ml
source .venv-ml/bin/activate  # On Windows: .venv-ml\Scripts\activate

# Install dependencies
pip install -U pip

# For CUDA support (uncomment and modify for your CUDA version)
# pip install --extra-index-url https://download.pytorch.org/whl/cu121 -r requirements-ml.txt

# For CPU-only (default)
pip install -r requirements-ml.txt
```

## Environment Configuration

### Setup .env file
Copy the example environment file and configure your API keys:
```bash
cp .env.example .env
# Edit .env with your actual API keys
```

**Required for core environment:**
- `OPENAI_API_KEY` - For semantic embeddings and AI features
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - For database operations

**Optional for ML environment:**
- `HUGGING_FACE_HUB_TOKEN` - Only needed for gated pyannote models

## Environment Usage

### Core Environment
```bash
source .venv/bin/activate
# Run API orchestration scripts
python scripts/ingest.py
python scripts/process.py
```

### ML Environment
```bash
source .venv-ml/bin/activate
# Run ML/transcription scripts
python scripts/select_and_clip.py
```

## CUDA Versions

Common PyTorch CUDA versions:
- `cu118` - CUDA 11.8
- `cu121` - CUDA 12.1
- `cu124` - CUDA 12.4

Check your CUDA version:
```bash
nvidia-smi
```

## Architecture

- **Core Environment**: API orchestration, database operations, web scraping
- **ML Environment**: Audio transcription, WhisperX processing, audio analysis

This separation allows for:
- Cleaner dependency management
- Different deployment strategies
- Optimized resource allocation
- Easier debugging and maintenance
