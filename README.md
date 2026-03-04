# 펨코 인기글 디스코드 알림 봇 (FMKorea Scraper)

## 📢 디스코드 참여하기
아래 링크를 통해 펨코 인기글 알림 서버에 자유롭게 참여하실 수 있습니다.
- [디스코드 서버 입장하기](https://discord.gg/r74ZhzyVUr)

FM코리아(fmkorea.com) 아프리카TV 게시판에서 일정 수준 이상의 추천을 받은 인기 게시글을 자동으로 수집하여 디스코드 채널로 전송해주는 파이썬 스크래퍼입니다.

## 주요 기능
- **인기글 필터링**: 추천수가 **300개 이상**인 게시글만 선별하여 수집합니다. (1~10페이지 체크)
- **중복 방지**: 이미 전송한 게시글의 ID를 `data.json`에 저장하여 중복 알림을 방지합니다.
- **보안 우회**: `seleniumbase`의 UC(Undetected-Chromedriver) 모드를 사용하여 웹사이트의 봇 감지를 우회합니다.
- **자동화**: GitHub Actions를 통해 정해진 시간마다 자동으로 실행됩니다.

## 기술 스택
- **Language**: Python 3.10+
- **Libraries**: SeleniumBase, BeautifulSoup4, Requests
- **Automation**: GitHub Actions
- **Data Storage**: JSON (Local file-based)

## 설정 및 사용 방법

### 1. 로컬 실행 환경 구축
```bash
# 저장소 클론
git clone https://github.com/사용자명/fmkoreaBot.git
cd fmkoreaBot

# 의존성 설치
pip install requests beautifulsoup4 seleniumbase
seleniumbase install chromedriver
```

### 2. 환경 변수 설정
스크립트 실행을 위해 디스코드 웹훅 URL이 필요합니다.
- 로컬 실행 시: 시스템 환경 변수에 `DISCORD_WEBHOOK` 등록
- GitHub Actions 사용 시: Repository Settings > Secrets and variables > Actions에 `DISCORD_WEBHOOK` 추가

### 3. 직접 실행
```bash
python main.py
```

## GitHub Actions 자동화
본 프로젝트는 `.github/workflows/scrape.yml` 설정에 따라 다음과 같이 자동 실행됩니다.

- **실행 주기**: 한국 시간 기준 **09:00 ~ 24:00 (3시간 간격, 1일 6회)**
- **데이터 업데이트**: 새로 수집된 글 번호는 자동으로 `data.json`에 커밋되어 반영됩니다.

## 주의 사항
- 펨코의 보안 정책 변경에 따라 수집이 일시적으로 제한될 수 있습니다.
- 과도한 요청은 사이트 이용 제한의 원인이 될 수 있으므로 실행 간격을 적절히 유지하십시오.
