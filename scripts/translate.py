"""Translate public announcement snippets; cache by original text, never overwrite it."""
import concurrent.futures
import hashlib
import re
import time

import requests


def fingerprint(text):
    return hashlib.sha256(('zh-CN:v1:' + text).encode()).hexdigest()


def translate_text(text):
    if not text.strip():
        return '', 'original'
    # Already Chinese snippets need no external request. Keep model identifiers intact.
    if len(re.findall(r'[\u3400-\u9fff]', text)) > len(re.findall(r'[A-Za-z]', text)):
        return text, 'original'
    for attempt in range(2):
        try:
            response = requests.get('https://translate.googleapis.com/translate_a/single',
                params={'client': 'gtx', 'sl': 'auto', 'tl': 'zh-CN', 'dt': 't', 'q': text},
                timeout=(5, 15))
            response.raise_for_status()
            result = response.json()
            translated = ''.join(part[0] for part in result[0] if part and isinstance(part[0], str))
            if not translated.strip() or not re.search(r'[\u3400-\u9fff]', translated):
                raise ValueError('No Chinese translation returned')
            return translated, 'machine'
        except (requests.RequestException, ValueError, TypeError, IndexError, KeyError):
            if attempt == 0:
                time.sleep(1)
    return '', 'unavailable'


def localize(items, translator=translate_text):
    def one(item):
        cache = item.get('translations', {})
        updated = {}
        for field in ('title', 'summary'):
            original = item.get(field, '')
            key = fingerprint(original)
            old = cache.get(field, {})
            if old.get('key') == key and old.get('status') in ('original', 'machine'):
                entry = old
            else:
                text, status = translator(original)
                entry = {'key': key, 'text': text, 'status': status}
            updated[field] = entry
            item[field + '_zh'] = entry['text'] or original
        item['translations'] = updated
        item['translation_status'] = ('unavailable' if any(e['status'] == 'unavailable' for e in updated.values())
            else 'machine' if any(e['status'] == 'machine' for e in updated.values()) else 'original')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(one, items))
    return items
