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
:root{--ivory:#F3EBDD;--paper:#FCF8F0;--paper-2:#F6EFE2;--line:#E2D5BF;--ink:#2F2B26;--ink-2:#6B6257;--ink-3:#9A8F81;
--rose:#B8697A;--rose-bg:#F6E4E3;--sage-bg:#E3EBDD;--forest:#2F3F34;--up:#B9443C;--down:#3D669B;--kraft:#B98549}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--ivory);color:var(--ink);font-family:'Pretendard Variable',Pretendard,-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;font-size:15px;line-height:1.6;word-break:keep-all;overflow-wrap:anywhere}
main{max-width:680px;margin:0 auto;padding:16px 16px 56px}
a{color:var(--rose)}
.brand{display:inline-flex;align-items:center;gap:6px;font-weight:800;font-size:18px;color:var(--forest);text-decoration:none}
.brand span{color:var(--rose)}
.crumb{font-size:13px;color:var(--ink-2);margin:12px 0 4px}
.crumb a{color:var(--ink-2)}
h1{font-family:'Gowun Batang',serif;font-size:26px;line-height:1.3;margin:4px 0 6px}
h2{font-size:17px;margin:30px 0 8px}
.lead{margin:0;color:var(--ink-2);font-size:14px}
.box{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:14px 16px;margin:14px 0}
.big{font-size:28px;font-weight:800}
.small{font-size:12.5px;color:var(--ink-2)}
.kpis{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
.kpis div{background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px 12px}
.kpis b{display:block;font-size:18px}
.kpis span{font-size:12px;color:var(--ink-2)}
.up{color:var(--up)}.down{color:var(--down)}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:14px}
th,td{padding:9px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:var(--paper-2);font-size:12.5px;color:var(--ink-2);font-weight:700}
tr:last-child td{border-bottom:0}
td.n,th.n{text-align:right;white-space:nowrap}
td.k{white-space:nowrap}
tr.hi td{background:var(--rose-bg)}
tr.lo td{background:var(--sage-bg)}
.bar{display:inline-block;height:8px;border-radius:4px;background:var(--rose);vertical-align:middle;margin-right:6px}
.cta{display:block;margin:12px 0 0;padding:14px;border-radius:14px;background:var(--forest);color:#fff;text-align:center;font-weight:700;text-decoration:none}
.cta.line{background:#fff;color:var(--forest);border:1.5px solid var(--forest)}
.notice{background:#fff;border:1px dashed var(--kraft);border-radius:12px;padding:10px 12px;font-size:13px;color:var(--ink-2);margin:12px 0}
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
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@700&display=swap">
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
    # 품종별 (최근 경매일)
    var = defaultdict(lambda: [0, 0, set()])
    grade = defaultdict(lambda: [0, 0])
    for _, v, g, avg, mx, mn, q, amt in items:
        if not q:
            continue
        var[v][0] += q; var[v][1] += amt; var[v][2].add(g)
        grade[g][0] += q; grade[g][1] += amt
    tq = sum(x[0] for x in var.values())
    if tq != top['lq']:
        raise ValueError(f"{raw}: 품종 합계 거래량 {tq} 와 품목 거래량 {top['lq']} 이 달라요")
    vs = sorted(((v, q, a, gs) for v, (q, a, gs) in var.items() if q >= MIN_VARIETY_QTY), key=lambda x: (-x[1], x[0]))
    shown = vs[:MAX_VARIETIES]
    rest = len(var) - len(shown)
    vrows = []
    for v, q, a, gs in shown:
        w = rows.get(raw + SEP + v) or {}
        vrows.append(f'<tr><td>{esc(v)}</td><td class="n">{num(a / q)}원</td><td class="n">{num(q)}속</td><td class="n">{num(w["wa"]) + "원" if w.get("wa") else "-"}</td></tr>')

    def grank(g):
        m = re.match(r'(특|상|보)?\s*(\d*)', g or '')
        return ({'특': 0, '상': 1, '보': 2}.get(m.group(1), 3), int(m.group(2) or 0), g)
    grows = ''.join(f'<tr><td class="k">{esc(g)}</td><td class="n">{num(a / q)}원</td><td class="n">{num(q)}속</td></tr>'
                    for g, (q, a) in sorted(grade.items(), key=lambda x: grank(x[0])) if q)
    # 8주 흐름
    tr = top.get('trend') or []
    labels = meta.get('weekLabels') or []
    mx = max(tr) if tr else 0
    wrows = ''.join(f'<tr><td class="k">{esc(l)}</td><td><span class="bar" style="width:{round(60 * v / mx)}px"></span></td><td class="n">{num(v)}원</td></tr>'
                    for l, v in zip(labels, tr) if v)
    # 1년 흐름 (품목 단위)
    h = [r for r in hist if r[1] == raw]
    months = defaultdict(lambda: [0, 0, set()])
    for d, _, q, a in h:
        months[d[:7]][0] += q; months[d[:7]][1] += a; months[d[:7]][2].add(d)
    yr = ''
    if h:
        first, last = min(r[0] for r in h), max(r[0] for r in h)
        full = [m for m in months if m != first[:7] and m != last[:7]]
        hi = max(full, key=lambda m: months[m][1] / months[m][0]) if full else None
        lo = min(full, key=lambda m: months[m][1] / months[m][0]) if full else None
        mrows = []
        for m in sorted(months):
            q, a, ds = months[m]
            note = ' <span class="small">(일부)</span>' if m not in full else ''
            cls = ' class="hi"' if m == hi else ' class="lo"' if m == lo else ''
            mrows.append(f'<tr{cls}><td class="k">{int(m[:4]) % 100}년 {int(m[5:])}월{note}</td><td class="n">{num(a / q)}원</td><td class="n">{num(q)}속</td><td class="n">{len(ds)}일</td></tr>')
        yq, ya = sum(r[2] for r in h), sum(r[3] for r in h)
        hl = ''
        if hi and lo:
            hl = (f'<p>지난 1년 동안 한 달 평균이 가장 높았던 달은 <b>{int(hi[5:])}월 {num(months[hi][1] / months[hi][0])}원</b>, '
                  f'가장 낮았던 달은 <b>{int(lo[5:])}월 {num(months[lo][1] / months[lo][0])}원</b>이었어요.</p>')
        yr = f"""<h2>{esc(disp)} 1년 시세 흐름</h2>
<p class="small">{dots(first)} ~ {dots(last)} 본경매 {len({r[0] for r in h})}일 기록, 품종·등급을 합친 {esc(disp)} 전체 평균이에요. 1년 평균 {num(ya / yq)}원, 거래량 {num(yq)}속.</p>
{hl}
<table><thead><tr><th>달</th><th class="n">평균가</th><th class="n">거래량</th><th class="n">경매일</th></tr></thead><tbody>
{chr(10).join(mrows)}
</tbody></table>
<p class="small">한 해 관측값이라 해마다 같은 흐름이라는 뜻은 아니에요. 처음과 마지막 달은 일부 날짜만 있어요. 설·추석 연휴에는 경매가 없었어요.</p>"""
    wk, pv, yw = meta.get('week') or [], meta.get('prev') or [], meta.get('yearWeek') or []
    wspan = lambda ws: f'{dots(ws[0])[5:]}~{dots(ws[-1])[5:]}' if ws else ''
    kp = [f'<div><span>최근 경매일 거래량</span><b>{num(top["lq"])}속</b></div>']
    if top.get('wa'):
        kp.append(f'<div><span>기준 주 평균 ({wspan(wk)})</span><b>{num(top["wa"])}원</b></div>')
    if top.get('pa'):
        kp.append(f'<div><span>그 전 주 평균 ({wspan(pv)})</span><b>{num(top["pa"])}원</b><span>기준 주가 {pct(top.get("wa"), top["pa"])}</span></div>')
    if top.get('ya'):
        kp.append(f'<div><span>작년 같은 주 ({dots(yw[0])[:4]} {wspan(yw)})</span><b>{num(top["ya"])}원</b><span>기준 주가 {pct(top.get("wa"), top["ya"])}</span></div>')
    alias = f'<p class="small">경매 이름: {esc(raw)}{", " + ", ".join(map(esc, others)) if others else ""}</p>' if raw != disp or others else ''
    body = f"""<h1>{esc(disp)} 경매 시세</h1>
<p class="lead">양재 aT 화훼공판장 {esc(disp)} 경매가를 품종·등급별로, 그리고 지난 1년 흐름까지 정리했어요. 1속(단) 평균 경매가예요.</p>
{alias}
<div class="box">
<p class="small" style="margin:0">최근 경매일 {kd(L)} · {esc(disp)} 전체 평균</p>
<p class="big" style="margin:2px 0">{num(top['la'])}원</p>
<div class="kpis">{''.join(kp)}</div>
</div>
<div class="notice">경매 낙찰가예요. 꽃집에서 사는 값(소매가)이나 도매상 판매가와 달라요.</div>
<h2>품종별 {esc(disp)} 시세 ({kd(L)})</h2>
<p class="small">거래량 {MIN_VARIETY_QTY}속 이상 품종, 거래량 많은 순{f'이에요. 그 밖에 {rest}품종이 더 거래됐어요.' if rest > 0 else '이에요.'} '기준 주'는 {wspan(wk)} 평균이에요.</p>
<table><thead><tr><th>품종</th><th class="n">평균가</th><th class="n">거래량</th><th class="n">기준 주</th></tr></thead><tbody>
{chr(10).join(vrows)}
</tbody></table>
<h2>등급별 {esc(disp)} 시세 ({kd(L)})</h2>
<p class="small">모든 품종을 합친 등급별 평균이에요. 특 → 상 → 보 순서예요.</p>
<table><thead><tr><th>등급</th><th class="n">평균가</th><th class="n">거래량</th></tr></thead><tbody>
{grows}
</tbody></table>
<h2>최근 8주 {esc(disp)} 시세</h2>
<p class="small">주마다 월·수·금 본경매를 거래량으로 가중한 평균이에요.</p>
<table><thead><tr><th>주</th><th></th><th class="n">평균가</th></tr></thead><tbody>
{wrows}
</tbody></table>
{yr}
<a class="cta" href="../?fav={urllib.parse.quote(disp)}">{esc(disp)} 관심 꽃에 담기</a>
<a class="cta line" href="../">전체 꽃 시세 보기 →</a>"""
    title = f'{disp} 시세 · 오늘 {disp} 경매가와 품종별 가격 | 오늘의 양재 꽃시세'
    desc = (f'양재 화훼공판장 {disp} 경매 시세. {kd(L)} {disp} 평균 {num(top["la"])}원(1속), 거래량 {num(top["lq"])}속. '
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
