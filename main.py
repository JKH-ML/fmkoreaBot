import sys
import os
import time
import requests
import json
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
                return json.load(f)
        except:
            return []
    return []

def save_data(data):
    # 최대 100개 유지 (오래된 항목 삭제)
    if len(data) > 100:
        data = data[-100:]
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def extract_id(url):
    parsed_url = urlparse(url)
    qs = parse_qs(parsed_url.query)
    # FMKorea URL format: ...document_srl=12345...
    return qs.get("document_srl", [None])[0]

def send_discord_message(webhook_url, posts):
    if not webhook_url or not posts:
        return

    # 디스코드 임베드는 한 번에 최대 10개까지만 가능
    # 10개가 넘으면 여러 번 나눠서 보냄
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

    print("수집을 시작합니다 (추천 300 이상 필터링)...")
    
    with SB(uc=True, test=True, headless=False, locale_code="ko") as sb:
        for page_num in range(1, 6):
            url = base_url.format(page_num)
            try:
                print(f"{page_num}페이지 접속 중...")
                sb.uc_open_with_reconnect(url, 4)
                time.sleep(3)
                
                html = sb.get_page_source()
                soup = BeautifulSoup(html, 'html.parser')
                posts = soup.select('li.li')
                
                found_new_on_page = 0
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
                        
                        # 추천수 300 이상 필터
                        if count < 300:
                            continue

                        link = link_elem['href']
                        if not link.startswith('http'):
                            link = "https://www.fmkorea.com" + link
                        
                        doc_id = extract_id(link)
                        # 중복 체크 (이미 처리된 ID이거나 현재 루프에서 새로 발견된 ID인 경우 제외)
                        if not doc_id or doc_id in processed_ids or doc_id in new_ids:
                            continue

                        title = " ".join(title_elem.get_text().split())
                        new_posts.append({'title': title, 'count': count, 'link': link})
                        new_ids.append(doc_id)
                        found_new_on_page += 1
                
                print(f"{page_num}페이지 완료 (새로운 글: {found_new_on_page})")
                
            except Exception as e:
                print(f"{page_num}페이지 오류: {e}")
                continue

    if new_posts:
        print(f"새로운 게시글 {len(new_posts)}개를 발견했습니다. 데이터를 업데이트하고 디스코드로 전송합니다.")
        # 데이터 업데이트 및 저장
        processed_ids.extend(new_ids)
        save_data(processed_ids)
        # 디스코드 전송
        send_discord_message(webhook_url, new_posts)
    else:
        print("새로 추가된 조건(300+)에 맞는 게시글이 없습니다.")

if __name__ == "__main__":
    get_top_posts()
