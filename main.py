import requests
from bs4 import BeautifulSoup
import json
import os
import time

# 설정
DB_FILE = "notified_ids.json"
WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')
# 최신순 페이지 주소 (1~5페이지 순회용)
BASE_URL = "https://www.fmkorea.com/index.php?mid=afreecatv&page="

def check_fmkorea():
    # 1. 기존 알림 목록 로드 (중복 방지용)
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                notified_ids = set(json.load(f))
        except:
            notified_ids = set()
    else:
        notified_ids = set()

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Referer': 'https://www.fmkorea.com/afreecatv'
    }

    new_notified_count = 0

    # 2. 1페이지부터 5페이지까지 확인 (밀려난 글의 추천수 변화 추적)
    for page in range(1, 6):
        print(f"--- Checking page {page} ---")
        try:
            res = requests.get(BASE_URL + str(page), headers=headers)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 게시글 아이템(li) 추출 
            posts = soup.select("li.li")
            
            for post in posts:
                try:
                    # 추천수 추출 [cite: 1, 2]
                    vote_tag = post.select_one("a.pc_voted_count span.count")
                    if not vote_tag: continue
                    votes = int(vote_tag.text.strip().replace(',', '') or 0)

                    # 추천 300개 이상 조건 확인
                    if votes >= 300:
                        link_tag = post.select_one("h3.title a")
                        # href에서 document_srl(글번호) 추출 [cite: 1, 2]
                        href = link_tag['href']
                        post_id = href.split('document_srl=')[-1].split('&')[0]

                        # 이미 보낸 알림인지 확인
                        if post_id not in notified_ids:
                            title = post.select_one("span.ellipsis-target").text.strip() # 
                            msg = f"🔥 **300추 돌파 인기글!**\n**제목:** {title}\n**추천:** {votes}개\n**링크:** https://www.fmkorea.com/{post_id}"
                            
                            # 디스코드 전송
                            if WEBHOOK_URL:
                                response = requests.post(WEBHOOK_URL, json={"content": msg})
                                if response.status_code == 204:
                                    notified_ids.add(post_id)
                                    new_notified_count += 1
                                    print(f"알림 전송: {title}")
                except:
                    continue
            time.sleep(1) # 차단 방지
        except Exception as e:
            print(f"페이지 오류: {e}")

    # 3. 데이터베이스 업데이트 (최근 1000개 기록 유지)
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(notified_ids)[-1000:], f)
    print(f"작업 완료. 새 알림: {new_notified_count}개")

if __name__ == "__main__":
    check_fmkorea()