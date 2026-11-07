from datetime import datetime
import unittest
from tracker import CN, build_snapshot, parse, render


class TrackerTests(unittest.TestCase):
    def test_nested_labels_and_duplicates(self):
        html = '<section id="trending"><div class="trend-group-title"><span>🔥</span> 风格</div><div class="trend-subgroup-label">穿搭</div><span class="trend-tag hot">A &amp; B</span><span class="trend-tag">a &amp; b</span></section><span class="trend-tag">ignore</span>'
        words = parse(html)
        self.assertEqual(len(words), 1)
        self.assertEqual(words[0]['term'], 'A & B')
        self.assertEqual(words[0]['categories'][0]['group'], '🔥 风格')

    def test_baseline_repeat_and_removal(self):
        words = [{'term': 'old', 'categories': [{'group': 'group', 'subgroup': 'sub'}]}]
        first = build_snapshot(words, {}, datetime(2026, 11, 6, tzinfo=CN))
        self.assertFalse(first['words'][0]['is_new'])
        history = {'2026-11-06': first}
        added = [{'term': '<new>', 'categories': words[0]['categories']}]
        next_day = build_snapshot(added, history, datetime(2026, 11, 7, tzinfo=CN))
        self.assertTrue(next_day['words'][0]['is_new'])
        self.assertEqual(next_day['removed'], ['old'])
        history['2026-11-07'] = next_day
        rerun = build_snapshot(added, history, datetime(2026, 11, 7, 15, tzinfo=CN))
        self.assertTrue(rerun['words'][0]['is_new'])
        self.assertIn('&lt;new&gt;', render(rerun))
        self.assertNotIn('<new>', render(rerun))

    def test_empty_source_rejected(self):
        with self.assertRaises(ValueError):
            parse('<html>not trends</html>')


if __name__ == '__main__':
    unittest.main()
