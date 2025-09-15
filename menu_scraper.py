import requests
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

def fetch_restaurant_menu(articleNo: str, date_str: str = None):
    """학교 식당의 메뉴를 가져오는 함수"""
    url = "https://www.ajou.ac.kr/kr/life/food.do"
    params = {"mode": "view", "articleNo": articleNo}
    if date_str:
        params["date"] = date_str

    resp = requests.get(url, params=params)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    
    return soup

def clean_menu_text(text: str) -> str:
    """메뉴 텍스트에서 불필요한 안내문구 제거"""
    patterns_to_remove = [
        r'\[.*?안내\].*?(?=\n|\Z)',
        r'-.*?운영.*?(?=\n|\Z)',
        r'\*.*?운영.*?(?=\n|\Z)',
        r'※.*?(?=\n|\Z)',
        r'<.*?원>.*?(?=\n|\Z)',
        r'★.*?★.*?(?=\n|\Z)',
        r'후식음료:.*?(?=\n|\Z)',
    ]
    
    cleaned = text
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL)
    
    # 연속된 줄바꿈 정리
    cleaned = re.sub(r'\n\s*\n+', '\n', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned

def extract_meal_menu(soup, meal_type: str) -> str:
    """특정 식사 시간의 메뉴 추출"""
    box = soup.select_one(f".b-menu-day.{meal_type}")
    if box:
        raw_text = box.get_text("\n", strip=True)
        return clean_menu_text(raw_text)
    return "메뉴 없음"

def fetch_ajou_meals(date_str: str = None):
    """기숙사식당과 교직원식당 메뉴를 병렬로 조회"""
    
    def get_restaurant_meals(restaurant_info):
        name, articleNo = restaurant_info
        try:
            soup = fetch_restaurant_menu(articleNo, date_str)
            meals = {}
            
            # 점심과 저녁만 추출
            for meal_type, meal_name in [("lunch", "점심"), ("dinner", "저녁")]:
                meals[meal_name] = extract_meal_menu(soup, meal_type)
            
            return name, meals
        except Exception as e:
            print(f"Error fetching {name} menu: {e}")
            return name, {"점심": "메뉴 조회 실패", "저녁": "메뉴 조회 실패"}
    
    restaurants = [
        ("기숙사식당", "63"),
        ("교직원식당", "221904")
    ]
    
    # 병렬로 두 식당 메뉴 조회
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(get_restaurant_meals, restaurants))
    
    return dict(results)

def format_menu_for_kakao(date_str: str = None):
    """카카오톡 메시지 형식으로 메뉴 포맷팅"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    try:
        all_menus = fetch_ajou_meals(date_str)
        
        message = f" 아주대 식당 메뉴 ({date_str})\n\n"
        
        for restaurant, meals in all_menus.items():
            message += f" {restaurant}\n"
            message += "─" * 20 + "\n"
            
            for meal_time, menu in meals.items():
                message += f" {meal_time}\n"
                if menu and menu != "메뉴 없음":
                    # 메뉴 항목들을 더 읽기 쉽게 포맷팅
                    menu_items = [item.strip() for item in menu.split('\n') if item.strip()]
                    formatted_items = []
                    for item in menu_items:
                        if len(item) > 1:  # 한 글자짜리 제외
                            formatted_items.append(f"• {item}")
                    
                    if formatted_items:
                        message += "\n".join(formatted_items)
                    else:
                        message += "메뉴 정보 없음"
                else:
                    message += "메뉴 없음"
                message += "\n\n"
            
            message += "\n"
        
        message += " 맛있게 드세요!"
        return message
        
    except Exception as e:
        return f" 메뉴 조회 중 오류가 발생했습니다: {str(e)}"

if __name__ == "__main__":
    # 테스트
    print(format_menu_for_kakao("2025-09-10"))