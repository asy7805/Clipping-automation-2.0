#!/bin/bash
# Real-time monitoring dashboard for asspizza730 stream
TEMP_DIR="/var/folders/ds/267px0t926s0tg69t7sgz7x00000gn/T/live_asspizza730_yokx8nfr"

while true; do
    clear
    echo "🎬 LIVE STREAM MONITORING: asspizza730"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📺 Stream: Day 18 Non-Stop Stream"
    echo "👥 Viewers: 610+"
    echo "🎮 Category: Just Chatting"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Process status
    echo "🔄 SYSTEM STATUS:"
    if ps aux | grep -q "[l]ive_ingest.py --channel asspizza730"; then
        echo "   ✅ AI Analyzer: RUNNING"
    else
        echo "   ❌ AI Analyzer: STOPPED"
    fi
    
    if ps aux | grep -q "[s]treamlink.*asspizza730"; then
        echo "   ✅ Stream Capture: ACTIVE"
    else
        echo "   ❌ Stream Capture: INACTIVE"
    fi
    
    if ps aux | grep -q "[f]fmpeg.*asspizza730"; then
        echo "   ✅ Video Processing: ENCODING"
    else
        echo "   ⏸️  Video Processing: IDLE"
    fi
    echo ""
    
    # Segments
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 SEGMENTS CAPTURED:"
    if [ -d "$TEMP_DIR" ]; then
        SEGMENT_COUNT=$(ls -1 "$TEMP_DIR"/seg_*.mp4 2>/dev/null | wc -l | tr -d ' ')
        echo "   Total: $SEGMENT_COUNT segments"
        echo ""
        ls -lht "$TEMP_DIR"/seg_*.mp4 2>/dev/null | head -5 | awk '{print "   " $9 " (" $5 ")"}'
    else
        echo "   Waiting for segments..."
    fi
    echo ""
    
    # Uploads
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "☁️  CLIPS UPLOADED TO SUPABASE:"
    cd /Users/aidanyap/Clipping-automation-2.0
    source whisperx-macos/bin/activate 2>/dev/null
    python3 -c "
import os, sys
from dotenv import load_dotenv
from supabase import create_client
load_dotenv()
os.environ['USE_SERVICE_ROLE'] = 'true'
try:
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    files = sb.storage.from_('raw').list('raw/asspizza730/')
    if files:
        print(f'   ✅ {len(files)} clips uploaded!')
        for f in files[:3]:
            size = f.get('metadata', {}).get('size', 0) / 1024 / 1024
            print(f'      • {f[\"name\"]} ({size:.1f} MB)')
    else:
        print('   ⏳ Waiting for first interesting clip...')
except:
    print('   ⏳ Waiting for first interesting clip...')
" 2>/dev/null || echo "   ⏳ Waiting for first interesting clip..."
    echo ""
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⏱️  Updated: $(date '+%H:%M:%S')"
    echo "🛑 Press Ctrl+C to stop monitoring"
    echo ""
    
    sleep 5
done

