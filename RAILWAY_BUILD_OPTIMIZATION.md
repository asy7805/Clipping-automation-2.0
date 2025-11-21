# Railway Build Optimization Guide

## Current Build Status

✅ **Build completes successfully** - All dependencies install correctly
⚠️ **Upload timeout** - Docker image upload times out due to large image size (~2-3GB)

## Why Builds Take Long

Railway builds are taking 16+ minutes because:

1. **Large ML Dependencies** (required for monitor workers):
   - PyTorch CPU-only: ~500MB
   - transformers: ~500MB+ (downloads models)
   - faster-whisper: ~200MB+ (downloads Whisper models)
   - librosa, scikit-learn, numpy: ~300MB+
   - Total ML dependencies: ~1.5-2GB

2. **Poetry Install Time**: 3-4 minutes (normal for this many dependencies)

3. **Docker Image Upload**: Times out because image is 2-3GB

## Solutions

### Option 1: Accept Long Build Times (Recommended)
- Railway builds will take 15-20 minutes
- This is normal for ML-heavy applications
- Builds complete successfully, just takes time

### Option 2: Upgrade Railway Plan
- Higher-tier plans may have longer timeout limits
- Check Railway dashboard for plan options

### Option 3: Optimize Further (Future)
- Consider lazy-loading ML models
- Use model caching/sharing between containers
- Split API and worker services (API without ML deps)

## Current Optimizations Applied

✅ CPU-only PyTorch (saves ~700MB vs GPU version)
✅ Poetry cache clearing after install
✅ `.dockerignore` excludes frontend, venv, logs, tests
✅ Cleanup of temporary files (`get-pip.py`)
✅ Excludes unnecessary files from build context

## Build Configuration

- **Builder**: Nixpacks
- **Python**: 3.12
- **Dependency Manager**: Poetry
- **Install Command**: `poetry install --only main --no-root`
- **Start Command**: `cd src/api && poetry run uvicorn main:app --host 0.0.0.0 --port $PORT`

## Monitoring Build Progress

Railway build logs show:
1. ✅ Setup phase (pip, poetry install) - completes
2. ✅ Install phase (dependencies) - completes (~3-4 min)
3. ✅ Build phase - completes
4. ⏱️ Importing to Docker - times out (image too large)

The build itself is successful - the timeout is during image upload.

