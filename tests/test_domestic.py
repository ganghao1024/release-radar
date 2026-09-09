import unittest
from scripts.core import domestic_phone_url, filter_domestic_phones


class DomesticPhoneTests(unittest.TestCase):
    source = {'id': 'honor', 'enabled': True, 'region': 'CN', 'categories': ['phone'],
              'article_prefixes': ['https://www.honor.com/cn/news/']}

    def test_region_and_hostname_boundary(self):
        self.assertTrue(domestic_phone_url('https://www.honor.com/cn/news/new-phone/', self.source))
        for url in ['https://www.honor.com/global/news/new-phone/',
                    'https://www.honor.com.evil.test/cn/news/new-phone/',
                    'https://www.honor.com/cn/news-other/new-phone/']:
            self.assertFalse(domestic_phone_url(url, self.source))

    def test_old_international_cache_removed_after_source_switch(self):
        items = [
            {'category': 'phone', 'source_ids': ['honor'], 'url': 'https://www.honor.com/global/news/old/'},
            {'category': 'phone', 'source_ids': ['honor'], 'url': 'https://www.honor.com/cn/news/new/'},
            {'category': 'phone', 'source_ids': ['pixel'], 'url': 'https://blog.google/pixel/'},
            {'category': 'ai', 'source_ids': ['google'], 'url': 'https://blog.google/model/'},
        ]
        self.assertEqual(filter_domestic_phones(items, [self.source]), [items[1], items[3]])

    def test_query_article_and_disabled_source(self):
        source = {**self.source, 'article_prefixes': ['https://www.vivo.com.cn/brand/news/detail']}
        self.assertTrue(domestic_phone_url('https://www.vivo.com.cn/brand/news/detail?id=1385&type=0', source))
        self.assertFalse(domestic_phone_url('https://www.vivo.com.cn/brand/news/detail?id=1385', {**source, 'enabled': False}))


if __name__ == '__main__':
    unittest.main()
