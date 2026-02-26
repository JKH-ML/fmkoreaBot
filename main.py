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
TARGET_URL = "https://www.fmkorea.com/index.php?mid=afreecatv&sort_index=pop&order_type=desc&page=1"

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
        browser = await p.chromium.launch(headless=True) # 서버용이므로 headless=True
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            await page.goto(TARGET_URL, wait_until="load", timeout=60000)
            await page.wait_for_timeout(7000) # 로딩 대기
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            posts = soup.select("li.li") [cite: 1]

            newly_notified = []
            for post in posts:
                try:
                    # 추천수 추출
                    vote_tag = post.select_one(".pc_voted_count .count") [cite: 1, 2]
                    if not vote_tag: continue
                    
                    votes = int(re.sub(r'[^0-9]', '', vote_tag.get_text()) or 0) [cite: 2]
                    
                    # 기준: 250추 이상
                    if votes >= 250:
                        link_tag = post.select_one("h3.title a") [cite: 1]
                        raw_href = link_tag['href']
                        
                        # document_srl 기반 고유 ID 추출
                        post_id = raw_href.split('document_srl=')[-1].split('&')[0]
                        
                        if post_id not in notified_ids:
                            title = post.select_one(".ellipsis-target").get_text(strip=True) [cite: 1, 2]
                            full_link = f"https://www.fmkorea.com{raw_href}" if raw_href.startswith('/') else raw_href
                            
                            # 디스코드 전송
                            if WEBHOOK_URL:
                                msg = f"🔥 **250추 돌파 인기글**\n**제목:** {title}\n**추천:** {votes}개\n**링크:** {full_link}"
                                requests.post(WEBHOOK_URL, json={"content": msg})
                                notified_ids.add(post_id)
                                newly_notified.append(title)

                except Exception:
                    continue

            # 2. 결과 저장
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(notified_ids)[-1000:], f)
            print(f"✅ 작업 완료. 새 알림: {len(newly_notified)}개")

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())