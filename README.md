# 꽃시세

양재 aT 화훼공판장 절화 경매 시세를 지난주와 비교해서 보여 주는 페이지입니다.

- 사이트: https://best15993232-sudo.github.io/flower-sise/
- 자료: 한국농수산식품유통공사 화훼유통정보시스템(flower.at.or.kr), 양재 aT 화훼공판장 절화 경매 결과

## 구조

- `index.html` 사이트 화면 전체
- `js/config.js` 시세를 받아 오는 Apps Script 웹 앱 주소
- `data/snapshot.json` 첫 화면용 시세 파일 (자동 생성, 직접 고치지 않음)
- `img/flowers/` 꽃 그림 (원본 저장소에서 자동으로 가져옴, 직접 고치지 않음)

## 자동 작업 (Actions)

- 시세 파일 미리 만들기: 한국 시간 6~11시 15분마다, 그 밖에는 1시간마다
- 꽃 그림 가져오기: 하루 한 번. 원본은 공개 저장소 Verdus927/kkot-sise

## 시세 서버

구글 시트에 붙은 Apps Script 입니다. 경매 자료를 받아 시세를 미리 계산해 두고, 사이트가 웹 앱 주소로 읽어 갑니다.
aT 서비스키는 Apps Script 스크립트 속성 `AT_API_KEY` 에만 있습니다. 이 저장소는 공개이므로 키를 올리지 마세요.
