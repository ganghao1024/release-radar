import json
import unittest
from pathlib import Path


class SourceConfigurationTests(unittest.TestCase):
    def test_bfl_current_blog_adapter(self):
        sources=json.loads((Path(__file__).parents[1]/'config/sources.json').read_text(encoding='utf-8'))
        source=next(item for item in sources if item['id']=='bfl')
        self.assertEqual(source['url'],'https://bfl.ai/blog')
        self.assertEqual(source['pattern'],r'/blog/[^/?#]+/?$')


if __name__=='__main__':unittest.main()
