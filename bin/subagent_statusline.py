#!/usr/bin/python3
"""Claude Code subagentStatusLine
エージェントパネルの各行に、サブエージェントのモデルとeffortを表示する。
行の形式: 名前  モデル effort  作業内容  トークン数
settings.json の subagentStatusLine.command から呼び出す。
"""
import json, re, sys, unicodedata

R = '\033[0m'
DIM = '\033[2m'
BOLD = '\033[1m'


def model_name(model_id):
    """claude-sonnet-5-5 → Sonnet 5.5（解釈できなければIDのまま）"""
    m = re.match(r'claude-([a-z]+)-(\d+)(?:-(\d{1,2}))?(?=$|-\d{8}|\[)', model_id)
    if not m:
        return model_id
    family, major, minor = m.groups()
    version = f'{major}.{minor}' if minor else major
    return f'{family.title()} {version}'


def effort_mark(effort):
    """xhigh→X, medium→M。数値（トークン予算）はそのまま"""
    if effort is None:
        return ''
    if isinstance(effort, str):
        return effort[:1].upper()
    return str(effort)


def tokens(n):
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f'{n / 1000:.1f}k'
    return f'{n / 1_000_000:.1f}M'


def width(s):
    return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in s)


def truncate(s, limit):
    if width(s) <= limit:
        return s
    out = ''
    for c in s:
        if width(out + c) > limit - 1:
            break
        out += c
    return out + '…'


def row(task, columns):
    name = task.get('name') or task.get('agentType') or task.get('type', '')
    model = task.get('model')
    mark = effort_mark(task.get('effort'))
    model_text = ' '.join(p for p in (model_name(model) if model else '', mark) if p)
    count = tokens(task.get('tokenCount', 0))
    label = task.get('label') or task.get('description', '')

    # 作業内容だけを詰めて、名前・モデル・トークン数は必ず残す
    fixed = width(name) + 2 + (width(model_text) + 2 if model_text else 0) + 2 + width(count)
    label = truncate(label, max(columns - fixed, 0)) if columns else label

    parts = [name]
    if model_text:
        parts.append(f'{BOLD}{model_text}{R}')
    if label:
        parts.append(label)
    parts.append(f'{DIM}{count}{R}')
    return '  '.join(parts)


try:
    data = json.load(sys.stdin)
    columns = data.get('columns') or 0
    for task in data.get('tasks', []):
        print(json.dumps({'id': task['id'], 'content': row(task, columns)}, ensure_ascii=False))
except Exception:
    # 何も出さなければ既定の表示のまま
    pass
