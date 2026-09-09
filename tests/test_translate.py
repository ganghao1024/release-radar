import unittest

from scripts.translate import localize


class TranslationTests(unittest.TestCase):
    def test_cache_originals_and_invalidation(self):
        calls = []
        def translator(text):
            calls.append(text)
            return '中文：' + text, 'machine'
        item = {'title': 'New model', 'summary': 'Available today'}
        localize([item], translator)
        self.assertEqual(item['title'], 'New model')
        self.assertEqual(item['title_zh'], '中文：New model')
        localize([item], translator)
        self.assertEqual(len(calls), 2)
        item['title'] = 'Updated model'
        localize([item], translator)
        self.assertEqual(calls, ['New model', 'Available today', 'Updated model'])
        self.assertEqual(item['title_zh'], '中文：Updated model')

    def test_failure_removes_stale_translation_and_retries(self):
        item = {'title': 'Old', 'summary': ''}
        localize([item], lambda text: ('旧译文', 'machine'))
        item['title'] = 'Changed'
        localize([item], lambda text: ('', 'unavailable'))
        self.assertEqual(item['title_zh'], 'Changed')
        self.assertEqual(item['translation_status'], 'unavailable')
        localize([item], lambda text: ('新译文', 'machine'))
        self.assertEqual(item['title_zh'], '新译文')


if __name__ == '__main__':
    unittest.main()
