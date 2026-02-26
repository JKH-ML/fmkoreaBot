import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from bs4 import BeautifulSoup
import re
import requests
import json
import os

DB_FILE = "notified_ids.json"
WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK')
BASE_URL = "https://www.fmkorea.com/index.php?mid=afreecatv&sort_index=pop&order_type=desc&page="

async def run_bot():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                notified_ids = set(json.load(f))
        except:
            notified_ids = set()
    else:
        notified_ids = set()

    async with async_playwright() as p:
        # 가상 브라우저 실행
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # [핵심] 스텔스 모드 적용 (봇 감지 우회)
        await stealth_async(page)
        
        newly_notified = []

        try:
            for page_num in range(1, 6):
                target_url = f"{BASE_URL}{page_num}"
                print(f"🔎 {page_num}페이지 분석 시작...")
                
                # 타임아웃을 늘리고 실제 사람처럼 동작 유도
                await page.goto(target_url, wait_until="networkidle", timeout=90000)
                await page.wait_for_timeout(8000) 
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                posts = soup.select("li.li")

                print(f"📊 {page_num}페이지에서 {len(posts)}개 글 발견")

                if len(posts) > 0:
                    for post in posts:
                        try:
                            vote_tag = post.select_one(".pc_voted_count .count")
                            if not vote_tag: continue
                            
                            votes = int(re.sub(r'[^0-9]', '', vote_tag.get_text()) or 0)
                            
                            if votes >= 250:
                                link_tag = post.select_one("h3.title a")
                                raw_href = link_tag['href']
                                post_id = raw_href.split('document_srl=')[-1].split('&')[0]
                                
                                if post_id not in notified_ids:
                                    title_tag = post.select_one(".ellipsis-target")
                                    title = title_tag.get_text(strip=True) if title_tag else "제목없음"
                                    full_link = f"https://www.fmkorea.com{raw_href}" if raw_href.startswith('/') else raw_href
                                    
                                    if WEBHOOK_URL:
                                        msg = f"🔥 **250추 돌파 인기글**\n**제목:** {title}\n**추천:** {votes}개\n**링크:** {full_link}"
                                        requests.post(WEBHOOK_URL, json={"content": msg})
                                        notified_ids.add(post_id)
                                        newly_notified.append(title)
                                        print(f"✅ 알림 전송: {title}")
                        except Exception:
                            continue
                
                await asyncio.sleep(3)

            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(notified_ids)[-1000:], f)
            print(f"🏁 작업 완료. 새 알림: {len(newly_notified)}개")

        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())