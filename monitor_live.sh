#!/bin/bash
# Live Ingestion Monitor
# Shows real-time status of the clipping system

echo "🎬 AscensionClips - Live Monitor"
echo "=========================================="
echo ""

while true; do
    clear
    echo "🎬 AscensionClips - Live Monitor"
    echo "=========================================="
    echo ""
    echo "📊 Process Status:"
    ps aux | grep -E "(live_ingest|streamlink|ffmpeg)" | grep -v grep | awk '{print "  " $0}' | head -5
    echo ""
    echo "📁 Temp Directories:"
    ls -ltd /tmp/live_* 2>/dev/null | head -3 | awk '{print "  " $0}'
    echo ""
    echo "📦 Segment Files:"
    find /tmp -name "live_*" -type d -exec sh -c 'echo "  $1: $(ls -1 "$1"/*.mp4 2>/dev/null | wc -l) segments"' _ {} \; 2>/dev/null | head -3
    echo ""
    echo "☁️  Supabase Uploads (recent):"
    echo "  (Check your Supabase dashboard: Storage > raw bucket)"
    echo ""
    echo "⏱️  Updated: $(date)"
    echo ""
    echo "Press Ctrl+C to stop monitoring"
    sleep 3
done

