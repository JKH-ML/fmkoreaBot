import sys
import os
import time
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Windows에서 한국어 출력을 위해 인코딩 설정
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def send_discord_message(webhook_url, posts):
    if not webhook_url:
        print("디스코드 웹훅 URL이 설정되지 않았습니다.")
        return

    embeds = []
    for i, post in enumerate(posts[:5], 1):
        embeds.append({
            "title": f"{i}. [추천: {post['count']}] {post['title']}",
            "url": post['link'],
            "color": 5814783 # FMKorea 느낌의 파란색 계열
        })

    payload = {
        "content": "📢 **FM코리아 아프리카TV 게시판 추천 TOP 5 (1~5페이지)**",
        "embeds": embeds
    }

    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 204:
            print("디스코드 메시지 전송 성공!")
        else:
            print(f"디스코드 메시지 전송 실패: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"디스코드 전송 중 예외 발생: {e}")

def get_top_posts():
    base_url = "https://www.fmkorea.com/index.php?mid=afreecatv&sort_index=pop&order_type=desc&page={}"
    all_posts = []
    webhook_url = os.environ.get("DISCORD_WEBHOOK")

    print("브라우저를 실행하여 데이터를 수집합니다 (1~5 페이지)...")
    
    with sync_playwright() as p:
        # 브라우저 실행
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page_obj = context.new_page()

        for page_num in range(1, 6):
            url = base_url.format(page_num)
            try:
                page_obj.goto(url, wait_until="domcontentloaded", timeout=60000)
                # 게시글 리스트가 로드될 때까지 대기
                time.sleep(3)
                
                html = page_obj.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                posts = soup.select('li.li')
                
                page_posts_count = 0
                for post in posts:
                    title_elem = post.select_one('h3.title span.ellipsis-target')
                    if not title_elem:
                        title_elem = post.select_one('h3.title a')
                    
                    count_elem = post.select_one('span.count')
                    link_elem = post.select_one('h3.title a')
                    
                    if title_elem and count_elem:
                        title = " ".join(title_elem.get_text().split())
                        try:
                            count_text = count_elem.get_text(strip=True)
                            count = int(''.join(filter(str.isdigit, count_text)))
                        except:
                            count = 0
                        
                        link = link_elem['href'] if link_elem else ""
                        if link and not link.startswith('http'):
                            link = "https://www.fmkorea.com" + link
                        
                        all_posts.append({
                            'title': title,
                            'count': count,
                            'link': link
                        })
                        page_posts_count += 1
                
                print(f"{page_num}페이지 완료 (수집된 게시글: {page_posts_count})")
                
            except Exception as e:
                print(f"{page_num}페이지 수집 중 오류: {str(e)}")
                continue

        browser.close()

    if not all_posts:
        print("\n수집된 게시글이 없습니다.")
        return

    # 추천수 기준 내림차순 정렬 및 중복 제거
    all_posts.sort(key=lambda x: x['count'], reverse=True)
    unique_posts = []
    seen_links = set()
    for p in all_posts:
        if p['link'] not in seen_links:
            unique_posts.append(p)
            seen_links.add(p['link'])
    
    # 디스코드 전송
    send_discord_message(webhook_url, unique_posts[:5])

if __name__ == "__main__":
    get_top_posts()
