# 아주대 메뉴 카카오톡 챗봇

아주대학교 기숙사식당과 교직원식당의 점심/저녁 메뉴를 매일 정오에 자동으로 전송하는 카카오톡 챗봇입니다.

## 주요 기능

- **자동 메뉴 배포**: 매일 정오(12:00)에 당일 점심 메뉴 자동 전송
- **병렬 메뉴 조회**: 기숙사식당과 교직원식당 메뉴를 동시에 빠르게 조회
- **메뉴 필터링**: 불필요한 안내문구 제거하고 깔끔한 메뉴 정보만 제공
- **대화형 챗봇**: 사용자가 '메뉴' 입력 시 실시간 메뉴 조회
- **웹 API**: REST API를 통한 메뉴 조회 및 수동 전송 가능

##  사전 준비사항

### 1. 카카오 개발자 계정 및 앱 등록
1. [카카오 개발자 콘솔](https://developers.kakao.com/)에서 계정 생성
2. 새 애플리케이션 생성
3. **REST API 키** 발급
4. **카카오톡 메시지 API** 활성화
5. **플랫폼 설정**에서 웹 플랫폼 추가 및 도메인 등록

### 2. 카카오톡 채널 생성 (선택사항)
1. [카카오톡 채널 관리자센터](https://center-pf.kakao.com/)에서 채널 생성
2. **채널 UUID** 발급

### 3. 서버 환경
- Python 3.8 이상
- 외부에서 접근 가능한 웹서버 (웹훅용)
- HTTPS 지원 권장

##  설치 및 설정

### 1. 프로젝트 설치
```bash
# 프로젝트 클론
git clone <repository-url>
cd kakao_menu_bot

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정
```bash
# .env 파일 생성
cp .env.example .env
```

`.env` 파일을 편집하여 다음 정보를 입력:
```env
# 카카오톡 채널 설정
KAKAO_REST_API_KEY=your_kakao_rest_api_key
KAKAO_ADMIN_KEY=your_kakao_admin_key
KAKAO_CHANNEL_UUID=your_channel_uuid

# 서버 설정
FLASK_PORT=5000
FLASK_DEBUG=False

# 메뉴 알림 설정
NOTIFICATION_TIME=12:00
TIMEZONE=Asia/Seoul
```

### 3. 카카오톡 개발자 콘솔 설정
1. **내 애플리케이션** > **앱 설정** > **플랫폼**
   - 웹 플랫폼 추가
   - 사이트 도메인: `https://your-domain.com`

2. **제품 설정** > **카카오 로그인**
   - 활성화 설정: ON
   - Redirect URI: `https://your-domain.com/oauth`

3. **제품 설정** > **카카오톡 메시지**
   - 활성화 설정: ON
   - 웹훅 URL: `https://your-domain.com/webhook`

## 실행 방법

### 개발 환경에서 실행
```bash
python app.py
```

### 프로덕션 환경에서 실행
```bash
# gunicorn 설치
pip install gunicorn

# gunicorn으로 실행
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## API 엔드포인트

### 1. 메뉴 조회
```
GET /menu?date=2025-09-10
```
특정 날짜의 메뉴를 조회합니다.

### 2. 수동 메뉴 전송
```
POST /send-menu
Content-Type: application/json

{
  "date": "2025-09-10"
}
```

### 3. 상태 체크
```
GET /health
```

### 4. 스케줄러 제어
```
POST /schedule/start  # 스케줄러 시작
POST /schedule/stop   # 스케줄러 중지
```

## 사용 방법

### 1. 자동 메뉴 배포
- 서버 실행 후 매일 설정된 시간(기본 12:00)에 자동으로 메뉴가 전송됩니다.
- `.env` 파일의 `NOTIFICATION_TIME`에서 시간 변경 가능

### 2. 수동 메뉴 전송
```bash
curl -X POST http://localhost:5000/send-menu \
  -H "Content-Type: application/json" \
  -d '{"date": "2025-09-10"}'
```

### 3. 카카오톡 챗봇 사용
사용자가 카카오톡에서 다음과 같이 입력하면 메뉴를 확인할 수 있습니다:
- "메뉴"
- "식단"
- "밥"
- "점심"

## 프로젝트 구조

```
kakao_menu_bot/
├── app.py              # Flask 웹서버 메인 파일
├── menu_scraper.py     # 아주대 메뉴 스크래핑 모듈
├── kakao_api.py        # 카카오톡 API 연동 모듈
├── scheduler.py        # 자동 메뉴 전송 스케줄러
├── requirements.txt    # 의존성 목록
├── .env.example        # 환경변수 템플릿
└── README.md          # 프로젝트 설명서
```

## 문제 해결

### 1. 카카오톡 API 오류
- REST API 키가 올바른지 확인
- 애플리케이션의 카카오톡 메시지 API가 활성화되어 있는지 확인
- 플랫폼 도메인이 올바르게 설정되어 있는지 확인

### 2. 메뉴 조회 실패
- 아주대 웹사이트 접근이 가능한지 확인
- 네트워크 연결 상태 확인
- HTML 구조 변경 여부 확인

### 3. 스케줄러 작동 안함
- 서버가 지속적으로 실행되고 있는지 확인
- 시간대(TIMEZONE) 설정이 올바른지 확인
- 로그에서 오류 메시지 확인

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 기여하기

버그 리포트나 기능 제안은 GitHub Issues를 통해 해주시기 바랍니다.

## 주의사항

- 카카오톡 API 사용량 제한을 확인하고 사용하세요
- 아주대 웹사이트의 robots.txt를 준수하여 적절한 요청 간격을 유지하세요
- 개인정보 처리에 주의하여 사용자 정보를 안전하게 관리하세요
