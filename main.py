import sys
import os
import time
import requests
import json
import random
from bs4 import BeautifulSoup
from seleniumbase import SB
from urllib.parse import urlparse, parse_qs

# Windows에서 한국어 출력을 위해 인코딩 설정
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except:
            return []
    return []

def save_data(data):
    if len(data) > 100:
        data = data[-100:]
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def extract_id(url):
    parsed_url = urlparse(url)
    qs = parse_qs(parsed_url.query)
    return qs.get("document_srl", [None])[0]

def send_discord_message(webhook_url, posts):
    if not webhook_url or not posts:
        return

    for i in range(0, len(posts), 10):
        chunk = posts[i:i+10]
        embeds = []
        for post in chunk:
            embeds.append({
                "title": f"🔥 [추천: {post['count']}] {post['title']}",
                "url": post['link'],
                "color": 15548997
            })

        payload = {
            "content": "📢 **새로운 인기 게시글 알림 (추천 300+ 건)**" if i == 0 else "",
            "embeds": embeds
        }
        try:
            requests.post(webhook_url, json=payload)
        except Exception as e:
            print(f"디스코드 전송 오류: {e}")

def get_top_posts():
    base_url = "https://www.fmkorea.com/index.php?mid=afreecatv&sort_index=pop&order_type=desc&page={}"
    webhook_url = os.environ.get("DISCORD_WEBHOOK")
    
    processed_ids = load_data()
    new_posts = []
    new_ids = []

    print(f"수집을 시작합니다... (현재 저장된 글 번호: {len(processed_ids)}개)")
    
    # 더 정교한 우회를 위해 stealth 설정을 강화한 SB 실행
    with SB(uc=True, test=True, headless=False, locale_code="ko", ad_block=True) as sb:
        try:
            # 1. 메인 페이지를 먼저 방문하여 세션 쿠키를 생성 (사람처럼 행동)
            print("메인 페이지 접속 중 (세션 생성)...")
            sb.uc_open_with_reconnect("https://www.fmkorea.com/", 6)
            time.sleep(random.uniform(5, 8))
            
            # 2. 게시판 페이지 순회
            for page_num in range(1, 11):
                url = base_url.format(page_num)
                print(f"\n[{page_num}페이지 접속 중...]")
                
                # 접속 시도 (최대 7회 재시도하며 보안 우회)
                sb.uc_open_with_reconnect(url, 7)
                time.sleep(random.uniform(7, 10))
                
                title = sb.get_title()
                print(f"페이지 타이틀: {title}")
                
                # 보안 페이지 감지 시 추가 대응
                if "보안" in title or "Just a moment" in title:
                    print("보안 페이지 감지! 캡차 우회 시도...")
                    try:
                        sb.uc_gui_click_captcha()
                        time.sleep(10)
                        title = sb.get_title()
                        print(f"재접속 후 타이틀: {title}")
                    except:
                        print("캡차 클릭 실패 또는 버튼 없음.")
                
                html = sb.get_page_source()
                soup = BeautifulSoup(html, 'html.parser')
                posts = soup.select('li.li')
                
                total_on_page = len(posts)
                max_count_on_page = 0
                found_new_on_page = 0
                
                if total_on_page == 0:
                    print(f"주의: {page_num}페이지에서 게시글을 찾지 못했습니다. (보안 차단 가능성)")
                    sb.save_screenshot(f"debug_page_{page_num}.png")
                
                for post in posts:
                    title_elem = post.select_one('h3.title span.ellipsis-target') or post.select_one('h3.title a')
                    count_elem = post.select_one('span.count')
                    link_elem = post.select_one('h3.title a')
                    
                    if title_elem and count_elem and link_elem:
                        try:
                            count_text = count_elem.get_text(strip=True)
                            count = int(''.join(filter(str.isdigit, count_text)))
                        except:
                            count = 0
                        
                        if count > max_count_on_page:
                            max_count_on_page = count
                        
                        if count < 300:
                            continue

                        link = link_elem['href']
                        if not link.startswith('http'):
                            link = "https://www.fmkorea.com" + link
                        
                        doc_id = extract_id(link)
                        if not doc_id or doc_id in processed_ids or doc_id in new_ids:
                            continue

                        title = " ".join(title_elem.get_text().split())
                        new_posts.append({'title': title, 'count': count, 'link': link})
                        new_ids.append(doc_id)
                        found_new_on_page += 1
                
                print(f"결과: {total_on_page}개 수집, 최고 추천수 {max_count_on_page}, 신규 {found_new_on_page}개")
                time.sleep(random.uniform(2, 4))
                
        except Exception as e:
            print(f"전체 프로세스 중 치명적 오류: {e}")
            sb.save_screenshot("fatal_error.png")

    if new_posts:
        print(f"\n총 {len(new_posts)}개의 새로운 게시글 발견. 데이터를 업데이트하고 디스코드로 전송합니다.")
        processed_ids.extend(new_ids)
        save_data(processed_ids)
        send_discord_message(webhook_url, new_posts)
    else:
        print("\n새로 추가할 게시글이 없습니다.")

if __name__ == "__main__":
    get_top_posts()
