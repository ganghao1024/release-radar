"""Read the maintained configuration; never regenerate obsolete international sources."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    rows = json.loads((ROOT/'config/sources.json').read_text(encoding='utf-8'))
    print(f'{len(rows)} configured entries. Edit config/sources.json to update.')
