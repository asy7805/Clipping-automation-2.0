#!/bin/bash

# Clipping Automation 2.0 - Environment Setup Script
# This script sets up two separate virtual environments:
# 1. Core environment for API orchestration
# 2. ML environment for WhisperX and audio processing

set -e  # Exit on any error

echo "🚀 Setting up Clipping Automation 2.0 environments..."

# Core Environment Setup
echo "📦 Setting up core environment (API + orchestration)..."
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
echo "✅ Core environment ready!"

# ML Environment Setup
echo "🤖 Setting up ML environment (WhisperX + audio processing)..."
python -m venv .venv-ml
source .venv-ml/bin/activate
pip install -U pip

# CUDA setup - uncomment and modify the line below for your CUDA version
# Common options: cu118, cu121, cu124
echo "🔧 Installing PyTorch with CUDA support..."
echo "   Please uncomment and modify the CUDA version in setup.sh if needed"
# pip install --extra-index-url https://download.pytorch.org/whl/cu121 -r requirements-ml.txt

# For CPU-only (default)
pip install -r requirements-ml.txt
echo "✅ ML environment ready!"

echo ""
echo "🎉 Setup complete! You now have two environments:"
echo "   Core: source .venv/bin/activate"
echo "   ML:   source .venv-ml/bin/activate"
echo ""
echo "📝 Usage:"
echo "   # For API orchestration:"
echo "   source .venv/bin/activate"
echo "   python scripts/your_api_script.py"
echo ""
echo "   # For ML/transcription:"
echo "   source .venv-ml/bin/activate"
echo "   python scripts/your_ml_script.py"
