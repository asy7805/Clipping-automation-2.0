# Windows Compatibility Guide

## ✅ Windows Support Added

The AscensionClips system is now compatible with Windows!

### Changes Made:

1. **Temp Directory Handling**
   - Uses Windows `TEMP` or `TMP` environment variables
   - Falls back to `C:\temp` if needed
   - Works on Windows, macOS, and Linux

2. **Hardware Acceleration**
   - Windows: Detects NVIDIA GPU (CUDA) or uses DXVA2
   - macOS: Uses VideoToolbox
   - Linux: Detects NVIDIA (CUDA) or Intel QuickSync (QSV)

3. **Path Handling**
   - All `Path` operations use `pathlib` (cross-platform)
   - Log directories created with `mkdir(exist_ok=True)`
   - File operations work on all platforms

### Running on Windows:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (Windows CMD)
set SUPABASE_URL=your_url
set SUPABASE_SERVICE_ROLE_KEY=your_key

# Run the API
python scripts\start_api.py

# Start a monitor
python scripts\live_ingest.py --channel streamername --quality best --encoder auto
```

### Windows-Specific Notes:

- **FFmpeg**: Must be installed and in PATH
- **Streamlink**: Must be installed (`pip install streamlink`)
- **Temp Files**: Stored in `%TEMP%\live_<channel>_<random>/`
- **Logs**: Stored in `logs/` directory (same as other platforms)

### Hardware Acceleration on Windows:

- **NVIDIA GPU**: Automatically detected, uses CUDA
- **Intel GPU**: Uses DXVA2 hardware acceleration
- **CPU Only**: Falls back to libx264 software encoding

