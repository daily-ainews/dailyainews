# 데일리 AI — GitHub Pages 버전

Claude 없이도 열리고, 6시간마다 자동으로 새 기사를 받아오는 정적 사이트입니다.

## 올리는 방법 (5분)

1. **github.com** 에서 새 저장소(repository)를 만듭니다. (예: `daily-ai`, Public으로)
2. 이 폴더 안의 파일을 전부 그 저장소에 업로드합니다.
   - 웹에서 할 거면: 저장소 페이지 → `Add file` → `Upload files` → 이 폴더의 내용을 통째로 끌어다 놓기
   - `.github/workflows/update-news.yml` 처럼 숨김 폴더(`.github`)도 반드시 같이 올라가야 합니다. 드래그 앤 드롭하면 폴더째로 올라가지만, 혹시 안 보이면 깃허브 데스크톱 앱이나 `git` 명령으로 올리는 걸 추천합니다.
3. 저장소 **Settings → Pages** 로 이동 → "Build and deployment" 에서 Source를 **Deploy from a branch** 로, Branch는 **main / (root)** 로 설정 → Save.
   - 1~2분 뒤 `https://<내아이디>.github.io/<저장소이름>/` 주소가 생깁니다.
4. 저장소 **Settings → Actions → General** 로 이동 → "Workflow permissions" 을 **Read and write permissions** 로 바꾸고 저장.
   (이게 있어야 자동 수집 봇이 `data.json`을 저장소에 다시 커밋할 수 있어요.)
5. 저장소 **Actions** 탭 → `Update AI news` 워크플로 선택 → **Run workflow** 버튼으로 한 번 수동 실행해 보면 바로 확인할 수 있습니다.

그 이후로는 6시간마다 자동으로 실행됩니다. 주기를 바꾸고 싶으면 `.github/workflows/update-news.yml` 안의
`cron: "0 */6 * * *"` 숫자만 바꾸면 돼요 (예: 매일 한 번이면 `"0 0 * * *"`).

## 페이지에 있는 기능

- **새로고침 아이콘**: `data.json`을 다시 읽어옵니다. 다만 실시간 검색을 하는 게 아니라, 마지막으로 봇이 저장해 둔 내용을 다시 불러오는 것입니다. 지금 당장 최신 내용이 필요하면 위 4번의 Actions 수동 실행을 쓰세요.
- **검색, 다크·라이트 모드, 목차(오늘/지난 소식), 공유 버튼**: 그대로 있습니다.
- **공유 버튼**: 기기의 공유 시트 → 클립보드 복사 → 그래도 안 되면 링크를 직접 복사할 수 있는 작은 창이 뜹니다. GitHub Pages는 평범한 웹사이트라서(Claude 미리보기 같은 제한된 환경이 아니라서) 대부분 기기에서 공유 시트나 클립보드 복사가 바로 될 거예요.

## 알아두면 좋은 점

- **"왜 봐야 하는지" 한 줄**: Claude가 매번 써주던 개인화된 한 줄 대신, 지금은 묶음별로 고정된 문구예요 (예: "생성 엔진 자체의 업데이트 소식이에요"). 완전히 무료로, API 키 없이 돌아가게 하려다 보니 생긴 트레이드오프입니다.
  - 정말 그 한 줄을 Claude가 써주길 원한다면: Anthropic API 키를 발급받아 저장소 **Settings → Secrets and variables → Actions** 에 `ANTHROPIC_API_KEY`로 등록하고, `update_news.py`에 기사 제목들을 Claude API로 보내 한 줄씩 받아오는 단계를 추가하면 됩니다. 이 경우 API 사용량만큼 비용이 발생하고, Claude 채팅창을 직접 열 필요는 없어요. 원하시면 그 버전도 만들어 드릴 수 있어요.
- **공모전 마감일**: 기사 제목에서 날짜 패턴을 찾아 자동으로 뽑아봅니다. 못 찾으면 "확인 필요"로 표시돼요 — 지원 전엔 꼭 원문을 확인하세요.
- **뉴스 출처**: Google 뉴스 RSS만 사용해서 API 키가 필요 없어요. 다만 링크가 news.google.com을 한 번 거쳐서 원문으로 넘어가는 구조라, 클릭하면 잠깐의 리다이렉트가 있을 수 있어요(정상입니다).
- **로컬에서 테스트할 때**: `index.html`을 더블클릭해서 직접 열면 브라우저 보안 정책 때문에 `data.json`을 못 읽어요. `python3 -m http.server` 로 간단한 로컬 서버를 띄워서 열어보세요. GitHub Pages에 올리면 이 문제는 없습니다.

## 파일 구성

- `index.html` — 화면
- `data.json` — 기사 데이터 (봇이 주기적으로 덮어씀)
- `update_news.py` — 뉴스 수집 스크립트 (표준 라이브러리만 사용, 설치 필요 없음)
- `.github/workflows/update-news.yml` — 자동 실행 설정
