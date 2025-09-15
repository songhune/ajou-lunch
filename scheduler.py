from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import os
import logging
from datetime import datetime
import pytz

from menu_scraper import format_menu_for_kakao
from kakao_api import KakaoAPI

logger = logging.getLogger(__name__)

class MenuScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.timezone = pytz.timezone(os.getenv('TIMEZONE', 'Asia/Seoul'))
        self.notification_time = os.getenv('NOTIFICATION_TIME', '12:00')
        
        # 알림 시간 파싱
        try:
            hour, minute = map(int, self.notification_time.split(':'))
            self.hour = hour
            self.minute = minute
        except ValueError:
            logger.warning(f"잘못된 알림 시간 형식: {self.notification_time}. 기본값 12:00 사용")
            self.hour = 12
            self.minute = 0
        
        self._setup_jobs()
    
    def _setup_jobs(self):
        """스케줄 작업 설정"""
        # 매일 정해진 시간에 메뉴 전송
        self.scheduler.add_job(
            func=self._send_daily_menu,
            trigger=CronTrigger(
                hour=self.hour, 
                minute=self.minute,
                timezone=self.timezone
            ),
            id='daily_menu_notification',
            name='Daily Menu Notification',
            replace_existing=True
        )
        
        logger.info(f"일일 메뉴 알림이 {self.hour:02d}:{self.minute:02d}에 설정되었습니다")
    
    def _send_daily_menu(self):
        """일일 메뉴 전송 작업"""
        try:
            logger.info("일일 메뉴 전송 시작")
            
            # 오늘 날짜로 메뉴 조회
            today = datetime.now(self.timezone).strftime("%Y-%m-%d")
            menu_message = format_menu_for_kakao(today)
            
            # 카카오톡 나에게 보내기로 메뉴 전송
            try:
                # 저장된 액세스 토큰 확인
                try:
                    with open('.access_token', 'r') as f:
                        access_token = f.read().strip()
                    
                    # 나에게 보내기 API 사용
                    import requests
                    import json
                    
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
                        logger.info("나에게 메뉴 전송 성공")
                    else:
                        logger.error(f"메뉴 전송 실패: {result}")
                        
                except FileNotFoundError:
                    logger.warning("액세스 토큰이 없습니다. OAuth 인증을 먼저 진행해주세요.")
                    
            except Exception as e:
                logger.error(f"카카오톡 메시지 전송 오류: {e}")
                
        except Exception as e:
            logger.error(f"일일 메뉴 전송 중 오류 발생: {e}")
    
    def start(self):
        """스케줄러 시작"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("메뉴 스케줄러가 시작되었습니다")
        else:
            logger.info("메뉴 스케줄러가 이미 실행 중입니다")
    
    def stop(self):
        """스케줄러 중지"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("메뉴 스케줄러가 중지되었습니다")
        else:
            logger.info("메뉴 스케줄러가 이미 중지되어 있습니다")
    
    def is_running(self):
        """스케줄러 실행 상태 확인"""
        return self.scheduler.running
    
    def get_next_run_time(self):
        """다음 실행 시간 조회"""
        job = self.scheduler.get_job('daily_menu_notification')
        if job:
            return job.next_run_time
        return None
    
    def send_test_menu(self):
        """테스트용 메뉴 전송"""
        logger.info("테스트 메뉴 전송 실행")
        self._send_daily_menu()
    
    def update_schedule(self, hour: int, minute: int):
        """스케줄 시간 업데이트"""
        try:
            # 기존 작업 제거
            self.scheduler.remove_job('daily_menu_notification')
            
            # 새로운 시간으로 작업 추가
            self.hour = hour
            self.minute = minute
            
            self.scheduler.add_job(
                func=self._send_daily_menu,
                trigger=CronTrigger(
                    hour=hour,
                    minute=minute, 
                    timezone=self.timezone
                ),
                id='daily_menu_notification',
                name='Daily Menu Notification',
                replace_existing=True
            )
            
            logger.info(f"알림 시간이 {hour:02d}:{minute:02d}로 변경되었습니다")
            return True
            
        except Exception as e:
            logger.error(f"스케줄 업데이트 실패: {e}")
            return False