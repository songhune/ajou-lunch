from flask import Flask, request, jsonify, abort
from dotenv import load_dotenv
import os
import json
import requests
from datetime import datetime
import logging
import hashlib
import secrets
from functools import wraps
import ipaddress

from menu_scraper import format_menu_for_kakao
from kakao_api import KakaoAPI, KakaoChannelAPI
from scheduler import MenuScheduler

# 환경변수 로드
load_dotenv()

app = Flask(__name__)

# Flask JSON 한글 설정
app.config['JSON_AS_ASCII'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))

# 보안 헤더 추가
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    return response

# 보안 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask 요청별 로깅을 위한 커스텀 로거
def log_with_ip(message, level='info'):
    """IP 주소와 함께 로깅하는 함수"""
    try:
        if request:
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            if client_ip:
                client_ip = client_ip.split(',')[0].strip()
            formatted_message = f"{message} - IP: {client_ip}"
        else:
            formatted_message = message
    except:
        formatted_message = message
    
    if level == 'info':
        logger.info(formatted_message)
    elif level == 'warning':
        logger.warning(formatted_message)
    elif level == 'error':
        logger.error(formatted_message)

# 허용된 IP 대역 (필요에 따라 수정)
ALLOWED_IP_RANGES = [
    '127.0.0.0/8',      # localhost
    '10.0.0.0/8',       # 사설 IP
    '172.16.0.0/12',    # 사설 IP
    '192.168.0.0/16',   # 사설 IP
    '210.107.197.0/24', # 현재 서버 대역
]

# 관리자 전용 엔드포인트를 위한 API 키
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', secrets.token_hex(32))

def check_ip_whitelist():
    """IP 화이트리스트 검사"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            if client_ip:
                client_ip = client_ip.split(',')[0].strip()
            
            # 허용된 IP 대역 확인
            allowed = False
            try:
                client_addr = ipaddress.ip_address(client_ip)
                for ip_range in ALLOWED_IP_RANGES:
                    if client_addr in ipaddress.ip_network(ip_range):
                        allowed = True
                        break
            except ValueError:
                logger.warning(f"Invalid IP address: {client_ip}")
                abort(403)
            
            if not allowed:
                log_with_ip(f"Access denied for IP: {client_ip}", 'warning')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_admin_key():
    """관리자 API 키 검증"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-Admin-Key') or request.args.get('admin_key')
            
            if not api_key or api_key != ADMIN_API_KEY:
                log_with_ip("Unauthorized admin access attempt", 'warning')
                abort(401)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_request():
    """요청 로깅"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            log_with_ip(f"Request: {request.method} {request.path}", 'info')
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 카카오톡 API 초기화
try:
    kakao_api = KakaoAPI()
    kakao_channel_api = KakaoChannelAPI()
except ValueError as e:
    logger.error(f"카카오톡 API 초기화 실패: {e}")
    kakao_api = None
    kakao_channel_api = None

# 스케줄러 초기화
scheduler = MenuScheduler()

@app.route('/webhook', methods=['POST'])
def webhook():
    """카카오톡 챗봇 웹훅 엔드포인트"""
    try:
        data = request.get_json()
        
        # 사용자 메시지 처리
        if 'userRequest' in data:
            user_message = data['userRequest']['utterance']
            user_id = data['userRequest']['user']['id']
            
            logger.info(f"사용자 메시지: {user_message} (사용자 ID: {user_id})")
            
            # 메뉴 요청 처리
            if any(keyword in user_message for keyword in ['메뉴', '식단', '밥', '점심', '저녁']):
                today = datetime.now().strftime("%Y-%m-%d")
                menu_message = format_menu_for_kakao(today)
                
                response = {
                    "version": "2.0",
                    "template": {
                        "outputs": [
                            {
                                "simpleText": {
                                    "text": menu_message
                                }
                            }
                        ]
                    }
                }
                return jsonify(response)
            
            # 기본 응답
            response = {
                "version": "2.0", 
                "template": {
                    "outputs": [
                        {
                            "simpleText": {
                                "text": "안녕하세요! 아주대 메뉴봇입니다. '메뉴'라고 입력하시면 오늘의 식단을 확인할 수 있어요!"
                            }
                        }
                    ]
                }
            }
            return jsonify(response)
        
        return jsonify({"status": "ok"})
        
    except Exception as e:
        logger.error(f"웹훅 처리 중 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/send-menu', methods=['POST'])
@require_admin_key()
@log_request()
def send_menu_manually():
    """수동으로 메뉴 전송 (관리자 전용)"""
    try:
        date_str = request.json.get('date', datetime.now().strftime("%Y-%m-%d"))
        menu_message = format_menu_for_kakao(date_str)
        
        logger.info(f"Manual menu send requested for date: {date_str}")
        
        if kakao_api:
            result = kakao_api.send_message_to_all_users(menu_message)
            logger.info(f"Menu sent successfully: {result}")
            return jsonify(result)
        else:
            return jsonify({"success": False, "error": "카카오톡 API가 설정되지 않았습니다"})
            
    except Exception as e:
        logger.error(f"메뉴 전송 중 오류: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/menu', methods=['GET'])
def get_menu():
    """메뉴 조회 API"""
    try:
        date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        menu_message = format_menu_for_kakao(date_str)
        return jsonify({"menu": menu_message})
    except Exception as e:
        logger.error(f"메뉴 조회 중 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/menu-web', methods=['GET'])
def get_menu_web():
    """웹 페이지 형태의 메뉴 조회"""
    try:
        date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        menu_message = format_menu_for_kakao(date_str)
        
        # HTML 형태로 반환 (한글 정상 표시)
        html_content = f'''
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>아주대 식당 메뉴 - {date_str}</title>
            <style>
                body {{
                    font-family: 'Malgun Gothic', sans-serif;
                    line-height: 1.6;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .menu-content {{
                    white-space: pre-line;
                    font-size: 14px;
                    line-height: 1.8;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #FEE500;
                }}
                .refresh-btn {{
                    background: #FEE500;
                    color: #000;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 14px;
                    margin-bottom: 20px;
                }}
                .refresh-btn:hover {{
                    background: #FFDC00;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1> 아주대 식당 메뉴</h1>
                    <p> {date_str}</p>
                </div>
                <button class="refresh-btn" onclick="location.reload()"> 새로고침</button>
                <div class="menu-content">{menu_message}</div>
                <br>
                <hr>
                <p style="text-align: center; color: #666; font-size: 12px;">
                     <strong>팁:</strong><br>
                    • API 형태: <a href="/menu?date={date_str}">/menu?date={date_str}</a><br>
                    • 다른 날짜: <a href="/menu-web?date=2025-09-16">/menu-web?date=YYYY-MM-DD</a><br>
                    • 카카오톡 봇에 "메뉴" 메시지를 보내보세요!
                </p>
            </div>
        </body>
        </html>
        '''
        
        response = app.response_class(
            response=html_content,
            status=200,
            mimetype='text/html; charset=utf-8'
        )
        return response
        
    except Exception as e:
        logger.error(f"웹 메뉴 조회 중 오류: {e}")
        return f"<h1>오류</h1><p>{str(e)}</p>", 500

@app.route('/health', methods=['GET'])
def health_check():
    """헬스체크 엔드포인트"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "scheduler_running": scheduler.is_running()
    })

@app.route('/schedule/start', methods=['POST'])
@require_admin_key()
@log_request()
def start_scheduler():
    """스케줄러 시작 (관리자 전용)"""
    try:
        scheduler.start()
        logger.info("Scheduler started by admin")
        return jsonify({"success": True, "message": "스케줄러가 시작되었습니다"})
    except Exception as e:
        logger.error(f"스케줄러 시작 중 오류: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/schedule/stop', methods=['POST'])
@require_admin_key()
@log_request()
def stop_scheduler():
    """스케줄러 중지 (관리자 전용)"""
    try:
        scheduler.stop()
        logger.info("Scheduler stopped by admin")
        return jsonify({"success": True, "message": "스케줄러가 중지되었습니다"})
    except Exception as e:
        logger.error(f"스케줄러 중지 중 오류: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/oauth/authorize')
@check_ip_whitelist()
@log_request()
def oauth_authorize():
    """카카오 OAuth 인증 시작 (IP 제한)"""
    rest_api_key = os.getenv('KAKAO_REST_API_KEY')
    redirect_uri = f"http://localhost:{os.getenv('FLASK_PORT', 5003)}/oauth/callback"
    
    auth_url = f"https://kauth.kakao.com/oauth/authorize?client_id={rest_api_key}&redirect_uri={redirect_uri}&response_type=code&scope=talk_message"
    
    log_with_ip("OAuth authorization started", 'info')
    
    return f'''
    <h2>카카오톡 메뉴봇 OAuth 인증</h2>
    <p>메뉴를 카카오톡으로 전송하기 위해 인증이 필요합니다.</p>
    <a href="{auth_url}" style="background: #FEE500; color: #000; padding: 10px 20px; text-decoration: none; border-radius: 5px;">카카오 로그인</a>
    '''

@app.route('/oauth/callback')
def oauth_callback():
    """카카오 OAuth 콜백 처리"""
    try:
        code = request.args.get('code')
        if not code:
            return jsonify({"error": "Authorization code not found"}), 400
        
        # 액세스 토큰 요청
        token_url = "https://kauth.kakao.com/oauth/token"
        rest_api_key = os.getenv('KAKAO_REST_API_KEY')
        redirect_uri = f"http://localhost:{os.getenv('FLASK_PORT', 5003)}/oauth/callback"
        
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': rest_api_key,
            'redirect_uri': redirect_uri,
            'code': code
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_result = token_response.json()
        
        if 'access_token' in token_result:
            access_token = token_result['access_token']
            
            # 액세스 토큰을 파일에 저장 (실제 운영에서는 더 안전한 방법 사용)
            with open('.access_token', 'w') as f:
                f.write(access_token)
            
            logger.info("액세스 토큰이 성공적으로 발급되었습니다")
            
            return f'''
            <h2>인증 완료!</h2>
            <p>카카오톡 메시지 전송 권한이 허용되었습니다.</p>
            <p>이제 메뉴를 카카오톡으로 전송할 수 있습니다.</p>
            <a href="/test-message">메시지 전송 테스트</a>
            '''
        else:
            logger.error(f"토큰 발급 실패: {token_result}")
            return jsonify({"error": "토큰 발급 실패", "details": token_result}), 400
            
    except Exception as e:
        logger.error(f"OAuth 콜백 처리 중 오류: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/test-message')
def test_message():
    """액세스 토큰을 사용한 메시지 전송 테스트 (나에게 보내기 전용)"""
    try:
        # 저장된 액세스 토큰 읽기
        try:
            with open('.access_token', 'r') as f:
                access_token = f.read().strip()
        except FileNotFoundError:
            return "액세스 토큰이 없습니다. <a href='/oauth/authorize'>인증하기</a>"
        
        # 오늘 메뉴 가져오기
        today = datetime.now().strftime("%Y-%m-%d")
        menu_message = format_menu_for_kakao(today)
        
        # 카카오톡 메시지 전송 (나에게 보내기)
        url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        template_object = {
            "object_type": "text",
            "text": menu_message,
            "link": {
                "web_url": "https://www.ajou.ac.kr/kr/life/food.do"
            }
        }
        
        data = {
            "template_object": json.dumps(template_object)
        }
        
        response = requests.post(url, headers=headers, data=data)
        result = response.json()
        
        if response.status_code == 200:
            return f'''
            <h2>메시지 전송 성공!</h2>
            <p> 주의: 이는 "나에게 보내기" 전용입니다.</p>
            <p>다른 사용자에게 메뉴를 전송하려면 카카오톡 채널을 사용해야 합니다.</p>
            <p><a href="/channel-setup">카카오톡 채널 설정하기</a></p>
            <pre>{json.dumps(result, indent=2, ensure_ascii=False)}</pre>
            '''
        else:
            return f'''
            <h2>메시지 전송 실패</h2>
            <p>오류: {result}</p>
            '''
            
    except Exception as e:
        logger.error(f"메시지 전송 테스트 중 오류: {e}")
        return f"오류: {str(e)}"

@app.route('/channel-setup')
def channel_setup():
    """TBD: 카카오톡 채널 설정 안내"""
    return 

@app.route('/favicon.ico')
def favicon():
    """Favicon 요청 처리"""
    return '', 204

@app.route('/apple-touch-icon.png')
@app.route('/apple-touch-icon-precomposed.png')
def apple_touch_icon():
    """Apple touch icon 요청 처리"""
    return '', 204

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5003))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # 스케줄러 시작
    scheduler.start()
    
    try:
        app.run(host='0.0.0.0', port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info("서버 종료 중...")
        scheduler.stop()
    except Exception as e:
        logger.error(f"서버 실행 중 오류: {e}")
        scheduler.stop()