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
:root{--ivory:#F3EBDD;--paper:#FCF8F0;--paper-2:#F6EFE2;--line:#E2D5BF;--line-2:#ECE3D3;--ink:#2F2B26;--ink-2:#6B6257;--ink-3:#9A8F81;
--rose:#B8697A;--rose-2:#E9C3C8;--rose-bg:#F6E4E3;--sage:#8FA88C;--sage-bg:#E3EBDD;--forest:#2F3F34;--up:#B9443C;--down:#3D669B;--kraft:#B98549}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--ivory);color:var(--ink);font-family:'Pretendard Variable',Pretendard,-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;font-size:15px;line-height:1.6;word-break:keep-all;overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
main{max-width:640px;margin:0 auto;padding:14px 16px 56px}
a{color:var(--rose)}
.brand{display:inline-flex;align-items:center;gap:6px;font-weight:800;font-size:17px;color:var(--forest);text-decoration:none}
.brand span{color:var(--rose)}
.crumb{font-size:13px;color:var(--ink-2);margin:10px 0 0}
.crumb a{color:var(--ink-2)}
.hero{position:relative;background:var(--paper);border:1px solid var(--line);border-radius:20px;padding:18px 18px 16px;margin:14px 0 10px;box-shadow:0 12px 26px -20px rgba(80,50,20,.45)}
.hero::before{content:"";position:absolute;top:-9px;left:28px;width:74px;height:20px;background:rgba(233,195,200,.75);transform:rotate(-4deg)}
.hero-top{display:flex;gap:12px;align-items:flex-start}
.hero-top img{width:84px;height:84px;object-fit:contain;flex:none;margin:-6px -4px 0 0}
.hand{font-family:'Nanum Pen Script',cursive;font-size:20px;color:var(--rose);margin:0;line-height:1}
h1{font-family:'Gowun Batang',serif;font-size:25px;line-height:1.3;margin:2px 0 4px}
.chip{display:inline-block;font-size:12.5px;color:var(--ink-2);background:var(--paper-2);border:1px solid var(--line-2);border-radius:999px;padding:2px 10px}
.price{font-size:34px;font-weight:800;letter-spacing:-.5px;margin:12px 0 0;line-height:1.2}
.price small{font-size:15px;font-weight:600;color:var(--ink-2);margin-left:4px}
.say{font-size:16px;font-weight:700;margin:4px 0 0}
.sub{font-size:13px;color:var(--ink-2);margin:2px 0 0}
.cmp{margin:14px 0 0;border-top:1px solid var(--line-2)}
.cmp div{display:grid;grid-template-columns:1fr auto 76px;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--line-2)}
.cmp div:last-child{border-bottom:0;padding-bottom:0}
.cmp span{font-size:14px;color:var(--ink-2)}
.cmp span i{display:block;font-style:normal;font-size:12px;color:var(--ink-3);line-height:1.3}
.cmp b{font-size:16px;text-align:right}
.cmp em{font-style:normal;font-size:14px;font-weight:700;text-align:right}
em{font-style:normal;font-weight:700}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--ink-3)}
.notice{font-size:12.5px;color:var(--ink-2);margin:0 2px}
h2{font-size:18px;margin:34px 0 4px}
.desc{font-size:13px;color:var(--ink-2);margin:0 0 10px}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden;font-size:14.5px}
th,td{padding:10px 10px;border-bottom:1px solid var(--line-2);text-align:left}
th{background:var(--paper-2);font-size:12.5px;color:var(--ink-2);font-weight:700}
tr:last-child td{border-bottom:0}
td.n,th.n{text-align:right;white-space:nowrap}
td.k{white-space:nowrap}
tr.now td{font-weight:800;background:var(--rose-bg)}
tr.hi td:first-child{box-shadow:inset 4px 0 var(--rose)}
tr.lo td:first-child{box-shadow:inset 4px 0 var(--sage)}
details{margin:10px 0 0}
summary{cursor:pointer;list-style:none;display:block;text-align:center;font-size:14px;font-weight:700;color:var(--forest);background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px}
summary::-webkit-details-marker{display:none}
details[open] summary{margin-bottom:10px}
.chart{background:#fff;border:1px solid var(--line);border-radius:14px;padding:10px 8px 4px;margin:0 0 10px}
.chart svg{display:block;width:100%;height:auto}
.legend{display:flex;gap:14px;font-size:12.5px;color:var(--ink-2);margin:0 0 8px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.cta{display:block;margin:12px 0 0;padding:14px;border-radius:14px;background:var(--forest);color:#fff;text-align:center;font-weight:700;text-decoration:none}
.cta.line{background:#fff;color:var(--forest);border:1.5px solid var(--forest)}
.foot{font-size:12px;color:var(--ink-3);line-height:1.7;margin:30px 0 0}
"""


def page(path, title, desc, crumbs, body, changed):
    up = '../' * path.count('/')
    url = BASE + path
    crumb_html = ' › '.join(f'<a href="{esc(h)}">{esc(n)}</a>' if h else f'<span>{esc(n)}</span>' for n, h in crumbs)
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
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@700&family=Nanum+Pen+Script&display=swap">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>{CSS}</style>
</head>
<body>
<main>
<a class="brand" href="{up}"><span>✿</span>오늘의 양재 꽃시세</a>
<nav class="crumb" aria-label="위치">{crumb_html}</nav>
{body}
<p class="foot">출처: 한국농수산식품유통공사 화훼유통정보시스템, 양재 aT 화훼공판장 절화 본경매. 경매 낙찰가예요. 소매가·도매상 판매가와 달라요. <a href="{up}privacy.html">개인정보처리방침</a><br>마지막 변경일 {esc(changed)}</p>
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
    dots = ''.join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{5 if k == len(vals) - 1 else 3}" fill="{"#B8697A" if k == len(vals) - 1 else "#fff"}" stroke="#B8697A" stroke-width="2"/>'
                   for k, (x, y) in enumerate(zip(xs, ys)))
    xl = ''.join(f'<text x="{x:.1f}" y="{H - 6}" font-size="11" fill="#9A8F81" text-anchor="middle">{esc(l.replace("주", ""))}</text>'
                 for k, (x, l) in enumerate(zip(xs, labels)) if k % 2 == 1 or k == len(vals) - 1)
    k0 = min(range(len(vals)), key=lambda k: vals[k])
    vl = (f'<text x="{xs[-1]:.1f}" y="{ys[-1] - 10:.1f}" font-size="12.5" font-weight="700" fill="#2F2B26" text-anchor="end">{num(vals[-1])}원</text>'
          + (f'<text x="{xs[k0]:.1f}" y="{ys[k0] + 18:.1f}" font-size="11.5" fill="#6B6257" text-anchor="{"start" if k0 == 0 else "middle"}">{num(vals[k0])}원</text>' if k0 != len(vals) - 1 else ''))
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="최근 8주 평균 경매가 그래프">'
            f'<polygon points="{area}" fill="#F6E4E3" opacity=".7"/><polyline points="{pts}" fill="none" stroke="#B8697A" stroke-width="2.5" stroke-linejoin="round"/>'
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
        col = '#B8697A' if m == hi else '#8FA88C' if m == lo else '#E2D5BF'
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
    items = [x for x in cat.get('items') or [] if x[0] == raw]
    var = defaultdict(lambda: [0, 0])
    grade = defaultdict(lambda: [0, 0])
    for _, v, g, avg, mx, mn, q, amt in items:
        if not q:
            continue
        var[v][0] += q; var[v][1] += amt
        grade[g][0] += q; grade[g][1] += amt
    tq = sum(x[0] for x in var.values())
    if tq != top['lq']:
        raise ValueError(f"{raw}: 품종 합계 거래량 {tq} 와 품목 거래량 {top['lq']} 이 달라요")
    la = top['la']
    wk, pv, yw = meta.get('week') or [], meta.get('prev') or [], meta.get('yearWeek') or []
    span = lambda ws: f'{int(ws[0][5:7])}.{int(ws[0][8:])}~{int(ws[-1][5:7])}.{int(ws[-1][8:])}' if ws else ''

    # 맨 위: 오늘 값 + 한 문장 + 같은 모양의 비교 세 줄 (모두 '최근 경매가'를 기준으로)
    t, c = chg(la, top.get('wa'))
    say = (f'지난주 평균보다 <span class="{c}">{t.split(" ")[-1]} {"올랐어요" if c == "up" else "내렸어요"}</span>'
           if c in ('up', 'down') else '지난주 평균과 비슷해요')
    cmp_rows = []
    for name, ws, v in (('지난주', wk, top.get('wa')), ('2주 전', pv, top.get('pa')), ('작년 같은 주', yw, top.get('ya'))):
        if v:
            cmp_rows.append(f'<div><span>{name}<i>{span(ws)}</i></span><b>{num(v)}원</b>{chg_html(la, v)}</div>')
    hero = f"""<section class="hero">
<div class="hero-top"><div style="flex:1;min-width:0">
<p class="hand">today's {esc(slug)}</p>
<h1>{esc(disp)} 경매 시세</h1>
<span class="chip">{kd(L)} 본경매 · 1속(단) 평균</span>
</div><img src="../img/flowers/{urllib.parse.quote(raw)}.webp" alt="" width="84" height="84"></div>
<p class="price">{num(la)}원<small>/속</small></p>
<p class="say">{say}</p>
<p class="sub">이날 거래량 {num(top['lq'])}속{f" · 경매 이름 {esc(raw)}" if raw != disp else ""}{(", " + ", ".join(map(esc, others))) if others else ""}</p>
<div class="cmp">{''.join(cmp_rows)}</div>
<p class="sub" style="margin-top:8px">오른쪽 %는 최근 경매가({num(la)}원)가 그때보다 얼마나 바뀌었는지예요.</p>
</section>
<p class="notice">경매 낙찰가예요. 꽃집에서 사는 값(소매가)이나 도매상 판매가와 달라요.</p>"""

    # 품종별: 10개 먼저, 나머지는 접기. 마지막 칸은 '지난주보다' 변화
    vs = sorted(((v, q, a) for v, (q, a) in var.items() if q >= MIN_VARIETY_QTY), key=lambda x: (-x[1], x[0]))[:MAX_VARIETIES]
    rest = len(var) - len(vs)

    def vrow(v, q, a):
        w = (rows.get(raw + SEP + v) or {}).get('wa')
        return f'<tr><td>{esc(v)}</td><td class="n">{num(a / q)}원</td><td class="n">{num(q)}속</td><td class="n">{chg_html(a / q, w) if w else "-"}</td></tr>'
    head = '<thead><tr><th>품종</th><th class="n">평균가</th><th class="n">거래량</th><th class="n">지난주보다</th></tr></thead>'
    vtab = f'<table>{head}<tbody>\n' + '\n'.join(vrow(*x) for x in vs[:10]) + '\n</tbody></table>'
    if len(vs) > 10:
        vtab += (f'<details><summary>품종 {len(vs) - 10}개 더 보기</summary><table>{head}<tbody>\n'
                 + '\n'.join(vrow(*x) for x in vs[10:]) + '\n</tbody></table></details>')

    def grank(g):
        m = re.match(r'(특|상|보)?\s*(\d*)', g or '')
        return ({'특': 0, '상': 1, '보': 2}.get(m.group(1), 3), int(m.group(2) or 0), g)
    grows = '\n'.join(f'<tr><td class="k">{esc(g)}</td><td class="n">{num(a / q)}원</td><td class="n">{num(q)}속</td></tr>'
                      for g, (q, a) in sorted(grade.items(), key=lambda x: grank(x[0])) if q)

    # 8주: 꺾은선 + 표(전 주보다)
    tr = top.get('trend') or []
    labels = meta.get('weekLabels') or []
    wk8 = [(l, v) for l, v in zip(labels, tr) if v]
    wrows = []
    for k, (l, v) in enumerate(wk8):
        prev = wk8[k - 1][1] if k else None
        wrows.append(f'<tr{" class=\"now\"" if k == len(wk8) - 1 else ""}><td class="k">{esc(l)}{" (지난주)" if k == len(wk8) - 1 else ""}</td><td class="n">{num(v)}원</td><td class="n">{chg_html(v, prev) if prev else "-"}</td></tr>')
    w8 = ''
    if len(wk8) >= 3:
        first, last = wk8[0][1], wk8[-1][1]
        t8, c8 = chg(last, first)
        w8 = f"""<h2>최근 8주 {esc(disp)} 시세</h2>
<p class="desc">주마다 월·수·금 본경매를 거래량으로 가중한 평균이에요. 8주 전보다 <span class="{c8}">{t8}</span>.</p>
<div class="chart">{line_chart([l for l, _ in wk8], [v for _, v in wk8])}</div>
<details><summary>주별 숫자 보기</summary><table><thead><tr><th>주</th><th class="n">평균가</th><th class="n">전 주보다</th></tr></thead><tbody>
{chr(10).join(wrows)}
</tbody></table></details>"""

    # 1년: 요약 문장 + 막대 + 접은 표 (품목 단위)
    h = [r for r in hist if r[1] == raw]
    months = defaultdict(lambda: [0, 0, set()])
    for d, _, q, a in h:
        months[d[:7]][0] += q; months[d[:7]][1] += a; months[d[:7]][2].add(d)
    yr = ''
    if h:
        first, last = min(r[0] for r in h), max(r[0] for r in h)
        full = [m for m in months if m != first[:7] and m != last[:7]]
        avg = lambda m: months[m][1] / months[m][0]
        hi = max(full, key=avg) if full else None
        lo = min(full, key=avg) if full else None
        ms = sorted(months.items())
        mrows = []
        for m, (q, a, ds) in ms:
            cls = ' class="hi"' if m == hi else ' class="lo"' if m == lo else ''
            note = ' <span class="sub">(일부)</span>' if m not in full else ''
            mrows.append(f'<tr{cls}><td class="k">{int(m[:4]) % 100}년 {int(m[5:])}월{note}</td><td class="n">{num(a / q)}원</td><td class="n">{num(q)}속</td></tr>')
        yq, ya = sum(r[2] for r in h), sum(r[3] for r in h)
        lead = (f'지난 1년 {esc(disp)} 평균은 <b>{num(ya / yq)}원</b>이었어요. 가장 비싼 달은 <b class="up">{int(hi[5:])}월 {num(avg(hi))}원</b>, '
                f'가장 싼 달은 <b class="down">{int(lo[5:])}월 {num(avg(lo))}원</b>이었어요.') if hi and lo else ''
        yr = f"""<h2>{esc(disp)} 1년 시세 흐름</h2>
<p class="desc">{lead}</p>
<div class="chart"><div class="legend"><span><i style="background:#B8697A"></i>가장 비싼 달</span><span><i style="background:#8FA88C"></i>가장 싼 달</span><span><i style="background:#E2D5BF;opacity:.5;outline:1px dashed #C9B89C"></i>일부 날짜만</span></div>{month_bars(ms, hi, lo, full)}</div>
<details><summary>달별 숫자 보기</summary><table><thead><tr><th>달</th><th class="n">평균가</th><th class="n">거래량</th></tr></thead><tbody>
{chr(10).join(mrows)}
</tbody></table></details>
<p class="desc" style="margin-top:10px">{dots(first)} ~ {dots(last)} 본경매 {len({r[0] for r in h})}일 기록, 품종·등급을 합친 평균이에요. 한 해 관측값이라 해마다 같은 흐름이라는 뜻은 아니에요. 처음과 마지막 달은 일부 날짜만 있고, 설·추석 연휴에는 경매가 없었어요.</p>"""

    body = f"""{hero}
<h2>품종별 {esc(disp)} 시세</h2>
<p class="desc">{kd(L)} 본경매, 거래량 {MIN_VARIETY_QTY}속 이상 품종을 거래량 많은 순으로 보여 줘요.{f" 그 밖에 {rest}품종이 더 거래됐어요." if rest > 0 else ""}</p>
{vtab}
<h2>등급별 {esc(disp)} 시세</h2>
<p class="desc">{kd(L)} 본경매, 모든 품종을 합친 등급별 평균이에요. 특 → 상 → 보 순서예요.</p>
<table><thead><tr><th>등급</th><th class="n">평균가</th><th class="n">거래량</th></tr></thead><tbody>
{grows}
</tbody></table>
{w8}
{yr}
<a class="cta" href="../?fav={urllib.parse.quote(disp)}">☆ {esc(disp)} 관심 꽃에 담기</a>
<a class="cta line" href="../">전체 꽃 시세 보기 →</a>"""
    title = f'{disp} 시세 · 오늘 {disp} 경매가와 품종별 가격 | 오늘의 양재 꽃시세'
    desc = (f'양재 화훼공판장 {disp} 경매 시세. {kd(L)} {disp} 평균 {num(la)}원(1속), 거래량 {num(top["lq"])}속. '
            f'품종·등급별 가격, 최근 8주와 지난 1년 흐름을 볼 수 있어요.')
    return title, desc, [('꽃시세', '../'), (disp, None)], body, L


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
            title, desc, crumbs, body, changed = flower_page(s, raw, disp, others, snap, hist)
            texts[f'flower/{s}.html'] = page(f'flower/{s}.html', title, desc, crumbs, body, changed)
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
