# 꽃별 시세 페이지(검색용 글자 페이지)를 만듭니다. 예: flower/rose.html (장미)
#
# 메인 화면이 '오늘 얼마? 지난주보다 올랐나?'에 답한다면, 꽃별 페이지는
# '품종·등급 중 무엇을 고를까? 1년 동안 어땠나?'에 답합니다 (docs: flower-planner 저장소 docs/seo-plan-20261120.md 6-2).
#
# 자료
# - data/snapshot.json : 최근 경매일 품종×등급(catalog), 8주 흐름·지난주·작년 같은 주(index)
# - data/history/items-YYYY-MM.csv : 품목 단위 하루 합계 1년치 (품종·등급 없음)
# 원칙
# - HTML 안에 꽃 이름·가격이 처음부터 글자로 있음. 같은 자료면 같은 파일(만든 시각을 넣지 않음).
# - 1년 수치는 품목 단위로만, '지난 1년 관측'이라고 밝힘. 계절 법칙처럼 단정하지 않음.
# - 검사에 걸리면 아무 파일도 쓰지 않음.
#
# 쓰는 법: python3 tools/build_pages.py            (FLOWERS 전부)
#          python3 tools/build_pages.py --only rose
import argparse, csv, glob, html, json, os, re, sys, urllib.parse
from collections import defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://best15993232-sudo.github.io/flower-sise/'
SEP = '␟'
# 주소용 영문 이름: 경매 품목명(원자료 그대로), 화면 이름, 다른 이름
FLOWERS = {
    'rose': ('장미', '장미', []),
}
MIN_VARIETY_QTY = 30      # 품종 표: 최근 경매일 거래량 30속 이상만
MAX_VARIETIES = 30
DOW = '월화수목금토일'
esc = lambda s: html.escape(str(s), quote=True)


def num(n):
    return f'{int(round(n)):,}'


def kd(d):            # 2026-11-20 → 11월 20일(금)
    x = date.fromisoformat(d)
    return f'{x.month}월 {x.day}일({DOW[x.weekday()]})'


def dots(d):          # 2026-11-20 → 2026.11.20
    return d.replace('-', '.')


def pct(a, b):
    if not a or not b:
        return '-'
    r = a / b - 1
    return f"{'▲' if r > 0 else '▼' if r < 0 else ''} {abs(r) * 100:.1f}%".strip()


def load_history():
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'data', 'history', 'items-*.csv'))):
        with open(p, encoding='utf-8') as f:
            r = csv.reader(f)
            next(r)
            rows += [(d, item, int(q), int(a)) for d, item, q, a, *_ in r]
    return rows


CSS = """
:root{--bg:#F5EFE6;--card:#FFFDF9;--line:#EAE1D3;--ink:#2B2723;--ink-2:#7A7064;--accent:#2F3F34;--up:#C0463E;--down:#3B6CA8}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:'Pretendard Variable',Pretendard,-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;font-size:15px;line-height:1.55;word-break:keep-all;font-variant-numeric:tabular-nums;letter-spacing:-.2px}
main{max-width:600px;margin:0 auto;padding:18px 20px 64px}
a{color:inherit}
.top{font-size:13px;color:var(--ink-2)}
.top a{text-decoration:none;font-weight:700;color:var(--accent)}
.hero{display:flex;justify-content:space-between;align-items:flex-start;margin:22px 0 0}
.hero img{width:72px;height:72px;object-fit:contain;margin-top:-6px}
h1{font-size:22px;font-weight:800;margin:0;letter-spacing:-.5px}
.meta{font-size:13px;color:var(--ink-2);margin:2px 0 0}
.price{font-size:36px;font-weight:800;letter-spacing:-1px;margin:14px 0 0;line-height:1.1}
.price span{font-size:15px;font-weight:600;color:var(--ink-2);margin-left:2px}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:18px 0 0}
.tiles div{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px}
.tiles span{display:block;font-size:13px;color:var(--ink-2);white-space:nowrap}
.tiles b{display:block;font-size:17px;margin-top:2px}
em{font-style:normal;font-weight:700}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--ink-2)}
h2{font-size:17px;font-weight:800;margin:40px 0 0}
h2+.meta{margin-bottom:12px}
.list{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:0 14px}
.list table{width:100%;border-collapse:collapse;table-layout:fixed}
.list th{font-size:13px;font-weight:600;color:var(--ink-2);text-align:left;padding:12px 0 8px}
.list td{padding:12px 0;border-top:1px solid var(--line);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.list th:nth-child(n+2),.list td:nth-child(n+2){text-align:right}
.list col.c1{width:46%}
details summary{list-style:none;cursor:pointer;text-align:center;font-size:14px;font-weight:700;color:var(--accent);padding:12px 0;border-top:1px solid var(--line)}
details summary::-webkit-details-marker{display:none}
details[open] summary{display:none}
.chart{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 10px 6px}
.chart svg{display:block;width:100%;height:auto}
.cta{display:block;margin:40px 0 0;padding:15px;border-radius:14px;background:var(--accent);color:#fff;text-align:center;font-weight:700;text-decoration:none}
.more{display:block;text-align:center;margin:14px 0 0;font-size:14px;font-weight:700;color:var(--accent);text-decoration:none}
.foot{font-size:12px;color:var(--ink-2);line-height:1.7;margin:40px 0 0;padding-top:16px;border-top:1px solid var(--line)}
.foot a{color:var(--ink-2)}
"""


def page(path, title, desc, crumbs, body, changed, FOOT_NOTE=''):
    up = '../' * path.count('/')
    url = BASE + path
    crumb_html = ' › '.join(f'<a href="{esc(h)}">✿ 오늘의 양재 꽃시세</a>' if h and i == 0 else f'<a href="{esc(h)}">{esc(n)}</a>' if h else f'<span>{esc(n)}</span>' for i, (n, h) in enumerate(crumbs))
    ld = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': urllib.parse.urljoin(url, h) if h else url}
        for i, (n, h) in enumerate(crumbs)]}
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{esc(url)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{BASE}og.jpg?v=1">
<meta name="theme-color" content="#F3EBDD">
<link rel="icon" type="image/svg+xml" href="{up}img/favicon.svg?v=4">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>{CSS}</style>
</head>
<body>
<main>
<nav class="top" aria-label="위치">{crumb_html}</nav>
{body}
<p class="foot">{FOOT_NOTE}경매 낙찰가예요. 꽃집 소매가나 도매상 판매가와 달라요.<br>출처: 한국농수산식품유통공사 화훼유통정보시스템 (양재 aT 화훼공판장 절화 본경매)<br><a href="{up}privacy.html">개인정보처리방침</a> · 마지막 변경일 {esc(changed)}</p>
</main>
<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "8be9a26d6f3f4182aff85b28dbce6b00"}}'></script>
</body>
</html>
"""


def chg(a, b):
    """a 가 b 보다 얼마나 바뀌었는지: (글자, 색 이름)"""
    if not a or not b:
        return '-', 'flat'
    r = a / b - 1
    if abs(r) < 0.0005:
        return '변동 없음', 'flat'
    return f"{'▲' if r > 0 else '▼'} {abs(r) * 100:.1f}%", 'up' if r > 0 else 'down'


def chg_html(a, b):
    t, c = chg(a, b)
    return f'<em class="{c}">{t}</em>'


def line_chart(labels, vals):
    """8주 꺾은선 (SVG). 마지막 주는 진한 점과 값."""
    W, H, L, R, T, B = 340, 150, 12, 12, 26, 26
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.15 or hi * 0.1
    lo, hi = lo - pad, hi + pad
    xs = [L + (W - L - R) * k / (len(vals) - 1) for k in range(len(vals))]
    ys = [T + (H - T - B) * (1 - (v - lo) / (hi - lo)) for v in vals]
    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in zip(xs, ys))
    area = f'{xs[0]:.1f},{H - B} ' + pts + f' {xs[-1]:.1f},{H - B}'
    dots = ''.join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{5 if k == len(vals) - 1 else 3}" fill="{"#2F3F34" if k == len(vals) - 1 else "#fff"}" stroke="#2F3F34" stroke-width="2"/>'
                   for k, (x, y) in enumerate(zip(xs, ys)))
    xl = ''.join(f'<text x="{x:.1f}" y="{H - 6}" font-size="11" fill="#9A8F81" text-anchor="middle">{esc(l.replace("주", ""))}</text>'
                 for k, (x, l) in enumerate(zip(xs, labels)) if k % 2 == 1 or k == len(vals) - 1)
    k0 = min(range(len(vals)), key=lambda k: vals[k])
    vl = (f'<text x="{xs[-1]:.1f}" y="{ys[-1] - 10:.1f}" font-size="12.5" font-weight="700" fill="#2F2B26" text-anchor="end">{num(vals[-1])}원</text>'
          + (f'<text x="{xs[k0]:.1f}" y="{ys[k0] + 18:.1f}" font-size="11.5" fill="#6B6257" text-anchor="{"start" if k0 == 0 else "middle"}">{num(vals[k0])}원</text>' if k0 != len(vals) - 1 else ''))
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="최근 8주 평균 경매가 그래프">'
            f'<polygon points="{area}" fill="#2F3F34" opacity=".06"/><polyline points="{pts}" fill="none" stroke="#2F3F34" stroke-width="2.2" stroke-linejoin="round"/>'
            f'{dots}{xl}{vl}</svg>')


def month_bars(ms, hi, lo, full):
    """달별 평균가 막대 (0원부터). 가장 비싼 달 분홍, 가장 싼 달 초록, 일부 날짜만 있는 달은 옅게."""
    W, H, T, B = 340, 140, 10, 22
    vals = [a / q for _, (q, a, _d) in ms]
    mx = max(vals)
    bw = (W - 8) / len(ms)
    out = []
    for k, ((m, _), v) in enumerate(zip(ms, vals)):
        h = (H - T - B) * v / mx
        x = 4 + bw * k
        col = '#C0463E' if m == hi else '#3B6CA8' if m == lo else '#E3D8C6'
        part = '' if m in full else ' fill-opacity=".45" stroke="#C9B89C" stroke-dasharray="3 2"'
        out.append(f'<rect x="{x + 3:.1f}" y="{H - B - h:.1f}" width="{bw - 6:.1f}" height="{h:.1f}" rx="3" fill="{col}"{part}/>'
                   f'<text x="{x + bw / 2:.1f}" y="{H - 7}" font-size="10.5" fill="#9A8F81" text-anchor="middle">{int(m[5:])}</text>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="달별 평균 경매가 막대">{"".join(out)}</svg>'


def flower_page(slug, raw, disp, others, snap, hist):
    meta = snap['index']['meta']
    rows = snap['index']['rows']
    top = rows.get(raw + SEP + '*')
    if not top or not top.get('lastDate'):
        raise ValueError(f'{raw}: 최근 경매 자료가 없어요')
    L = top['lastDate']
    cat = snap.get('catalog') or {}
    if cat.get('date') != L:
        raise ValueError(f"{raw}: 품종·등급 자료 날짜({cat.get('date')})가 최근 경매일({L})과 달라요")
    var = defaultdict(lambda: [0, 0])
    grade = defaultdict(lambda: [0, 0])
    for _, v, g, avg, mx, mn, q, amt in (x for x in cat.get('items') or [] if x[0] == raw):
        if not q:
            continue
        var[v][0] += q; var[v][1] += amt
        grade[g][0] += q; grade[g][1] += amt
    if sum(x[0] for x in var.values()) != top['lq']:
        raise ValueError(f"{raw}: 품종 합계 거래량과 품목 거래량 {top['lq']} 이 달라요")
    la = top['la']
    name_note = f' · 경매 이름 {esc(raw)}' if raw != disp else ''

    # 맨 위: 이름 · 가격 · 비교 3칸 (% 만)
    tiles = ''.join(f'<div><span>{n}</span>{chg_html(la, v).replace("<em", "<b").replace("</em>", "</b>")}</div>'
                    for n, v in (('지난주보다', top.get('wa')), ('2주 전보다', top.get('pa')), ('작년보다', top.get('ya'))) if v)
    hero = f"""<div class="hero"><div>
<h1>{esc(disp)} 경매 시세</h1>
<p class="meta">{kd(L)} 본경매 · 1속 평균{name_note}</p>
</div><img src="../img/flowers/{urllib.parse.quote(raw)}.webp" alt="" width="72" height="72"></div>
<p class="price">{num(la)}<span>원</span></p>
<div class="tiles">{tiles}</div>"""

    def table(head, rows_html, more=None):
        cols = '<colgroup><col class="c1"><col><col></colgroup>'
        t = f'<div class="list"><table>{cols}<thead><tr>{head}</tr></thead><tbody>\n{rows_html}\n</tbody></table>'
        if more:
            t += f'<details><summary>{more[0]}</summary><table>{cols}<tbody>\n{more[1]}\n</tbody></table></details>'
        return t + '</div>'

    # 품종: 3칸, 10개 + 더 보기
    vs = sorted(((v, q, a) for v, (q, a) in var.items() if q >= MIN_VARIETY_QTY), key=lambda x: (-x[1], x[0]))[:MAX_VARIETIES]
    vr = lambda v, q, a: (f'<tr><td title="{esc(v)}">{esc(v)}</td><td>{num(a / q)}원</td>'
                          f'<td>{chg_html(a / q, (rows.get(raw + SEP + v) or {}).get("wa"))}</td></tr>')
    vsec = table('<th>품종</th><th>평균가</th><th>지난주 대비</th>', '\n'.join(vr(*x) for x in vs[:10]),
                 (f'{len(vs) - 10}개 더 보기', '\n'.join(vr(*x) for x in vs[10:])) if len(vs) > 10 else None)

    def grank(g):
        m = re.match(r'(특|상|보)?\s*(\d*)', g or '')
        return ({'특': 0, '상': 1, '보': 2}.get(m.group(1), 3), int(m.group(2) or 0), g)
    gsec = table('<th>등급</th><th>평균가</th><th>거래량</th>', '\n'.join(
        f'<tr><td>{esc(g)}</td><td>{num(a / q)}원</td><td>{num(q)}속</td></tr>'
        for g, (q, a) in sorted(grade.items(), key=lambda x: grank(x[0])) if q))

    # 8주
    wk8 = [(l, v) for l, v in zip(meta.get('weekLabels') or [], top.get('trend') or []) if v]
    w8 = ''
    if len(wk8) >= 3:
        t8, c8 = chg(wk8[-1][1], wk8[0][1])
        w8 = f"""<h2>최근 8주 흐름</h2>
<p class="meta">주 평균 · 8주 전 대비 <em class="{c8}">{t8}</em></p>
<div class="chart">{line_chart([l for l, _ in wk8], [v for _, v in wk8])}</div>"""

    # 1년 (품목 단위)
    h = [r for r in hist if r[1] == raw]
    yr, note = '', ''
    if h:
        months = defaultdict(lambda: [0, 0, set()])
        for d, _, q, a in h:
            months[d[:7]][0] += q; months[d[:7]][1] += a; months[d[:7]][2].add(d)
        first, last = min(r[0] for r in h), max(r[0] for r in h)
        full = [m for m in months if m not in (first[:7], last[:7])]
        avg = lambda m: months[m][1] / months[m][0]
        hi, lo = (max(full, key=avg), min(full, key=avg)) if full else (None, None)
        ms = sorted(months.items())
        mrows = '\n'.join(f'<tr><td>{int(m[:4]) % 100}년 {int(m[5:])}월{"" if m in full else " (일부)"}</td><td>{num(a / q)}원</td><td>{num(q)}속</td></tr>'
                          for m, (q, a, ds) in ms)
        lead = (f'<em class="up">{int(hi[5:])}월</em> 가장 비쌈 {num(avg(hi))}원 · <em class="down">{int(lo[5:])}월</em> 가장 쌈 {num(avg(lo))}원'
                if hi else '')
        yr = f"""<h2>지난 1년 흐름</h2>
<p class="meta">{lead}</p>
<div class="chart">{month_bars(ms, hi, lo, full)}</div>
<details style="margin-top:6px"><summary>달별 숫자 보기</summary>{table('<th>달</th><th>평균가</th><th>거래량</th>', mrows)}</details>"""
        note = (f'1년 흐름은 {dots(first)}~{dots(last)} 본경매 {len({r[0] for r in h})}일, 품종·등급을 합친 {esc(disp)} 평균이에요. '
                f'한 해 관측값이라 해마다 같다는 뜻은 아니에요. 점선 막대는 일부 날짜만 있는 달이에요.<br>')

    body = f"""{hero}
<h2>품종별 시세</h2>
<p class="meta">{kd(L)} · 거래 많은 순</p>
{vsec}
<h2>등급별 시세</h2>
<p class="meta">{kd(L)} · 모든 품종 합계</p>
{gsec}
{w8}
{yr}
<a class="cta" href="../?fav={urllib.parse.quote(disp)}">{esc(disp)} 관심 꽃에 담기</a>
<a class="more" href="../">전체 꽃 시세 보기</a>"""
    title = f'{disp} 시세 · 오늘 {disp} 경매가와 품종별 가격 | 오늘의 양재 꽃시세'
    desc = (f'양재 화훼공판장 {disp} 경매 시세. {kd(L)} {disp} 평균 {num(la)}원(1속), 거래량 {num(top["lq"])}속. '
            f'품종·등급별 가격, 최근 8주와 지난 1년 흐름을 볼 수 있어요.')
    return title, desc, [('꽃시세', '../'), (disp, None)], body, L, note


def verify(texts):
    err = []
    for p, t in texts.items():
        if 'noindex' in t: err.append(f'{p}: noindex')
        if '—' in t: err.append(f'{p}: em dash 기호가 있어요')
        if f'<link rel="canonical" href="{BASE}{p}">' not in t: err.append(f'{p}: canonical 다름')
        if '<tbody>\n\n</tbody>' in t or '<tbody>\n</tbody>' in t: err.append(f'{p}: 빈 표')
        for h in re.findall(r'href="([^"]+)"', t):
            if re.match(r'(https?:|mailto:|#)', h): continue
            tgt = os.path.normpath(os.path.join(os.path.dirname(p), h.split('?')[0]))
            tgt = 'index.html' if tgt in ('.', '') else tgt
            if not os.path.exists(os.path.join(ROOT, tgt)) and tgt not in texts: err.append(f'{p}: 없는 링크 {h}')
    return err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only')
    a = ap.parse_args()
    slugs = [s.strip() for s in a.only.split(',')] if a.only else list(FLOWERS)
    snap = json.load(open(os.path.join(ROOT, 'data', 'snapshot.json'), encoding='utf-8'))
    hist = load_history()
    texts = {}
    try:
        for s in slugs:
            raw, disp, others = FLOWERS[s]
            title, desc, crumbs, body, changed, note = flower_page(s, raw, disp, others, snap, hist)
            texts[f'flower/{s}.html'] = page(f'flower/{s}.html', title, desc, crumbs, body, changed, note)
    except ValueError as e:
        print('꽃별 페이지 건너뜀 (파일 그대로):', e)
        return 0
    err = verify(texts)
    if err:
        print('\n'.join(err))
        print('검사에 걸려 꽃별 페이지를 바꾸지 않았어요')
        return 0
    n = 0
    for p, t in texts.items():
        f = os.path.join(ROOT, p)
        if os.path.exists(f) and open(f, encoding='utf-8').read() == t:
            continue
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f + '.tmp', 'w', encoding='utf-8') as o:
            o.write(t)
        os.replace(f + '.tmp', f)
        n += 1
    print(f'꽃별 페이지 {len(texts)}개, 바뀐 파일 {n}개')
    return 0


if __name__ == '__main__':
    sys.exit(main())
