"""Fashion Edit daily keyword tracker; Python 3.11+, no dependencies."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import time
import unicodedata
from urllib.request import Request, urlopen

SOURCE = 'https://fashion-edit-merchant.netlify.app/'
ROOT = Path(__file__).resolve().parent
CN = timezone(timedelta(hours=8))


def key(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', text).split()).casefold()


class TrendParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.capture: tuple[str, int] | None = None
        self.parts: list[str] = []
        self.section = False
        self.group = ''
        self.subgroup = ''
        self.words: dict[str, dict] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == 'section' and attr.get('id') == 'trending':
            self.section = True
        if not self.section:
            return
        if tag not in {'br', 'img', 'hr', 'input', 'meta', 'link', 'wbr'}:
            self.stack.append(tag)
        classes = (attr.get('class') or '').split()
        kind = next((c for c in ('trend-group-title', 'trend-subgroup-label', 'trend-tag') if c in classes), None)
        if kind:
            self.capture = (kind, len(self.stack))
            self.parts = []

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.section:
            return
        if self.capture and len(self.stack) == self.capture[1]:
            kind = self.capture[0]
            text = ' '.join(''.join(self.parts).split())
            if kind == 'trend-group-title':
                self.group, self.subgroup = text, ''
            elif kind == 'trend-subgroup-label':
                self.subgroup = text
            elif text:
                item = self.words.setdefault(key(text), {'term': text, 'categories': []})
                category = {'group': self.group, 'subgroup': self.subgroup}
                if category not in item['categories']:
                    item['categories'].append(category)
            self.capture = None
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        if tag == 'section':
            self.section = False


def parse(source: str) -> list[dict]:
    parser = TrendParser()
    parser.feed(source)
    words = list(parser.words.values())
    if not words or any(not w['categories'][0]['group'] for w in words):
        raise ValueError('未找到有效趋势词，来源结构可能已改变；保留上次数据。')
    return words


def fetch() -> str:
    for attempt in range(3):
        try:
            request = Request(SOURCE, headers={'User-Agent': 'FashionEditTrendTracker/1.0 (daily public keyword monitor)'})
            with urlopen(request, timeout=45) as response:
                return response.read(10_000_001).decode('utf-8')
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError('下载失败')


def build_snapshot(words: list[dict], history: dict[str, dict], now: datetime) -> dict:
    day = now.astimezone(CN).date().isoformat()
    earlier = sorted(d for d in history if d < day)
    baseline = history[earlier[-1]] if earlier else None
    old = {key(w['term']) for w in baseline['words']} if baseline else set()
    current = {key(w['term']) for w in words}
    first_seen: dict[str, str] = {}
    for date in sorted(history):
        for word in history[date]['words']:
            first_seen.setdefault(key(word['term']), word.get('first_seen', date))
    return {
        'date': day, 'checked_at': now.astimezone(CN).isoformat(),
        'source': SOURCE + '#trending', 'baseline_date': baseline['date'] if baseline else None,
        'removed': [w['term'] for w in baseline['words'] if key(w['term']) not in current] if baseline else [],
        'words': [dict(w, is_new=baseline is not None and key(w['term']) not in old,
                       first_seen=first_seen.get(key(w['term']), day)) for w in words],
    }


def render(snapshot: dict) -> str:
    groups: dict[str, list[str]] = {}
    for word in snapshot['words']:
        for category in word['categories']:
            group = category['group']
            badge = '<b>NEW</b>' if word['is_new'] else ''
            cls = ' new' if word['is_new'] else ''
            groups.setdefault(group, []).append(
                f'<article class="term{cls}"><div><span>{escape(word["term"])}</span>{badge}</div>'
                f'<small>{escape(category["subgroup"])} · 首次收录 {word["first_seen"]}</small></article>')
    sections = ''.join(f'<section><h2>{escape(g)}</h2><div class="terms">{"".join(items)}</div></section>' for g, items in groups.items())
    count = sum(w['is_new'] for w in snapshot['words'])
    comparison = f'对比 {snapshot["baseline_date"]}' if snapshot['baseline_date'] else '首次采集 · 已建立基线'
    removed = '、'.join(snapshot['removed']) or '暂无'
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fashion Edit · 趋势词观察</title><link rel="stylesheet" href="style.css">
<header><a href="./">FASHION <i>EDIT</i><small>TREND OBSERVATORY / MÉXICO</small></a><a href="{SOURCE}#trending" target="_blank" rel="noopener">查看数据来源 ↗</a></header>
<main><div class="eyebrow">DAILY KEYWORD INTELLIGENCE</div><h1>捕捉趋势，<br><em>从一个新词开始。</em></h1>
<p class="intro">每日追踪 Fashion Edit 站内趋势关键词。红色 NEW 表示相较上一采集日期新增或重新出现的词。</p>
<div class="stats"><div><strong>{len(snapshot['words'])}</strong><span>当前趋势词</span></div><div><strong class="red">{count:02d}</strong><span>本次新增 · {comparison}</span></div><div><strong class="date">{snapshot['date']}</strong><span>最近成功采集（北京时间）</span></div></div>
<div class="controls"><label>搜索趋势词 <input id="search" type="search" placeholder="输入关键词或分类…"></label><label><input id="only-new" type="checkbox"> 只看新增</label><a href="data/latest.json" download>下载 JSON ↓</a></div>
<p id="empty" hidden>没有符合条件的趋势词。</p>{sections}
<details><summary>本次移出的词（{len(snapshot['removed'])}）</summary><p>{escape(removed)}</p></details>
<footer>计划每天北京时间 09:15 更新，实际运行可能因 GitHub 调度延迟。<br>数据为来源站整理的关键词，不代表实时搜索量或排名；来源未更新时不会生成新词。<br>最近成功检查：{snapshot['checked_at']} · <a href="data/history.json">历史快照</a></footer></main>
<script>
const search=document.querySelector('#search'),only=document.querySelector('#only-new');
function filter(){{let total=0;document.querySelectorAll('section').forEach(section=>{{let visible=0;section.querySelectorAll('.term').forEach(term=>{{term.hidden=!(term.textContent.toLocaleLowerCase().includes(search.value.toLocaleLowerCase())&&(!only.checked||term.classList.contains('new')));if(!term.hidden)visible++;}});section.hidden=!visible;total+=visible;}});document.querySelector('#empty').hidden=total>0;}}
search.addEventListener('input',filter);only.addEventListener('change',filter);
</script></html>'''


def write_json(path: Path, data: dict) -> None:
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def run(source_file: Path | None = None, output: Path = ROOT / 'docs') -> dict:
    data_dir = output / 'data'
    history_path = data_dir / 'history.json'
    history = json.loads(history_path.read_text(encoding='utf-8')) if history_path.exists() else {}
    words = parse(source_file.read_text(encoding='utf-8') if source_file else fetch())
    now = datetime.now(CN)
    snapshot = build_snapshot(words, history, now)
    page = render(snapshot)
    history[snapshot['date']] = snapshot
    data_dir.mkdir(parents=True, exist_ok=True)
    write_json(history_path, history)
    write_json(data_dir / 'latest.json', snapshot)
    (output / 'index.html').write_text(page, encoding='utf-8')
    (output / '.nojekyll').touch()
    return snapshot


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--source-file', type=Path, help='从已下载 HTML 验证采集，不访问网络')
    args = cli.parse_args()
    result = run(args.source_file)
    print(f"采集成功：{len(result['words'])} 个词，新增 {sum(w['is_new'] for w in result['words'])} 个。")
