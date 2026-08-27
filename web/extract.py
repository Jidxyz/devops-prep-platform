import json, re

MATRIX = '/mnt/user-data/uploads/devops-interview-skills-question-matrix.md'
KEY    = '/mnt/user-data/uploads/git-answer-key.md'

# ---- matrix: Git domain is lines 15..162 ----
lines = open(MATRIX, encoding='utf-8').read().split('\n')[14:162]

sections, cur = [], None
row = re.compile(r'^\|\s*(\d+\.\d+)\s*\|\s*(.+?)\s*\|\s*\|\s*\|\s*$')
for ln in lines:
    m = re.match(r'^##\s+(\d+)\.\s+(.+?)\s*$', ln)
    if m:
        cur = {'num': int(m.group(1)), 'title': m.group(2).strip(), 'items': []}
        sections.append(cur)
        continue
    if ln.startswith('## '):        # scoring summary etc
        cur = None
        continue
    r = row.match(ln)
    if r and cur is not None:
        cur['items'].append({'id': r.group(1), 'capability': r.group(2).strip()})

# ---- answer key: **1.1 — Title** ... until next **n.n or ---- ----
raw = open(KEY, encoding='utf-8').read()
starts = [(m.start(), m.group(1), m.group(2).strip())
          for m in re.finditer(r'^\*\*(\d+\.\d+)\s*—\s*([^*]+?)\*\*\s*$', raw, re.M)]

answers = {}
for i, (pos, iid, title) in enumerate(starts):
    end = starts[i+1][0] if i+1 < len(starts) else len(raw)
    body = raw[pos:end]
    body = body.split('\n', 1)[1] if '\n' in body else ''
    body = re.sub(r'\n---\s*\n.*$', '\n', body, flags=re.S)   # trim trailing section rule
    answers[iid] = {'title': title, 'body': body.strip()}

total = 0
for s in sections:
    for it in s['items']:
        a = answers.get(it['id'])
        it['title']  = a['title'] if a else it['capability']
        it['answer'] = a['body']  if a else ''
        total += 1

missing = [it['id'] for s in sections for it in s['items'] if not it['answer']]
print(f"sections: {len(sections)}  items: {total}  answers matched: {total-len(missing)}")
if missing: print("MISSING:", missing)

json.dump({'domain': 'Git', 'sections': sections},
          open('git-data.json', 'w', encoding='utf-8'), ensure_ascii=False)
print("bytes:", len(open('git-data.json', encoding='utf-8').read()))
