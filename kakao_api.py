import requests
import json
import os
from datetime import datetime

class KakaoAPI:
    def __init__(self):
        self.rest_api_key = os.getenv('KAKAO_REST_API_KEY')
        self.admin_key = os.getenv('KAKAO_ADMIN_KEY')
        self.channel_uuid = os.getenv('KAKAO_CHANNEL_UUID')
        
        if not all([self.rest_api_key, self.admin_key, self.channel_uuid]):
            raise ValueError("카카오톡 API 설정이 완료되지 않았습니다. .env 파일을 확인해주세요.")
    
    def send_message_to_all_users(self, message: str):
        """모든 채널 친구들에게 메시지 전송"""
        url = "https://kapi.kakao.com/v1/api/talk/friends/message/default/send"
        
        headers = {
            "Authorization": f"Bearer {self.rest_api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        template_object = {
            "object_type": "text",
            "text": message,
            "link": {
                "web_url": "https://www.ajou.ac.kr/kr/life/food.do"
            }
        }
        
        data = {
            "template_object": json.dumps(template_object)
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            return {"success": True, "response": response.json()}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def send_message_to_user(self, user_uuid: str, message: str):
        """특정 사용자에게 메시지 전송"""
        url = "https://kapi.kakao.com/v1/api/talk/friends/message/default/send"
        
        headers = {
            "Authorization": f"Bearer {self.rest_api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        template_object = {
            "object_type": "text",
            "text": message,
            "link": {
                "web_url": "https://www.ajou.ac.kr/kr/life/food.do"
            }
        }
        
        data = {
            "receiver_uuids": f'["{user_uuid}"]',
            "template_object": json.dumps(template_object)
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            return {"success": True, "response": response.json()}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}
    
    def get_friends_list(self):
        """채널 친구 목록 조회"""
        url = "https://kapi.kakao.com/v1/api/talk/friends"
        
        headers = {
            "Authorization": f"Bearer {self.rest_api_key}"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return {"success": True, "friends": response.json()}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}

class KakaoChannelAPI:
    """카카오톡 채널(구 플러스친구) API"""
    
    def __init__(self):
        self.admin_key = os.getenv('KAKAO_ADMIN_KEY')
        
        if not self.admin_key:
            raise ValueError("카카오톡 Admin Key가 설정되지 않았습니다.")
    
    def send_channel_message(self, message: str):
        """채널을 통해 메시지 전송 (관리자 권한 필요)"""
        # 실제 구현에서는 카카오 비즈니스 API를 사용해야 합니다
        # 이는 개인 개발자가 사용하기 어려운 API입니다
        url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
        
        headers = {
            "Authorization": f"KakaoAK {self.admin_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        template_object = {
            "object_type": "text", 
            "text": message,
            "link": {
                "web_url": "https://www.ajou.ac.kr/kr/life/food.do"
            }
        }
        
        data = {
            "template_object": json.dumps(template_object)
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            return {"success": True, "response": response.json()}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)}