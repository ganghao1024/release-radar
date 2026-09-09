"""Read the maintained configuration; never regenerate obsolete international sources."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    rows = json.loads((ROOT/'config/catalog.json').read_text(encoding='utf-8'))
    print(f'{len(rows)} configured entries. Edit config/catalog.json to update.')
