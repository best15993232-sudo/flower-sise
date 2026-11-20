# 경매 기록을 data/history/ 에 이어 쌓습니다. (시세 서버는 최근 8주만 들고 있어서, 안 쌓으면 지나간 날이 사라집니다)
#
# 쌓는 것 (한 달에 파일 하나씩)
# - items-YYYY-MM.csv  : 경매일 × 품목 합계 (경매일, 품목, 거래량(속), 거래금액(원), 품종 수)
# - detail-YYYY-MM.csv : 경매일 × 품목 × 품종 × 등급 (평균가·최고가·최저가·거래량·거래금액)
#
# 규칙
# - 집계가 끝난 본경매일만 (시세 파일 meta.dates 에서 m=본경매, p=집계 중 아님, 진행 중인 날 제외).
# - 이미 있는 날은 덮어쓰지 않습니다. 단 가장 최근 경매일은 같은 날 늦게 고쳐진 자료를 반영합니다.
# - 시세 파일에 없는 날(최근 8주 안)은 시세 서버에 그날 자료를 물어 채웁니다.
#   시세 서버는 8주보다 오래된 날을 물으면 최근 날 자료를 돌려주므로, 받은 날짜가 물은 날짜와 같은지 꼭 확인합니다.
# - 이상한 자료(품목 50개 미만, 월·수·금이 아님, 날짜 다름)는 쓰지 않습니다. 실패해도 다른 날·시세 파일 저장은 계속됩니다.
import csv, json, os, re, sys, time, urllib.parse, urllib.request
from collections import defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(ROOT, 'data', 'history')
ITEM_HEAD = ['경매일', '품목', '거래량(속)', '거래금액(원)', '품종 수']
DETAIL_HEAD = ['경매일', '품목', '품종', '등급', '평균가', '최고가', '최저가', '거래량(속)', '거래금액(원)']
MAX_FETCH = 30          # 한 번에 시세 서버에 묻는 날 수 (처음 8주 채우기 24일 정도)
MIN_ITEMS = 50


def api():
    cfg = open(os.path.join(ROOT, 'js', 'config.js'), encoding='utf-8').read()
    return re.search(r"https://script\.google\.com/macros/s/[^'\"]+/exec", cfg).group(0)


def catalog_day(d):
    url = api() + '?' + urllib.parse.urlencode({'api': 'getCatalogDay', 'args': json.dumps([d])})
    last = None
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'flower-sise-history'})
            with urllib.request.urlopen(req, timeout=90) as r:
                j = json.loads(r.read().decode('utf-8'))
            if not j.get('ok'):
                raise RuntimeError(j.get('error'))
            return j['data']
        except Exception as e:
            last = e
            time.sleep(3 * (i + 1))
    raise RuntimeError(f'{d} 받기 실패: {last}')


def read(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        r = csv.reader(f)
        next(r, None)
        return [row for row in r if row]


def write(path, head, rows):
    with open(path + '.tmp', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(head)
        w.writerows(rows)
    os.replace(path + '.tmp', path)


def ok_catalog(c, d):
    """그날 자료가 맞고 쓸 만한지. 아니면 이유를 돌려줌"""
    if not c or c.get('date') != d:
        return f"받은 날짜 {c and c.get('date')} 가 {d} 와 달라요"
    if c.get('partial') or c.get('main') is False:
        return '집계 중이거나 본경매가 아니에요'
    if date.fromisoformat(d).weekday() not in (0, 2, 4):
        return '월·수·금이 아니에요'
    items = [x for x in c.get('items') or [] if len(x) >= 8 and x[6]]
    if len({x[0] for x in items}) < MIN_ITEMS:
        return f'품목이 {len({x[0] for x in items})}개뿐이에요'
    return ''


def rows_of(c, d):
    det, q, a, v = [], defaultdict(int), defaultdict(int), defaultdict(set)
    for x in c['items']:
        if len(x) < 8 or not x[6]:
            continue
        item, var, grade, avg, mx, mn, qty, amt = x[:8]
        det.append([d, item, var, grade, int(avg), int(mx), int(mn), int(qty), int(amt)])
        q[item] += int(qty); a[item] += int(amt); v[item].add(var)
    det.sort(key=lambda r: (r[1], r[2], r[3]))
    items = sorted([[d, k, q[k], a[k], len(v[k])] for k in q], key=lambda r: r[1])
    return items, det


def main():
    try:
        snap = json.load(open(os.path.join(ROOT, 'data', 'snapshot.json'), encoding='utf-8'))
        meta = snap['index']['meta']
    except Exception as e:
        print('시세 파일을 읽지 못해 기록 건너뜀:', e)
        return 0
    latest, busy = meta.get('latestDate') or '', meta.get('inProgressDate') or ''
    days = sorted({x['d'] for x in meta.get('dates') or [] if x.get('m') and not x.get('p') and x.get('d') != busy})
    os.makedirs(H, exist_ok=True)
    added, fetched, notes = [], 0, []
    for d in days:
        ym = d[:7]
        ip, dp = os.path.join(H, f'items-{ym}.csv'), os.path.join(H, f'detail-{ym}.csv')
        irows, drows = read(ip), read(dp)
        have_i = any(r[0] == d for r in irows)
        have_d = any(r[0] == d for r in drows)
        if have_i and have_d and d != latest:
            continue
        cat = snap.get('catalog') if (snap.get('catalog') or {}).get('date') == d else None
        if cat is None:
            if have_d or fetched >= MAX_FETCH:
                continue
            try:
                cat = catalog_day(d); fetched += 1
            except Exception as e:
                notes.append(str(e)); continue
        why = ok_catalog(cat, d)
        if why:
            notes.append(f'{d}: {why}'); continue
        items, det = rows_of(cat, d)
        new_i = [[str(x) for x in r] for r in items]
        new_d = [[str(x) for x in r] for r in det]
        old_i = [r for r in irows if r[0] == d]
        old_d = [r for r in drows if r[0] == d]
        # 품목 합계: 없으면 더하고, 있으면 최근 경매일만 고침. 지난날은 그대로 두되 다르면 알림
        if not old_i or (d == latest and old_i != new_i):
            irows = [r for r in irows if r[0] != d] + new_i
            irows.sort(key=lambda r: (r[0], r[1]))
            write(ip, ITEM_HEAD, irows); added.append(f'{d} 품목 {len(new_i)}')
        elif old_i != new_i:
            notes.append(f'{d}: 이미 있는 품목 합계와 서버 자료가 달라 그대로 둠')
        if not old_d or (d == latest and old_d != new_d):
            drows = [r for r in drows if r[0] != d] + new_d
            drows.sort(key=lambda r: (r[0], r[1], r[2], r[3]))
            write(dp, DETAIL_HEAD, drows); added.append(f'{d} 품종·등급 {len(new_d)}')
    for n in notes:
        print('기록 참고:', n)
    print('기록 더함:', ', '.join(added) if added else '없음', f'(서버에 물은 날 {fetched}일)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
