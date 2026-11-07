from datetime import datetime
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from openpyxl import load_workbook
from tracker import CN, build_snapshot, export_excel, parse, parse_content, render


class TrackerTests(unittest.TestCase):
    def test_nested_labels_and_duplicates(self):
        html = '<section id="trending"><div class="trend-group-title"><span>🔥</span> 风格</div><div class="trend-subgroup-label">穿搭</div><span class="trend-tag hot">A &amp; B</span><span class="trend-tag">a &amp; b</span></section><span class="trend-tag">ignore</span>'
        words = parse(html)
        self.assertEqual(len(words), 1)
        self.assertEqual(words[0]['term'], 'A & B')
        self.assertEqual(words[0]['categories'][0]['group'], '🔥 风格')
        self.assertTrue(words[0]['is_hot'])

    def test_advice_and_excel(self):
        html = '<section id="trending"><div class="trend-group-title">分类</div><span class="trend-tag hot">=1+1</span><div class="trend-suggestion-card"><span>💡</span><b>选品 &amp; 上新</b><p>关注<b>冬季</b>商品</p></div></section>'
        words, suggestions = parse_content(html)
        self.assertEqual(suggestions, [{'title': '选品 & 上新', 'text': '关注冬季商品'}])
        snapshot = build_snapshot(words, {}, datetime(2026, 11, 7, tzinfo=CN))
        snapshot['words'][0]['is_new'] = True
        snapshot['suggestions'] = suggestions
        page = render(snapshot)
        self.assertIn('term hot new', page)
        self.assertIn('选品 &amp; 上新', page)
        self.assertIn('section:not(.advice)', page)
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'test.xlsx'
            export_excel(snapshot, path)
            workbook = load_workbook(path)
            self.assertEqual(workbook.sheetnames, ['趋势词', '选品建议'])
            self.assertEqual(workbook['趋势词']['A2'].value, '=1+1')
            self.assertEqual(workbook['趋势词']['A2'].data_type, 's')
            self.assertEqual(workbook['趋势词']['D2'].value, '是')
            self.assertEqual(workbook['趋势词']['E2'].value, '是')
            self.assertEqual(workbook['趋势词']['A2'].fill.fgColor.rgb, '00FFF0B3')
            self.assertEqual(workbook['趋势词']['A2'].font.color.rgb, '00B42832')
            self.assertEqual(workbook['选品建议']['B2'].value, '关注冬季商品')
            workbook.close()

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
