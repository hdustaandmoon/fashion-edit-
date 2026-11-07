import json
from unittest import TestCase
from unittest.mock import patch, MagicMock

from notify_feishu import build_message, send, main


class FeishuTests(TestCase):
    def snapshot(self):
        return {'date': '2026-11-07', 'baseline_date': '2026-11-06',
                'words': [{'term': 'coat', 'is_new': True, 'is_hot': True}],
                'suggestions': [{'title': '冬季服饰', 'text': '关注保暖需求'}]}

    def test_message_contains_summary_and_excel(self):
        message = build_message(self.snapshot(), 'https://example.com/shop/')
        text = message['content']['text']
        self.assertEqual(message['msg_type'], 'text')
        for part in ['新增：1', '重点词：1', 'coat', '关注保暖需求', 'https://example.com/shop/data/trends.xlsx']:
            self.assertIn(part, text)

    def test_no_new_words_and_legacy_snapshot(self):
        snapshot = self.snapshot()
        snapshot['baseline_date'] = None
        snapshot['words'] = [{'term': 'coat'}]
        del snapshot['suggestions']
        self.assertIn('首次采集', build_message(snapshot, 'https://example.com')['content']['text'])

    def test_signed_send_checks_api_result(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"code":0}'
        with patch('notify_feishu.urlopen', return_value=response) as request, patch('notify_feishu.time.time', return_value=123):
            send('https://open.feishu.cn/open-apis/bot/v2/hook/test', build_message(self.snapshot(), 'https://example.com'), 'secret')
            payload = json.loads(request.call_args.args[0].data)
            self.assertEqual(payload['timestamp'], '123')
            self.assertTrue(payload['sign'])
        response.__enter__.return_value.read.return_value = b'{"code":19024}'
        with patch('notify_feishu.urlopen', return_value=response):
            with self.assertRaises(RuntimeError):
                send('https://open.feishu.cn/open-apis/bot/v2/hook/test', {})

    def test_invalid_destination_never_requested(self):
        with patch('notify_feishu.urlopen') as request:
            with self.assertRaises(ValueError):
                send('https://example.com/hook', {})
            request.assert_not_called()

    def test_unconfigured_secret_skips(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(main(), 0)
