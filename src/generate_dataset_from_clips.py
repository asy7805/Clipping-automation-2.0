#!/usr/bin/env python3
"""
Generate labeled_clips.csv from the current folder structure:
- data/edited_clips/good_only/ → label 1
- data/raw_clips/good/         → label 1
- data/raw_clips/bad/          → label 0
"""
import csv
from pathlib import Path

def main():
    base = Path('data')
    edited_good = base / 'edited_clips' / 'good_only'
    raw_good = base / 'raw_clips' / 'good'
    raw_bad = base / 'raw_clips' / 'bad'
    csv_path = base / 'labeled_clips.csv'

    rows = []
    # Helper to add rows from a folder
    def add_rows_from_folder(folder, label, source):
        if not folder.exists():
            return
        for f in folder.glob('*.mp4'):
            rows.append({
                'clip_id': f.stem,
                'text': '',  # Placeholder for transcript or description
                'label': label,
                'source': source
            })

    add_rows_from_folder(edited_good, 1, 'edited_good_only')
    add_rows_from_folder(raw_good, 1, 'raw_good')
    add_rows_from_folder(raw_bad, 0, 'raw_bad')

    # Write to CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['clip_id', 'text', 'label', 'source'])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f'✅ Generated {csv_path} with {len(rows)} rows.')

if __name__ == '__main__':
    main() 