# 매장 좌석현황 카카오톡 연동 시스템

휴니크 POS(manage.empos.com)에서 좌석 정보를 가져와 회원들에게 카카오톡 채널로 공유하는 시스템.

## 구성

```
매장 PC (agent.py)  →  GitHub Gist (seats.json)  →  GitHub Pages (index.html)  →  회원 (카카오톡 링크)
```

- `agent.py` — 매장 PC에서 24시간 돌아가는 Python 스크립트. 30초마다 POS에서 좌석 데이터를 가져와 GitHub에 업로드
- `index.html` — 회원들이 볼 공개 웹페이지. 모바일 최적화된 좌석 배치도
- `config.ini` — 로그인 정보 설정 파일 (공개 저장소에 올리면 안 됨)

---

## 설치 (1회만 실행)

### 1단계 — GitHub 계정 및 Gist 준비

1. https://github.com 에서 계정 생성 (무료)

2. **Personal Access Token 발급**
   - https://github.com/settings/tokens/new 접속
   - Note: `seat-agent`
   - Expiration: `No expiration`
   - Select scopes: **`gist`** 체크
   - Generate token → 나오는 `ghp_xxxx...` 문자열을 복사해둠 (다시 못 봄)

3. **Gist 생성**
   - https://gist.github.com 접속
   - Filename: `seats.json`
   - Content: `{}`
   - **Create public gist** 클릭
   - 생성된 URL: `https://gist.github.com/본인아이디/abc123def456...`
   - 끝의 긴 문자열(`abc123def456...`)이 **Gist ID** — 복사해둠

### 2단계 — GitHub Pages에 웹페이지 배포

1. https://github.com/new 에서 새 저장소 생성
   - Repository name: `seat-viewer` (원하는 이름)
   - **Public** 선택
   - Create repository

2. `index.html` 파일 업로드
   - Add file → Upload files → `index.html` 드래그
   - 업로드 전에 파일 안의 아래 줄을 수정:
     ```javascript
     const GIST_RAW_URL = "https://gist.githubusercontent.com/YOUR_USERNAME/YOUR_GIST_ID/raw/seats.json";
     ```
     YOUR_USERNAME과 YOUR_GIST_ID를 본인 값으로 교체
   - Commit changes

3. **Pages 활성화**
   - Settings → Pages
   - Source: `Deploy from a branch`
   - Branch: `main` / `/(root)` → Save
   - 1-2분 후 `https://본인아이디.github.io/seat-viewer/` 주소로 접속 가능

### 3단계 — 매장 PC에 Python 설치

1. https://www.python.org/downloads/ 에서 Python 3.10+ 다운로드

2. 설치 시 **"Add Python to PATH"** 반드시 체크

3. 설치 완료 후 명령 프롬프트(cmd)에서 확인:
   ```
   python --version
   ```

### 4단계 — 에이전트 설정

1. `agent.py`, `config.ini.sample` 파일을 매장 PC의 폴더(예: `C:\seat-agent\`)에 저장

2. `config.ini.sample`을 복사해서 **`config.ini`**로 이름 변경

3. `config.ini`를 메모장으로 열어서 값 입력:
   ```ini
   [pos]
   base_url = https://manage.empos.com
   username = (POS 아이디)
   password = (POS 비밀번호)

   [github]
   token = ghp_xxxxxxxxxxxxxx  (1단계에서 발급한 토큰)
   gist_id = abc123def456       (1단계에서 만든 Gist의 ID)

   [agent]
   interval_seconds = 30
   ```

4. 필요한 패키지 설치 (명령 프롬프트):
   ```
   cd C:\seat-agent
   pip install requests
   ```

### 5단계 — API 엔드포인트 확인 (⚠️ 필수)

`agent.py` 안의 로그인 URL과 파라미터 이름은 예시입니다. 실제 값을 확인해서 맞춰야 합니다:

1. 크롬으로 `https://manage.empos.com` 접속
2. `F12` 눌러 개발자도구 열기 → **Network** 탭
3. 로그인 페이지에서 아이디/비번 입력 후 로그인 버튼 클릭
4. Network 탭에 뜬 요청 중 `login` 같은 이름의 항목 클릭
5. 확인할 정보:
   - **Request URL** — 전체 주소 (예: `https://manage.empos.com/auth/login`)
   - **Request Method** — 보통 `POST`
   - **Payload** 또는 **Form Data** — 파라미터 이름 (예: `user_id`, `user_pw`)

6. 그리고 로그인 후 좌석 현황 페이지에서:
   - Network 탭 필터에 `menu` 입력
   - F5로 새로고침
   - `menu` 요청 클릭 → Request URL 복사
   - Response 탭에서 JSON 구조 확인 (`data`, `locations` 배열이 어떻게 생겼는지)

7. `agent.py`의 다음 부분을 실제 값으로 교체:
   ```python
   login_url = f"{self.base_url}/login"           # 실제 경로로
   api_url   = f"{self.base_url}/api/menu"        # 실제 경로로
   payload = {"id": self.username, "pw": self.password}  # 실제 파라미터 이름으로
   ```

---

## 실행

### 수동 실행 (테스트)
```
cd C:\seat-agent
python agent.py
```

정상 동작 시 30초마다 다음과 같이 출력됩니다:
```
[09:00:15] 로그인 성공
[09:00:16] 좌석 12/30, 스터디룸 1/4, 사물함 8/20
[09:00:46] 좌석 13/30, 스터디룸 1/4, 사물함 8/20
```

### 자동 실행 (매일 PC 켤 때 자동 시작)

Windows 작업 스케줄러 등록:

1. 시작 메뉴에서 "작업 스케줄러" 검색
2. **작업 만들기**
3. 일반 탭 — 이름: `Seat Agent`, `사용자가 로그온했는지 여부에 관계없이 실행` 체크
4. 트리거 탭 — 새로 만들기 — 시작 시: `로그온할 때`
5. 동작 탭 — 새로 만들기
   - 프로그램: `python.exe`의 전체 경로 (예: `C:\Python310\python.exe`)
   - 인수: `agent.py`
   - 시작 위치: `C:\seat-agent`
6. 조건 탭 — `컴퓨터의 AC 전원이 켜져 있는 경우에만 작업 시작` 체크 해제

---

## 카카오톡 채널 연동

1. https://center-pf.kakao.com 에서 비즈니스 채널 생성 (무료)

2. 관리자 홈 → **홈 메뉴 관리** 또는 **채널 홈 설정**

3. **링크 버튼 추가**
   - 버튼명: `실시간 좌석현황`
   - 링크: `https://본인아이디.github.io/seat-viewer/`

4. 자동응답 설정 (선택):
   - 키워드 `좌석`, `자리`, `빈자리` 등록
   - 응답 메시지에 링크 포함

회원들은 카카오톡에서 채널을 친구 추가하고, 홈 화면의 버튼이나 "좌석"이라고 입력하면 좌석현황 페이지로 이동합니다.

---

## 문제 해결

**로그인 실패**
- `config.ini`의 아이디/비밀번호 다시 확인
- `agent.py`의 login URL과 파라미터 이름이 실제 사이트와 일치하는지 확인 (5단계)

**Gist 업로드 실패**
- Personal Access Token의 `gist` 권한이 체크됐는지 확인
- 토큰이 만료되지 않았는지 확인

**웹페이지에서 "연결 실패"**
- `index.html`의 `GIST_RAW_URL`이 정확한지 확인
- Gist가 **Public**인지 확인 (Secret Gist는 접근 불가)
- 브라우저 개발자도구 Console 탭의 에러 메시지 확인

**좌석이 안 보임**
- 에이전트 콘솔창에 업로드 성공 로그가 뜨는지 확인
- Gist 페이지에서 `seats.json`이 실제로 업데이트되는지 확인

---

## 보안 주의사항

- `config.ini`는 **절대 GitHub에 업로드하지 마세요** (POS 비밀번호 포함)
- Personal Access Token은 외부에 노출되면 즉시 재발급
- GitHub Pages로 공개되는 좌석 정보에는 개인정보(전화번호, 이름)가 포함되지 않도록 `agent.py`의 `extract_seat_summary` 함수가 필터링합니다

## 비용

- 전부 무료 (GitHub 무료 계정, Python, 카카오톡 비즈니스 채널 기본 기능)
- 매장 PC의 전기 + 인터넷 비용만 들어감
