import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
import requests
import json
import os

# 설정
DB_FILE = "notified_ids.json"
WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')
# 인기순(pop) 정렬이 유지된 기본 주소
BASE_URL = "https://www.fmkorea.com/index.php?mid=afreecatv&sort_index=pop&order_type=desc&page="

async def run_bot():
    # 1. 기존 알림 목록 로드
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                notified_ids = set(json.load(f))
        except:
            notified_ids = set()
    else:
        notified_ids = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        newly_notified = []

        try:
            # 인기순 페이지 1부터 5까지 순회
            for page_num in range(1, 6):
                target_url = f"{BASE_URL}{page_num}"
                print(f"🔎 인기순 {page_num}페이지 분석 중...")
                
                await page.goto(target_url, wait_until="load", timeout=60000)
                await page.wait_for_timeout(7000) # 자바스크립트 로딩 대기
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                posts = soup.select("li.li")

                for post in posts:
                    try:
                        # 추천수 추출
                        vote_tag = post.select_one(".pc_voted_count .count")
                        if not vote_tag: continue
                        
                        votes = int(re.sub(r'[^0-9]', '', vote_tag.get_text()) or 0)
                        
                        # 기준: 250추 이상
                        if votes >= 250:
                            link_tag = post.select_one("h3.title a")
                            raw_href = link_tag['href']
                            
                            # 고유 ID(document_srl) 추출
                            if 'document_srl=' in raw_href:
                                post_id = raw_href.split('document_srl=')[-1].split('&')[0]
                            else:
                                post_id = raw_href.strip('/')

                            # 중복 알림 체크
                            if post_id not in notified_ids:
                                title_tag = post.select_one(".ellipsis-target")
                                title = title_tag.get_text(strip=True) if title_tag else "제목없음"
                                full_link = f"https://www.fmkorea.com{raw_href}" if raw_href.startswith('/') else raw_href
                                
                                if WEBHOOK_URL:
                                    msg = f"🔥 **250추 돌파 인기글**\n**제목:** {title}\n**추천:** {votes}개\n**링크:** {full_link}"
                                    requests.post(WEBHOOK_URL, json={"content": msg})
                                    notified_ids.add(post_id)
                                    newly_notified.append(title)
                                    print(f"✅ 알림 전송: {title} ({votes}추)")
                    except Exception:
                        continue
                
                await asyncio.sleep(1.5) # 페이지 간 안전 대기

            # 2. 결과 저장
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(notified_ids)[-1000:], f)
            print(f"✅ 작업 완료. 새 알림: {len(newly_notified)}개")

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())