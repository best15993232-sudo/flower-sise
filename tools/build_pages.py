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
# 발행 기준 (사용자 결정 2026-11-20, B안): 1년 기록 153 경매일 중 120일 이상 거래, 1년 20,000속 이상,
# 지난주 300속 이상. '절화'·'절지'·'허브'처럼 여러 꽃을 묶은 이름은 뺌. 나머지 품목은 flower/others.html 한 페이지.
FLOWERS = {
    'rose': ('장미', '장미', []), 'chrysanthemum': ('국화', '국화', []), 'gerbera': ('거베라', '거베라', []),
    'lisianthus': ('리시안사스', '리시안셔스', []), 'stock': ('스톡크', '스토크', []), 'lily': ('백합', '백합', []),
    'ruscus': ('루스커스', '루스커스', []), 'eucalyptus': ('유칼립투스', '유칼립투스', []), 'calla': ('칼라', '칼라', []),
    'oxypetalum': ('옥시페탈륨', '옥시페탈륨', []), 'anthurium': ('안시리움', '안스리움', []), 'tulip': ('튜립', '튤립', []),
    'alstroemeria': ('알스트메리아', '알스트로메리아', []), 'sunflower': ('해바라기', '해바라기', []),
    'statice': ('스타티스', '스타티스', []), 'nomura': ('노무라', '노무라', []), 'borisacho': ('보리사초', '보리사초', []),
    'gypsophila': ('안개', '안개꽃', []), 'aster': ('공작초', '공작초', []), 'delphinium': ('델피니움', '델피니움', []),
    'chamomile': ('캐모마일', '캐모마일', []), 'hinoki': ('편백', '편백', []), 'panicum': ('파니쿰', '파니쿰', []),
    'celosia': ('맨드라미', '맨드라미', []), 'marguerite': ('마가렛', '마가렛', []), 'dahlia': ('다알리아', '달리아', []),
    'aspidistra': ('엽란', '엽란', []), 'marigold': ('메리골드', '메리골드', []), 'carnation': ('카네이션', '카네이션', []),
    'dianthus': ('석죽', '석죽', []), 'gladiolus': ('글라디올러스', '글라디올러스', []), 'ammi': ('아미초', '아미초', []),
    'scabiosa': ('스카비오사', '스카비오사', []), 'silene': ('시레네', '실레네', []), 'winter-jasmine': ('영춘화', '영춘화', []),
    'gomphrena': ('천일홍', '천일홍', []), 'phlox': ('후록스', '플록스', []), 'cycas': ('소철', '소철', []),
    'naengicho': ('냉이초', '냉이초', []), 'bullocho': ('불노초', '불로초', []), 'didiscus': ('디디스커스', '디디스커스', []),
    'solidaster': ('솔리다스터', '솔리다스터', []), 'veronica': ('베로니카', '베로니카', []), 'solidago': ('솔리다고', '솔리다고', []),
}
GENERIC = {'절화', '절지', '허브'}
MIN_VARIETY_QTY = 30      # 품종 표: 최근 경매일 거래량 30속 이상만
MAX_VARIETIES = 30
MIN_CMP_QTY = 100         # 지난주·2주 전·작년 비교: 그 주 거래량 100속 이상일 때만 %
MIN_YEAR_DAYS = 300       # 1년 흐름: 기록이 300일 넘게 이어질 때만 (8주 자료로 1년 수치를 만들지 않음)
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
.links{display:flex;flex-wrap:wrap;gap:8px 18px;font-size:14px;margin:12px 0 0}
.links a{color:var(--accent);text-decoration:none;white-space:nowrap}
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


def year_rows(hist, raw):
    """'지난 1년': 그 꽃 기록 중 가장 최근 기록일부터 365일 안 (기록이 쌓여도 창이 앞으로 움직임)"""
    h = [r for r in hist if r[1] == raw]
    if not h:
        return h
    end = date.fromisoformat(max(r[0] for r in hist))
    return [r for r in h if (end - date.fromisoformat(r[0])).days < 365]


def img_tag(raw):
    return (f'<img src="../img/flowers/{urllib.parse.quote(raw)}.webp" alt="" width="72" height="72">'
            if os.path.exists(os.path.join(ROOT, 'img', 'flowers', raw + '.webp')) else '')


def other_links(cur):
    links = ''.join(f'<a href="{s}.html">{esc(d)}</a>' for s, (_, d, _o) in sorted(FLOWERS.items(), key=lambda x: x[1][1]) if s != cur)
    tail = '' if cur == 'others' else '<a href="others.html">기타 품목</a>'
    return f'<h2>다른 꽃 시세</h2>\n<p class="links">{links}{tail}</p>'


def others_page(snap):
    """FLOWERS 에 없는 품목: 최근 경매일 품목별 평균가·거래량 한 표"""
    meta, rows = snap['index']['meta'], snap['index']['rows']
    L = meta.get('latestDate') or ''
    cat = snap.get('catalog') or {}
    if cat.get('date') != L:
        raise ValueError(f"기타 품목: 자료 날짜({cat.get('date')})가 최근 경매일({L})과 달라요")
    mine = {r for r, _d, _o in FLOWERS.values()}
    q, a = defaultdict(int), defaultdict(int)
    for x in cat.get('items') or []:
        if x[0] not in mine and x[0] not in GENERIC and x[6]:
            q[x[0]] += x[6]; a[x[0]] += x[7]
    if not q:
        raise ValueError('기타 품목: 거래가 없어요')
    def tr(n):
        w = rows.get(n + SEP + '*') or {}
        c = chg_html(a[n] / q[n], w['wa']) if w.get('wa') and (w.get('wq') or 0) >= MIN_VARIETY_QTY else '<em class="flat">-</em>'
        return f'<tr><td title="{esc(n)}">{esc(n)}</td><td>{num(a[n] / q[n])}원</td><td>{c}</td></tr>'
    names = sorted(q, key=lambda n: (-q[n], n))
    cols = '<colgroup><col class="c1"><col><col></colgroup>'
    body = f"""<div class="hero"><div>
<h1>기타 품목 경매 시세</h1>
<p class="meta">{kd(L)} 본경매 · 1속 평균 · {len(names)}개 품목</p>
</div></div>
<h2>품목별 시세</h2>
<p class="meta">거래 많은 순 · 품종·등급을 합친 평균</p>
<div class="list"><table>{cols}<thead><tr><th>품목</th><th>평균가</th><th>지난주 대비</th></tr></thead><tbody>
{chr(10).join(tr(n) for n in names)}
</tbody></table></div>
<a class="more" href="../">전체 꽃 시세 보기</a>
{other_links('others')}"""
    title = '기타 꽃 경매 시세 · 품목별 경매가 | 오늘의 양재 꽃시세'   # 제목에 날짜를 넣지 않음 (검색 결과에 옛 날짜가 남음, 2026-11-23 사용자 요청)
    desc = f'양재 화훼공판장 {kd(L)} 본경매 기타 품목 {len(names)}개의 평균 경매가와 지난주 대비. ' + ', '.join(names[:6]) + ' 등.'
    return title, desc, [('꽃시세', '../'), ('기타 품목', None)], body, L, ''


def check_others(t, snap):
    err, cat = [], snap['catalog']
    mine = {r for r, _d, _o in FLOWERS.values()}
    q, a = defaultdict(int), defaultdict(int)
    for x in cat['items']:
        if x[0] not in mine and x[0] not in GENERIC and x[6]:
            q[x[0]] += x[6]; a[x[0]] += x[7]
    got = re.findall(r'<tr><td title="([^"]+)">[^<]*</td><td>([\d,]+)원</td>', t)
    if sorted(html.unescape(n) for n, _ in got) != sorted(q): err.append('flower/others.html: 품목 목록 다름')
    for n, pr in got:
        n = html.unescape(n)
        if pr != num(a[n] / q[n]): err.append(f'flower/others.html: {n} 평균가 다름')
    return err


def flower_page(slug, raw, disp, others, snap, hist):
    meta = snap['index']['meta']
    rows = snap['index']['rows']
    top = rows.get(raw + SEP + '*')
    if not top or not top.get('lastDate'):
        raise ValueError(f'{raw}: 최근 경매 자료가 없어요')
    L = meta.get('latestDate') or ''          # 가장 최근 본경매일 (이 꽃이 거래 안 됐어도 이 날짜)
    traded = (top.get('lq') or 0) > 0 and bool(top.get('la'))
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
    if traded and sum(x[0] for x in var.values()) != top['lq']:
        raise ValueError(f"{raw}: 품종 합계 거래량과 품목 거래량 {top['lq']} 이 달라요")
    la = top['la'] if traded else None
    name_note = f' · 경매 이름 {esc(raw)}' if raw != disp else ''

    # 맨 위: 이름 · 가격 · 비교 3칸 (% 만)
    tiles = ''.join(f'<div><span>{n}</span>{chg_html(la, v).replace("<em", "<b").replace("</em>", "</b>")}</div>'
                    for n, v, q in (('지난주보다', top.get('wa'), top.get('wq')), ('2주 전보다', top.get('pa'), top.get('pq')),
                                    ('작년보다', top.get('ya'), top.get('yq'))) if traded and v and (q or 0) >= MIN_CMP_QTY)
    last = (f' · 마지막 거래 {kd(top["lastDate"])} {num(top["lastAvg"])}원' if top.get('lastAvg') and top.get('lastDate') else '')
    hero = f"""<div class="hero"><div>
<h1>{esc(disp)} 경매 시세</h1>
<p class="meta">{kd(L)} 본경매 · 1속 평균{name_note}</p>
</div>{img_tag(raw)}</div>
{f'<p class="price">{num(la)}<span>원</span></p>' if traded else f'<p class="price">거래 없음</p><p class="meta">이날 본경매에는 {esc(disp)} 거래가 없었어요{last}</p>'}
{f'<div class="tiles">{tiles}</div>' if tiles else ''}"""

    def table(head, rows_html, more=None):
        cols = '<colgroup><col class="c1"><col><col></colgroup>'
        t = f'<div class="list"><table>{cols}<thead><tr>{head}</tr></thead><tbody>\n{rows_html}\n</tbody></table>'
        if more:
            t += f'<details><summary>{more[0]}</summary><table>{cols}<tbody>\n{more[1]}\n</tbody></table></details>'
        return t + '</div>'

    # 품종: 3칸, 10개 + 더 보기
    vs = sorted(((v, q, a) for v, (q, a) in var.items() if q >= MIN_VARIETY_QTY), key=lambda x: (-x[1], x[0]))[:MAX_VARIETIES]
    def vr(v, q, a):
        w = rows.get(raw + SEP + v) or {}
        c = chg_html(a / q, w['wa']) if w.get('wa') and (w.get('wq') or 0) >= MIN_VARIETY_QTY else '<em class="flat">-</em>'
        return f'<tr><td title="{esc(v)}">{esc(v)}</td><td>{num(a / q)}원</td><td>{c}</td></tr>'
    vsec = ('' if not traded else
            f'<p class="meta">이날은 {MIN_VARIETY_QTY}속 넘게 거래된 품종이 없었어요. (전체 {num(top["lq"])}속)</p>' if not vs else
            table('<th>품종</th><th>평균가</th><th>지난주 대비</th>', '\n'.join(vr(*x) for x in vs[:10]),
                  (f'{len(vs) - 10}개 더 보기', '\n'.join(vr(*x) for x in vs[10:])) if len(vs) > 10 else None))

    def grank(g):
        m = re.match(r'(특|상|보)?\s*(\d*)', g or '')
        return ({'특': 0, '상': 1, '보': 2}.get(m.group(1), 3), int(m.group(2) or 0), g)
    gsec = '' if not traded else table('<th>등급</th><th>평균가</th><th>거래량</th>', '\n'.join(
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
    h = year_rows(hist, raw)
    yr, note = '', ''
    if h and (date.fromisoformat(max(r[0] for r in h)) - date.fromisoformat(min(r[0] for r in h))).days >= MIN_YEAR_DAYS:
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

    today = (f"""<h2>품종별 시세</h2>
<p class="meta">{kd(L)} · 거래 많은 순</p>
{vsec}
<h2>등급별 시세</h2>
<p class="meta">{kd(L)} · 모든 품종 합계</p>
{gsec}""" if traded else '')
    body = f"""{hero}
{today}
{w8}
{yr}
<a class="cta" href="../?fav={urllib.parse.quote(disp)}">{esc(disp)} 관심 꽃에 담기</a>
<a class="more" href="../">전체 꽃 시세 보기</a>
{other_links(slug)}"""
    title = f'{disp} 시세 · 오늘 {disp} 경매가와 품종별 가격 | 오늘의 양재 꽃시세'
    have = [x for x, ok in (('품종·등급별 가격', traded), ('최근 8주', bool(w8)), ('지난 1년 흐름', bool(yr))) if ok]
    desc = ((f'양재 화훼공판장 {disp} 경매 시세. {kd(L)} {disp} 평균 {num(la)}원(1속), 거래량 {num(top["lq"])}속.') if traded else
            f'양재 화훼공판장 {disp} 경매 시세. {kd(L)} 본경매에는 거래가 없었어요.') + (f' {", ".join(have)}{"을" if (ord(have[-1][-1]) - 0xAC00) % 28 else "를"} 볼 수 있어요.' if have else '')
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


def check_history(hist, snap):
    """1년 기록 자체 검사: 중복·경매 요일·숫자, 그리고 시세 파일과 겹치는 날은 거래량이 같은지."""
    err, seen = [], set()
    for d, item, q, a in hist:
        if (d, item) in seen: err.append(f'기록 중복 {d} {item}')
        seen.add((d, item))
        if date.fromisoformat(d).weekday() not in (0, 2, 4): err.append(f'월·수·금이 아닌 경매일 {d}')
        if q <= 0 or a <= 0: err.append(f'거래량·금액이 0 이하 {d} {item}')
    rows = snap['index']['rows']
    for d, item, q, a in hist:
        x = rows.get(item + SEP + '*') or {}
        if d == snap['index']['meta'].get('latestDate') and x.get('lq') != q:
            err.append(f'{d} {item} 거래량이 기록 {q} / 시세 파일 {x.get("lq")} 로 달라요')
    return err


def check_page(path, t, raw, snap, hist):
    """만든 페이지의 숫자를 원자료에서 처음부터 다시 계산해 맞춰 봐요."""
    err = []
    rows = snap['index']['rows']; meta = snap['index']['meta']
    top = rows[raw + SEP + '*']; L = meta['latestDate']
    traded = (top.get('lq') or 0) > 0 and bool(top.get('la')); la = top['la'] if traded else None
    if re.search(r'>0원', t): err.append(f'{path}: 0원 표시가 있어요 (거래 없음은 0원이 아니에요)')
    m = re.search(r'<p class="price">([\d,]+)<span>원', t)
    if traded and (not m or m.group(1) != num(la)): err.append(f'{path}: 맨 위 가격 다름')
    if not traded and (m or '<p class="price">거래 없음</p>' not in t): err.append(f'{path}: 거래가 없는데 가격을 보여 줌')
    if f'<p class="meta">{kd(L)} 본경매' not in t: err.append(f'{path}: 경매일 다름')
    want = {'지난주보다': ('wa', 'wq'), '2주 전보다': ('pa', 'pq'), '작년보다': ('ya', 'yq')}
    got = dict((n, c) for n, c in re.findall(r'<div><span>([^<]+)</span><b class="\w+">([^<]+)</b>', t))
    for n, (k, kq) in want.items():
        ok = traded and top.get(k) and (top.get(kq) or 0) >= MIN_CMP_QTY
        if ok and got.get(n) != chg(la, top[k])[0]: err.append(f'{path}: {n} % 다름')
        if not ok and n in got: err.append(f'{path}: 표본이 적은데 {n} % 를 보여 줌')
    # 품종: 순서·평균가·지난주 대비
    q, a = defaultdict(int), defaultdict(int)
    gq, ga = defaultdict(int), defaultdict(int)
    for x in (snap['catalog']['items']):
        if x[0] == raw and x[6]:
            q[x[1]] += x[6]; a[x[1]] += x[7]; gq[x[2]] += x[6]; ga[x[2]] += x[7]
    exp = sorted((v for v in q if q[v] >= MIN_VARIETY_QTY), key=lambda v: (-q[v], v))[:MAX_VARIETIES] if traded else []
    vrows = re.findall(r'<tr><td title="([^"]+)">[^<]*</td><td>([\d,]+)원</td><td><em class="\w+">([^<]+)</em></td></tr>', t)
    if [html.unescape(v) for v, _, _ in vrows] != exp: err.append(f'{path}: 품종 목록·순서 다름')
    for v, pr, c in vrows:
        v = html.unescape(v); w = rows.get(raw + SEP + v) or {}
        if pr != num(a[v] / q[v]): err.append(f'{path}: {v} 평균가 다름')
        ec = chg(a[v] / q[v], w['wa'])[0] if w.get('wa') and (w.get('wq') or 0) >= MIN_VARIETY_QTY else '-'
        if c != ec: err.append(f'{path}: {v} 지난주 대비 다름 ({c} / {ec})')
    # 등급
    for g, pr, qq in re.findall(r'<tr><td>([특상보][^<]*)</td><td>([\d,]+)원</td><td>([\d,]+)속</td></tr>', t):
        if pr != num(ga[g] / gq[g]) or qq != num(gq[g]): err.append(f'{path}: 등급 {g} 다름')
    # 8주 마지막 값
    tr = [v for v in top.get('trend') or [] if v]
    if tr and f'>{num(tr[-1])}원</text>' not in t: err.append(f'{path}: 8주 마지막 주 값 다름')
    # 1년 달별
    h = year_rows(hist, raw)
    mq, ma = defaultdict(int), defaultdict(int)
    for d, _, qq, aa in h: mq[d[:7]] += qq; ma[d[:7]] += aa
    months = re.findall(r'<tr><td>(\d+)년 (\d+)월[^<]*</td><td>([\d,]+)원</td><td>([\d,]+)속</td></tr>', t)
    span = (date.fromisoformat(max(r[0] for r in h)) - date.fromisoformat(min(r[0] for r in h))).days if h else 0
    if months and span < MIN_YEAR_DAYS: err.append(f'{path}: 기록이 1년이 안 되는데 1년 흐름을 보여 줌')
    if span >= MIN_YEAR_DAYS and len(months) != len(mq): err.append(f'{path}: 달 수 다름')
    for y, mo, pr, qq in months:
        k = f'20{int(y):02d}-{int(mo):02d}'
        if pr != num(ma[k] / mq[k]) or qq != num(mq[k]): err.append(f'{path}: {k} 달별 값 다름')
    return err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only')
    a = ap.parse_args()
    slugs = [s.strip() for s in a.only.split(',')] if a.only else list(FLOWERS)
    try:
        snap = json.load(open(os.path.join(ROOT, 'data', 'snapshot.json'), encoding='utf-8'))
        hist = load_history()
    except Exception as e:
        print('시세 파일·기록을 읽지 못해 꽃별 페이지 건너뜀 (파일 그대로):', e)
        return 0
    texts = {}
    try:
        for s in slugs:
            raw, disp, others = FLOWERS[s]
            title, desc, crumbs, body, changed, note = flower_page(s, raw, disp, others, snap, hist)
            texts[f'flower/{s}.html'] = page(f'flower/{s}.html', title, desc, crumbs, body, changed, note)
    except (ValueError, KeyError, TypeError) as e:
        print('꽃별 페이지 건너뜀 (파일 그대로):', e)
        return 0
    if not a.only:
        try:
            t, d, c, b, L, n = others_page(snap)
            texts['flower/others.html'] = page('flower/others.html', t, d, c, b, L, n)
        except (ValueError, KeyError, TypeError) as e:
            print('기타 품목 페이지 건너뜀 (파일 그대로):', e)
            return 0
        sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
              f'  <url><loc>{BASE}</loc></url>']
        changed_day = snap['index']['meta'].get('latestDate') or ''
        sm += [f'  <url><loc>{BASE}{p}</loc><lastmod>{changed_day}</lastmod></url>' for p in sorted(texts)]
        texts['sitemap.xml'] = '\n'.join(sm + ['</urlset>']) + '\n'
    # 검사: 페이지 하나가 걸리면 그 페이지만 이전 것을 두고 나머지는 갱신. 기록·사이트맵 문제는 전부 멈춤
    page_err = defaultdict(list)
    for e in verify({k: v for k, v in texts.items() if k.endswith('.html')}):
        page_err[e.split(':')[0]].append(e)
    if 'flower/others.html' in texts:
        for e in check_others(texts['flower/others.html'], snap): page_err['flower/others.html'].append(e)
    for s in slugs:
        p = f'flower/{s}.html'
        if p in texts: page_err[p] += check_page(p, texts[p], FLOWERS[s][0], snap, hist)
    bad = sorted(p for p, e in page_err.items() if e)
    for p in bad:
        print('\n'.join(page_err[p]))
        print(f'{p} 는 검사에 걸려 이전 페이지를 그대로 둬요')
        texts.pop(p, None)
    if len(bad) > max(3, len(slugs) // 5):
        print(f'검사에 걸린 페이지가 {len(bad)}개로 많아요. 자료 문제일 수 있어 아무것도 바꾸지 않았어요')
        return 0
    err = check_history(hist, snap)
    if 'sitemap.xml' in texts:
        for u in re.findall(r'<loc>([^<]+)</loc>', texts['sitemap.xml']):
            r = u[len(BASE):] or 'index.html'
            if r not in texts and not os.path.exists(os.path.join(ROOT, r)): err.append(f'사이트맵 주소에 파일 없음: {u}')
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
