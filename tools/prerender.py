# 첫 화면 시세 표를 index.html 안에 미리 넣습니다 (검색 로봇이 처음 받는 글자에 꽃 이름·가격이 들어가게).
#
# 방법: 사이트 화면을 크롬(창 없이)으로 열어 data/snapshot.json 으로 그린 결과를 그대로 가져와
#       index.html 의 <!--pre:ID--> ... <!--/pre--> 자리에 넣습니다. 화면과 같은 코드로 그리므로 모양·숫자가 같습니다.
#       인터넷은 막고(시세 서버에 묻지 않음) 이 저장소 파일만으로 그립니다.
# 안전: 크롬 실패, 결과가 비었거나 이상하면 index.html 을 건드리지 않고 끝냅니다 (이전 표 유지).
#       내용이 같으면 파일을 다시 쓰지 않습니다. 경매일이 바뀌거나 그 경매일 숫자가 바뀔 때만 바뀝니다.
import functools, html, http.server, json, os, re, shutil, socket, subprocess, sys, tempfile, threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')
IDS = ['dayTitle', 'daySub', 'summary', 'rises', 'falls', 'todayItems']


def chrome():
    for c in (os.environ.get('CHROME'), shutil.which('google-chrome'), shutil.which('chromium'),
              shutil.which('chromium-browser'), '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome'):
        if c and os.path.exists(c):
            return c
    return None


def serve():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    h = functools.partial(Quiet, directory=ROOT)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def render():
    exe = chrome()
    if not exe:
        raise RuntimeError('크롬을 찾지 못했어요')
    srv, port = serve()
    prof = tempfile.mkdtemp()
    try:
        out = subprocess.run([exe, '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
                              f'--user-data-dir={prof}', '--window-size=390,844',
                              '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1',   # 인터넷 막기
                              '--virtual-time-budget=20000', '--dump-dom',
                              f'http://127.0.0.1:{port}/index.html?prerender=1'],
                             capture_output=True, text=True, timeout=120)
    finally:
        srv.shutdown(); shutil.rmtree(prof, ignore_errors=True)
    m = re.search(r'<pre id="__prerender"[^>]*>(.*?)</pre>', out.stdout, re.S)
    if not m:
        raise RuntimeError('화면에서 미리 그린 결과를 찾지 못했어요')
    return json.loads(html.unescape(m.group(1)))


def check(o):
    snap = json.load(open(os.path.join(ROOT, 'data', 'snapshot.json'), encoding='utf-8'))
    latest = ((snap.get('index') or {}).get('meta') or {}).get('latestDate') or ''
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', o.get('date') or ''):
        raise RuntimeError(f"경매일이 이상해요: {o.get('date')!r}")
    if latest and o['date'] > latest:
        raise RuntimeError(f"경매일 {o['date']} 이 시세 파일 날짜 {latest} 보다 늦어요")
    rows = o['todayItems'].count('class="row')
    if rows < 5 or '원' not in o['todayItems']:
        raise RuntimeError(f'주요 품목이 {rows}줄뿐이에요')
    for i in IDS:
        if '<!--' in o[i] or 'sk"' in o[i]:
            raise RuntimeError(f'{i} 에 불러오는 중 모양이나 주석이 섞였어요')


def inject(src, o):
    for i in IDS:
        pat = re.compile(r'(<!--pre:' + i + r'-->)(.*?)(<!--/pre-->)', re.S)
        if len(pat.findall(src)) != 1:
            raise RuntimeError(f'index.html 에 {i} 자리 표시가 하나가 아니에요')
        src = pat.sub(lambda m: m.group(1) + o[i] + m.group(3), src)
    return src


def main():
    try:
        o = render()
        check(o)
        src = open(INDEX, encoding='utf-8').read()
        new = inject(src, o)
    except Exception as e:
        print('미리 넣기 건너뜀 (index.html 그대로):', e)
        return 0          # 시세 파일 저장은 계속되게 실패로 끝내지 않아요
    if new == src:
        print('미리 넣은 표 그대로', o['date'])
        return 0
    with open(INDEX + '.tmp', 'w', encoding='utf-8') as f:
        f.write(new)
    os.replace(INDEX + '.tmp', INDEX)
    print('미리 넣은 표 바꿈', o['date'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
