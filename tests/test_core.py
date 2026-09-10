import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if (ROOT/'.cache/python').exists():sys.path.insert(0,str(ROOT/'.cache/python'))
sys.path.insert(0,str(ROOT))
import unittest
from datetime import datetime,timezone
from scripts.core import parse_feed,parse_date,canonical_url,classify,normalize,merge_items,has_term
from scripts.collect import article_data

class FeedTests(unittest.TestCase):
    def test_rss_date_and_safe_url(self):
        rows=parse_feed(b'<rss><channel><item><title>Introducing iPhone</title><link>https://a.com/new?utm_source=rss</link><pubDate>Tue, 08 Sep 2026 02:00:00 GMT</pubDate><description>&lt;b&gt;Available&lt;/b&gt;</description></item><item><title>Unsafe</title><link>javascript:alert(1)</link></item></channel></rss>','https://a.com')
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['url'],'https://a.com/new');self.assertEqual(rows[0]['summary'],'Available');self.assertEqual(rows[0]['published_at'],'2026-09-08T02:00:00+00:00')
    def test_atom_updated_is_not_publication(self):
        rows=parse_feed(b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Model</title><link href="https://a.com/model"/><updated>2026-09-08T00:00:00Z</updated><summary>News</summary></entry></feed>','https://a.com')
        self.assertIsNone(rows[0]['published_at']);self.assertIsNotNone(rows[0]['updated_at'])
    def test_html_is_not_successful_feed(self):
        with self.assertRaises(ValueError):parse_feed(b'<html><body>Blocked</body></html>','https://a.com')
    def test_reject_dtd(self):
        with self.assertRaises(ValueError):parse_feed(b'<!DOCTYPE rss [<!ENTITY x "a">]><rss/>','https://a.com')
    def test_html_jsonld_date_and_heading(self):
        row=article_data(b'<html><meta property="og:description" content="New model"><script type="application/ld+json">{"@graph":[{"@type":"NewsArticle","datePublished":"2026-09-01"}]}</script><h1>Introducing Claude</h1></html>','https://a.com/new')
        self.assertEqual(row['title'],'Introducing Claude');self.assertTrue(row['published_at'].startswith('2026-09-01'));self.assertEqual(row['summary'],'New model')

class ClassificationTests(unittest.TestCase):
    ai={'categories':['ai'],'terms':[]}
    phone={'categories':['phone'],'terms':['iPhone']}
    def row(self,title,summary=''):return {'title':title,'summary':summary}
    def test_real_release(self):self.assertEqual(classify(self.row('Introducing GPT-5'),self.ai),('ai','release'))
    def test_preview_before_release(self):self.assertEqual(classify(self.row('Introducing a preview of Claude'),self.ai),('ai','preview'))
    def test_availability(self):self.assertEqual(classify(self.row('iPhone 17 now available'),self.phone),('phone','available'))
    def test_model_number_alone_is_only_signal(self):self.assertEqual(classify(self.row('DeepSeek-V3.2'),self.ai),('ai','signal'))
    def test_funding_and_system_cards_excluded(self):
        self.assertIsNone(classify(self.row('Announcing new funding for model research'),self.ai))
        self.assertIsNone(classify(self.row('GPT-5 System Card'),self.ai))
    def test_gpu_not_model(self):self.assertIsNone(classify(self.row('Introducing a new NVIDIA GPU'),{'categories':['ai'],'terms':['Nemotron','Cosmos']}))
    def test_customer_story_not_model_release(self):
        self.assertIsNone(classify(self.row('Legora reviewed documents with GPT-6','Introducing GPT-6 into a workflow'),self.ai))
        self.assertIsNone(classify(self.row('Supporting independent journalism','OpenAI launches an AI program'),self.ai))
        self.assertIsNone(classify(self.row('Introducing the Admin plugin for ChatGPT'),self.ai))
    def test_accessory_not_phone(self):self.assertIsNone(classify(self.row('Introducing a new charger'),self.phone))
    def test_accessory_with_phone_name_is_excluded(self):
        self.assertIsNone(classify(self.row('New accessories for Pixel 11 phones are here.'),{'categories':['phone'],'terms':['Pixel']}))
        self.assertIsNone(classify(self.row('Introducing new cases for iPhone 17'),self.phone))
    def test_corporate_phone_appearance_is_not_a_product_release(self):
        source={'categories':['phone'],'terms':['vivo','手机']}
        generic='vivo-智能手机官网'
        self.assertIsNone(classify(self.row('vivo亮相ITU峰会 端侧智能体安全方案获全球认可',generic),source))
        self.assertEqual(classify(self.row('打造AI轻办公神器 vivo X Fold6折叠旗舰正式发布',generic),source),('phone','release'))
    def test_model_release_research_is_not_a_product_release(self):
        self.assertIsNone(classify(self.row('Predicting model behavior before release by simulating deployment'),self.ai))
        self.assertIsNone(classify(self.row('GPT-5.5 Bio Bug Bounty'),self.ai))
        self.assertEqual(classify(self.row('Introducing GPT-5.5'),self.ai),('ai','release'))
    def test_alias_word_boundaries(self):
        self.assertTrue(has_term('Qwen3 release','Qwen'));self.assertFalse(has_term('stepping up','Step'));self.assertFalse(has_term('innovation','Nova'))
    def test_google_split(self):
        source={'categories':['phone','ai'],'terms':['Pixel','Gemini']}
        self.assertEqual(classify(self.row('Introducing Pixel 11'),source)[0],'phone')
        self.assertEqual(classify(self.row('Introducing Gemini 3.5'),source)[0],'ai')

class StateTests(unittest.TestCase):
    now=datetime(2026,9,8,tzinfo=timezone.utc)
    def item(self,url='https://a.com/model',date='2026-09-01T00:00:00+00:00',source='a',seen='2026-09-02T00:00:00+00:00'):
        return dict(url=url,title='Model',source_ids=[source],published_at=date,first_seen_at=seen)
    def test_same_url_merges_and_keeps_first_seen(self):
        rows=merge_items([self.item()],[self.item(url='https://a.com/model?utm_source=feed',source='b',seen='2026-09-08T00:00:00+00:00')],self.now)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['source_ids'],['a','b']);self.assertTrue(rows[0]['first_seen_at'].startswith('2026-09-02'))
    def test_regional_urls_are_distinct(self):self.assertEqual(len(merge_items([self.item()],[self.item('https://a.com/cn/model')],self.now)),2)
    def test_failure_does_not_drop_previous_news(self):self.assertEqual(len(merge_items([self.item()],[],self.now)),1)
    def test_exact_headline_syndication_preserves_links(self):
        a={**self.item(),'vendor':'Google','category':'ai','region':'global','event_type':'release'}
        b={**a,'url':'https://b.com/model','source_ids':['b']}
        rows=merge_items([a],[b],self.now)
        self.assertEqual(len(rows),1);self.assertEqual(len(rows[0]['related_urls']),2)
        b['region']='China'
        self.assertEqual(len(merge_items([a],[b],self.now)),2)
    def test_unknown_date_remains_unknown(self):self.assertIsNone(merge_items([],[self.item(date=None)],self.now)[0]['published_at'])
    def test_old_and_future_dates_excluded(self):
        self.assertEqual(merge_items([],[self.item(date='2020-01-01T00:00:00+00:00'),self.item(url='https://a.com/future',date='2027-01-01T00:00:00+00:00')],self.now),[])
    def test_dates(self):
        for value in ['2026年9月8日','September 8, 2026','Sep 8, 2026','2026-09-08']:
            self.assertTrue(parse_date(value).startswith('2026-09-08'))
        self.assertIsNone(parse_date('not a date'))

if __name__=='__main__':unittest.main()
