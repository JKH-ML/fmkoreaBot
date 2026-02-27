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
        print("디스코드 웹훅 URL이 설정되지 않았습니다. 메일 전송을 건너뜁니다.")
        return

    if not posts:
        return

    embeds = []
    for i, post in enumerate(posts[:5], 1):
        embeds.append({
            "title": f"{i}. [추천: {post['count']}] {post['title']}",
            "url": post['link'],
            "color": 5814783
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
        browser = p.chromium.launch(headless=True)
        # 보안 탐지 우회를 위해 추가 설정
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800},
            locale="ko-KR",
            timezone_id="Asia/Seoul"
        )
        page_obj = context.new_page()

        for page_num in range(1, 6):
            url = base_url.format(page_num)
            try:
                # 봇 탐지를 피하기 위해Referer 추가 및 이동
                page_obj.goto("https://www.google.com", wait_until="domcontentloaded")
                time.sleep(1)
                
                print(f"{page_num}페이지 접속 중: {url}")
                page_obj.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # 로딩 대기 시간 충분히 확보
                time.sleep(5)
                
                html = page_obj.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                # 페이지 제목 출력 (차단 여부 확인용)
                print(f"페이지 타이틀: {page_obj.title()}")
                
                posts = soup.select('li.li')
                
                if not posts:
                    # 게시글을 찾지 못한 경우 스크린샷 저장
                    page_obj.screenshot(path=f"debug_page_{page_num}.png")
                    print(f"주의: {page_num}페이지에서 게시글 리스트를 찾지 못했습니다. (스크린샷 저장됨)")
                    
                    # 혹시 Cloudflare 차단 페이지인지 확인
                    if "Cloudflare" in html or "Verify" in html:
                        print("보안 차단 페이지(Cloudflare 등)가 감지되었습니다.")
                
                page_posts_count = 0
                for post in posts:
                    title_elem = post.select_one('h3.title span.ellipsis-target') or post.select_one('h3.title a')
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
                        
                        all_posts.append({'title': title, 'count': count, 'link': link})
                        page_posts_count += 1
                
                print(f"{page_num}페이지 완료 (수집된 게시글: {page_posts_count})")
                time.sleep(2)
                
            except Exception as e:
                print(f"{page_num}페이지 수집 중 오류: {str(e)}")
                page_obj.screenshot(path=f"error_page_{page_num}.png")
                continue

        browser.close()

    if all_posts:
        # 추천수 기준 내림차순 정렬 및 중복 제거
        all_posts.sort(key=lambda x: x['count'], reverse=True)
        unique_posts = []
        seen_links = set()
        for p in all_posts:
            if p['link'] not in seen_links:
                unique_posts.append(p)
                seen_links.add(p['link'])
        
        print(f"총 {len(unique_posts)}개의 고유 게시글 수집 완료. TOP 5 전송을 시작합니다.")
        send_discord_message(webhook_url, unique_posts[:5])
    else:
        print("\n수집된 게시글이 없어 메시지를 전송하지 않습니다.")

if __name__ == "__main__":
    get_top_posts()
