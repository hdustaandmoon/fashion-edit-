"""Send a deployed daily snapshot to a Feishu custom bot."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def clip(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[:limit] + '…'


def build_message(snapshot: dict, site_url: str) -> dict:
    words = snapshot['words']
    added = [w for w in words if w.get('is_new')]
    hot = [w for w in words if w.get('is_hot')]
    baseline = snapshot.get('baseline_date')
    lines = [
        'Fashion Edit 每日趋势',
        f"采集日期：{snapshot['date']}（北京时间）",
        f"趋势词：{len(words)} 个｜新增：{len(added)} 个｜重点词：{len(hot)} 个",
        f'对比采集日期：{baseline}' if baseline else '首次采集：建立基线，不将全部词标为新增。',
    ]
    for title, items in (('新增趋势词', added), ('来源重点词', hot)):
        lines.extend(['', title])
        lines.extend('• ' + clip(w['term'], 100) for w in items[:15])
        if not items:
            lines.append('暂无')
        if len(items) > 15:
            lines.append(f'另有 {len(items) - 15} 个，请查看看板。')
    lines.extend(['', '商家选品建议'])
    suggestions = snapshot.get('suggestions', [])
    for suggestion in suggestions[:8]:
        lines.append('• ' + clip(suggestion['title'], 80) + '：' + clip(suggestion['text'], 180))
    if not suggestions:
        lines.append('本次来源未提供建议，请查看原页面。')
    if len(suggestions) > 8:
        lines.append('其余建议请查看看板。')
    site_url = site_url.rstrip('/') + '/'
    lines.extend(['', '查看完整看板：' + site_url,
                  '下载 Excel：' + site_url + 'data/trends.xlsx',
                  '', '重点标记来自来源；新增不代表搜索量增长。来源未变化时，词和建议保持不变。'])
    return {'msg_type': 'text', 'content': {'text': '\n'.join(lines)}}


def send(webhook: str, message: dict, secret: str = '') -> None:
    target = urlsplit(webhook)
    if target.scheme != 'https' or target.hostname != 'open.feishu.cn' or not target.path.startswith('/open-apis/bot/v2/hook/') or target.username or target.password or target.query or target.fragment:
        raise ValueError('Webhook 格式不正确，请填写飞书自定义机器人的 HTTPS Webhook。')
    payload = dict(message)
    if secret:
        timestamp = str(int(time.time()))
        signing_key = f'{timestamp}\n{secret}'.encode('utf-8')
        payload.update(timestamp=timestamp, sign=base64.b64encode(hmac.new(signing_key, b'', hashlib.sha256).digest()).decode('ascii'))
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    if len(data) > 19000:
        raise ValueError('飞书消息过长。')
    request = Request(webhook, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    # No automatic POST retries: a timeout may occur after the bot accepted the message.
    with urlopen(request, timeout=30) as response:
        result = json.loads(response.read(65536).decode('utf-8'))
    code = result.get('code', result.get('StatusCode'))
    if code != 0:
        raise RuntimeError('飞书未确认发送成功，请检查机器人状态、关键词或签名设置。')


def main() -> int:
    webhook = os.environ.get('FEISHU_WEBHOOK_URL', '').strip()
    if not webhook:
        print('未配置 FEISHU_WEBHOOK_URL，跳过飞书通知。')
        return 0
    try:
        site_url = os.environ['SITE_URL']
        if urlsplit(site_url).scheme != 'https':
            raise ValueError('缺少有效看板地址。')
        snapshot_path = Path(os.environ.get('SNAPSHOT_PATH', 'docs/data/latest.json'))
        snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
        send(webhook, build_message(snapshot, site_url), os.environ.get('FEISHU_SIGN_SECRET', '').strip())
    except Exception:
        # Never print exceptions containing a request URL, webhook token or response body.
        print('飞书通知失败；网页部署不受影响。请检查 Secret、机器人安全设置及网络，确认群内消息后再手动重试。')
        return 1
    print('飞书每日趋势通知发送成功。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
