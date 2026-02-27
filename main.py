import sys
import os
import time
import requests
from bs4 import BeautifulSoup
from seleniumbase import SB

# Windows에서 한국어 출력을 위해 인코딩 설정
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def send_discord_message(webhook_url, posts):
    if not webhook_url:
        print("디스코드 웹훅 URL이 설정되지 않았습니다. 전송을 건너뜁니다.")
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

    print("SeleniumBase(Undetected 모드)를 실행하여 데이터를 수집합니다...")
    
    # uc=True: Cloudflare 우회를 위한 undetected-chromedriver 활성화
    # 가상 모니터(Xvfb)를 사용할 것이므로 script 내부에서는 headless=False로 설정
    with SB(uc=True, test=True, headless=False, locale_code="ko") as sb:
        for page_num in range(1, 6):
            url = base_url.format(page_num)
            try:
                print(f"{page_num}페이지 접속 중...")
                
                # Cloudflare 우회를 위한 특수 접속 메서드
                sb.uc_open_with_reconnect(url, 4)
                time.sleep(3)
                
                # Cloudflare 캡차가 보일 경우 자동 클릭 시도
                try:
                    sb.uc_gui_click_captcha()
                    time.sleep(2)
                except:
                    pass # 캡차가 없으면 무시
                
                html = sb.get_page_source()
                soup = BeautifulSoup(html, 'html.parser')
                
                print(f"페이지 타이틀: {sb.get_title()}")
                
                posts = soup.select('li.li')
                
                if not posts:
                    sb.save_screenshot(f"debug_page_{page_num}.png")
                    print(f"주의: {page_num}페이지에서 게시글 리스트를 찾지 못했습니다. (스크린샷 저장됨)")
                
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
                try:
                    sb.save_screenshot(f"error_page_{page_num}.png")
                except:
                    pass
                continue

    if all_posts:
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
