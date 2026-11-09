# 꽃시세 사이트 인수인계 (팀 Claude용)

이 저장소에서 일하는 Claude가 처음에 읽는 문서입니다. 사이트 주인은 '사용자'라고 부릅니다.
사용자에게는 한국어로, 쉬운 말로 답합니다. 문장에 em dash 기호(긴 줄표)를 쓰지 않습니다.
사용자에게 넘기는 글(문구, 지시서 등)은 복사하기 쉽게 코드 블록에 넣습니다.

## 1. 한눈에

- 사이트: https://best15993232-sudo.github.io/flower-sise/
- 하는 일: 양재 aT 화훼공판장 절화 경매 시세를 지난주와 비교해서 꽃집 사장님들에게 보여 줌
- 자료 출처: 한국농수산식품유통공사 화훼유통정보시스템 오픈API
- 수익: 광고 자리(월 3만원). 문의는 구글 폼으로 받음
- 이 팀 사이트가 기준입니다. 화면 디자인이나 기능을 고칠 때는 이 저장소만 고칩니다.
  같은 화면의 개인 사이트(Verdus927/kkot-sise)는 기록용이라 따라 고치지 않습니다.

## 2. 전체 흐름

```
aT 오픈API
  → 구글 시트 Apps Script (경매 자료 받기, 시세 미리 계산)
  → 웹 앱 주소 (?api=...)
  → GitHub Actions가 data/snapshot.json 으로 저장
  → 사이트가 snapshot.json 을 먼저 보여 주고, 웹 앱에 더 새 시세가 있으면 알려 줌

꽃 그림: 개인 저장소 Verdus927/kkot-sise 에서 만듦
  → 이 저장소의 '꽃 그림 가져오기' 작업이 매일 새 그림만 복사해 옴
```

## 3. 시세 서버 (구글 시트 + Apps Script)

- 스프레드시트 (팀 구글 계정): https://docs.google.com/spreadsheets/d/11KsmH-FnXVe0QXAGwHX3x0XHGwuCdUkeVFDl0Z9o_js/edit
- 웹 앱 주소: `js/config.js` 의 `API_URL`
- 스크립트 파일 5개
  - `Setup.gs`: 처음 설치(`setupAll`, 자동으로 이어서 진행, 상태는 설정 탭 27행), 자동 실행 걸기(`installAllTriggers`)
  - `Auction.gs`: aT에서 경매 자료 받기. 원자료 10블록, 추이원자료 24블록(8주), 이번주원자료 3블록
  - `PriceIndex.gs`: 모든 품목·품종 시세를 '시세집계' 탭에 미리 계산. 사이트가 읽는 `getPriceIndex`, `getCatalogDay`
  - `Api.gs`: 사이트 창구(`doGet`). 읽기 함수 4개만 열려 있음(`getDashboardData`, `getPriceIndex`, `getCatalogDay`, `getFlowerNews`). 첫 화면 주요 품목 목록 `DASH_MAIN`
  - `News.gs`: 구글 뉴스에서 꽃 시장 기사 찾기 (6시간 저장)
- 스크립트 속성: `AT_API_KEY` (aT 서비스키). 이 값은 어디에도 옮겨 적지 않습니다.
- 자동 실행 (서울 시간)
  - `updateTodayOnly`: 매일 8, 11, 14, 18시. 오늘 경매와 이번 주 경매
  - `fridayPublishWeek`: 금요일 12시, 16시. 이번 주를 '기준주'로 확정 (설정 B22)
  - `weeklyUpdate`: 월요일 5시. 원자료·추이 다시 받기 (금요일 확정이 실패했을 때 안전장치)
  - 시세 집계는 자료를 받은 뒤 1분 뒤에 따로 돔 (`piDeferredRefresh`)
- 설정 탭: B5 기준일, C8~C17 비교 날짜(이번 주, 지난주, 작년 같은 주, 오늘), 18~25행 마지막 갱신 시각과 상태, 27행 처음 설치 상태
- 배포 규칙: 코드를 고친 뒤에는 **배포 > 배포 관리 > 수정(연필) > 버전 '새 버전'** 으로 올립니다.
  '새 배포'를 누르면 주소가 바뀌어 사이트가 끊깁니다. 웹 앱 액세스는 '모든 사용자' 그대로 둡니다.
- 스프레드시트 파일 공유는 '제한됨'으로 둡니다. 웹 앱은 팀 계정 권한으로 돌아서 사이트에는 영향이 없습니다.

## 4. 이 저장소

- `index.html`: 화면 전체 (HTML, CSS, JS 한 파일)
- `js/config.js`: 웹 앱 주소, `js/api.js`: 웹 앱 호출
- `data/snapshot.json`: 첫 화면용 시세 파일. **자동 생성, 손으로 고치지 않음**
- `img/flowers/`: 꽃 그림. **'꽃 그림 가져오기'가 관리, 손으로 고치지 않음**
- `tools/snapshot.py`: snapshot.json 만드는 스크립트
- `sw.js`, `manifest.webmanifest`: 홈 화면 추가용

자동 작업 (`.github/workflows`, 둘 다 같은 concurrency 그룹이라 겹치지 않음)
- `snapshot.yml` 시세 파일 미리 만들기: 서울 6~11시 15분마다, 그 밖에는 1시간마다. 내용이 바뀌었을 때만 커밋
- `sync-flowers.yml` 꽃 그림 가져오기: 매일 서울 5시 20분. 새 그림과 바뀐 그림만 복사, 지우지 않음, .webp 3MB 이하만. 그림 목록 `FLOWER_IMG` 를 img/flowers 파일 이름으로 다시 만듦

자동 작업이 수시로 커밋하므로, 고치기 전에 항상 `git pull` 합니다.

index.html 에서 자주 보는 곳
- 첫 화면 주요 품목: `FIXED_MAIN` (1년 내내 많이 거래되는 꽃·소재 고정) + `WEEK_PICK` (그 주 많이 거래된 품목), `WEEK_SKIP` (뭉뚱그린 이름 제외)
- 품목 다른 이름으로 검색: `DISP`, `ALIAS`, `MAIN_ALIAS`
- 관심 꽃: 방문자 브라우저의 localStorage `yangjaeFav2`
- 첫 화면: `SNAP_URL` 로 snapshot.json 을 먼저 그리고, `checkLatest` 로 더 새 시세가 있는지 확인. 사용자가 읽는 도중에는 화면을 바꾸지 않고 '새 시세가 올라왔어요 [새로 보기]' 띠만 보여 줌
- 광고: `AD_FORM_URL` 하나로 세 곳(하단, 계절 카드, 시장 소식 아래 카드)이 함께 연결됨
- `SHOW_PARTNER_LINKS` 는 false 그대로 둠 (다른 사이트 연결 안 함)

## 5. 꽃 그림과 제작 대장

- 꽃 그림은 이 저장소에서 만들지 않습니다. 이 저장소에는 OpenAI 키가 없고, 넣지도 않습니다.
- 새 품목에 그림이 필요하면 사용자에게 알리기만 합니다. 그림은 개인 쪽에서 만들어 Verdus927/kkot-sise 에 올라가고, 다음 날 새벽 자동으로 이쪽에 들어옵니다.
  급하면 Actions 탭에서 '꽃 그림 가져오기'를 수동 실행합니다.
- 파일 이름 = aT 원자료 품목명 + .webp (예: `국화_대국.webp` 는 대국 품종용)
- 제작 대장 (팀 구글 계정): https://docs.google.com/spreadsheets/d/1aulg3n-fAZ3ey1VAroeX6hRWhQHXO8XKRem2X-asthQ/edit
  - 이 파일이 진짜 대장입니다. '작성 규칙' 탭을 따릅니다.
  - 제작 비용 참고: 자동 제작 장당 약 $0.07 (약 100원)

## 6. 광고

- 광고 문의 구글 폼은 `index.html` 의 `AD_FORM_URL` 에 이미 연결됨(2026-11-09). 폼 주소가 바뀔 때만 고침
- 광고가 잡히면 사용자가 광고 이미지와 연결 주소를 줍니다. 시작일과 끝일을 사용자에게 확인합니다.
- 배너 넣는 방법
  - 파일: `img/ads/` 에 넣습니다. 가로 1440 x 세로 480 px (3:1), JPG 또는 PNG, 500KB 이하. 이름 예: `img/ads/가게이름-2026-12.jpg`
  - 설정: `index.html` 의 `const AD={img:'', link:'', until:''};` 한 줄만 고칩니다.
    `img` 배너 파일 경로, `link` 누르면 갈 주소, `until` 끝나는 날(YYYY-MM-DD, 서울 기준, 그날까지 보임)
  - 배너는 메인 페이지 시장 소식 아래와 시장 소식 탭 두 곳에 같이 나오고, 왼쪽 위에 작게 '광고' 표시가 붙습니다.
  - `img` 가 비어 있거나 `until` 이 지나면 자동으로 '이 자리에 광고를 실어 보세요' 문의 카드로 돌아갑니다.
    `until` 을 비우면 끝나지 않으므로 꼭 넣습니다.
  - 광고 시작일에 맞춰 올립니다(미리 올리면 바로 보입니다). 끝난 뒤 `AD` 를 비우고 배너 파일은 지워도 됩니다.
- 폼 응답 알림은 구글 폼 '새 응답 이메일 알림'으로 받습니다. 별도 스크립트는 만들지 않습니다.
- 개인정보처리방침: `privacy.html` (하단 링크). 폼의 수집 항목, 목적, 보유 기간이 바뀌면 이 페이지도 같이 고치고 시행일을 바꿉니다. 보호책임자 연락처는 사용자가 정한 이메일입니다.

## 7. 방문자 통계

- Cloudflare Web Analytics (사용자 계정). 코드는 index.html 맨 아래, 토큰은 공개 값이라 저장소에 있어도 됩니다.
- 같은 주소(best15993232-sudo.github.io) 아래 다른 사이트(flower-planner)와 한 곳에 합쳐 집계됩니다.
  꽃시세만 보려면 Visits > Path 탭에서 `/flower-sise/` 로 나눠 봅니다.

## 8. aT 오픈API 키

- 화훼유통정보시스템(flower.at.or.kr) 오픈API '화훼가격정보', 일자별 경매정보, 일일 3,000건 (실제 사용은 하루 20~30건)
- 승인일 2026-11-06, 활용기간 20개월 → **2028-07-06 무렵 만료**
- 만료 한 달 전(2028-06 초)에 사용자에게 재신청을 알립니다. 새 키는 Apps Script 스크립트 속성 `AT_API_KEY` 값만 바꾸면 됩니다.
- 이용 조건 '제작자 표시': 사이트 하단의 출처 문구(한국농수산식품유통공사 화훼유통정보시스템)를 지우지 않습니다.

## 9. 하면 안 되는 것

- 비밀 값(aT 키, OpenAI 키 등)을 저장소, 코드, 커밋 메시지, 대화에 적지 않습니다. 이 저장소는 공개입니다.
- 사이트에 회사 이름, 회사 연락처, 다른 사이트 연결을 넣지 않습니다. 꽃집 카페 등에 올리는 중립 사이트입니다.
- `data/snapshot.json`, `img/flowers/`, `FLOWER_IMG` 목록을 손으로 고치지 않습니다.
- Apps Script 는 '새 배포' 대신 '배포 관리 > 새 버전'으로 올립니다.
- 사용자 관련 실명이나 직책을 문서에 적지 않습니다. '사용자'로만 씁니다.

## 10. 문제가 생겼을 때

- 시세가 안 바뀜: 스프레드시트 설정 탭 18~25행 시각과 상태 확인 → Apps Script 왼쪽 '실행' 기록에서 실패한 함수 확인
- 금요일 확정이 안 됨 (설정 23행이 '완료'가 아님): 금요일 11시 이후 `fridayPublishWeek` 수동 실행
- 추이원자료가 비었거나 이상함: 메뉴 '경매 데이터 > 추이원자료 처음부터 다시 받기' 후 '이어서 받기'를 끝날 때까지
- 처음부터 다시 설치: `resetSetup` 실행 후 `setupAll`
- Actions 가 403 으로 실패: 저장소 Settings > Actions > General > Workflow permissions 를 'Read and write' 로
- 웹 앱 동작 확인: `API_URL?api=getDashboardData` 를 열면 `{"ok":true,...}` 가 나와야 함

## 검색 등록 (구글·네이버·다음)

- 2026-11-09 세 곳 모두 등록 끝. 맨 위 주소 `https://best15993232-sudo.github.io` 로 한 번 등록해서 두 사이트(flower-planner, flower-sise)가 같이 들어가 있음
- 소유 확인 태그(구글·네이버)와 `robots.txt`(다음 PIN, 사이트맵 주소)는 **`best15993232-sudo/best15993232-sudo.github.io` 저장소**에서 관리. 이 저장소에서는 고치지 않음
- `robots.txt` 는 두 사이트만 허용하고 같은 주소 아래 다른 사이트는 막음. 다른 사이트를 검색에 내보내려면 그 저장소의 robots.txt 에 `Allow:` 줄과 `Sitemap:` 줄을 더함
- 이 저장소의 `sitemap.xml` 과 `<link rel="canonical">` 은 지우지 않음. 새 페이지를 만들면 sitemap.xml 에 추가
