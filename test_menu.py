#!/usr/bin/env python3
"""
메뉴 스크래핑 테스트 스크립트
"""

from menu_scraper import format_menu_for_kakao, fetch_ajou_meals
from datetime import datetime

def test_menu_scraping():
    """메뉴 스크래핑 테스트"""
    print("=== 메뉴 스크래핑 테스트 ===")
    
    # 오늘 날짜로 테스트
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"테스트 날짜: {today}")
    
    try:
        # 원본 데이터 확인
        print("\n--- 원본 메뉴 데이터 ---")
        all_menus = fetch_ajou_meals(today)
        
        for restaurant, meals in all_menus.items():
            print(f"\n{restaurant}:")
            for meal_time, menu in meals.items():
                print(f"  {meal_time}: {menu[:100]}..." if len(menu) > 100 else f"  {meal_time}: {menu}")
        
        # 포맷팅된 메시지 확인
        print("\n--- 카카오톡용 포맷팅된 메시지 ---")
        formatted_message = format_menu_for_kakao(today)
        print(formatted_message)
        
        print(f"\n메시지 길이: {len(formatted_message)} 문자")
        
    except Exception as e:
        print(f"테스트 실패: {e}")

if __name__ == "__main__":
    test_menu_scraping()