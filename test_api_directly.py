#!/usr/bin/env python3
"""Direct test of the clips endpoint"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import the endpoint directly
from api.routers.clips import get_clips

# Call it
import asyncio

async def test():
    result = await get_clips(limit=1, offset=0, channel_name=None, is_clip_worthy=None)
    print(f"Result type: {type(result)}")
    print(f"Result length: {len(result)}")
    if result:
        clip_dict = result[0] if isinstance(result[0], dict) else result[0].dict()
        print(f"\nFirst clip:")
        print(f"  ID: {clip_dict.get('id', 'N/A')[:50]}")
        print(f"  confidence_score: {clip_dict.get('confidence_score')}")
        print(f"  score_breakdown: {clip_dict.get('score_breakdown')}")

asyncio.run(test())

