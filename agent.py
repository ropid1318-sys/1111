"""
매장 좌석 현황 에이전트
======================
매장 POS PC에서 실행됩니다. 아침에 한 번 실행하면 하루 종일
좌석 정보를 자동으로 가져와서 공개 저장소에 업로드합니다.

사용법:
    1. config.ini 파일에 로그인 정보와 GitHub 토큰 입력
    2. python agent.py 실행
    3. 콘솔창을 닫지 않고 그대로 둡니다
"""

import requests
import json
import time
import configparser
import sys
import os
from datetime import datetime
from pathlib import Path


# ============================================================
# 설정 로드
# ============================================================
def load_config():
    config = configparser.ConfigParser()
    config_path = Path(__file__).parent / "config.ini"

    if not config_path.exists():
        print("[오류] config.ini 파일이 없습니다.")
        print(f"경로: {config_path}")
        print("config.ini.sample을 복사해서 config.ini로 이름을 바꾸고 값을 입력해주세요.")
        sys.exit(1)

    config.read(config_path, encoding="utf-8")
    return config


# ============================================================
# POS 로그인 및 세션 유지
# ============================================================
class PosClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        })
        self.logged_in = False

    def login(self):
        """
        POS 로그인.
        ※ 실제 로그인 URL과 파라미터 이름은 manage.empos.com의
           Network 탭을 통해 확인한 후 여기서 조정하세요.
        """
        login_url = f"{self.base_url}/login"  # 실제 경로로 교체 필요
        payload = {
            "id": self.username,       # 실제 파라미터 이름으로 교체 필요
            "pw": self.password,       # (예: user_id / user_pw 등)
        }

        try:
            r = self.session.post(login_url, data=payload, timeout=10)
            r.raise_for_status()

            if r.text and ("success" in r.text.lower() or r.status_code == 200):
                self.logged_in = True
                print(f"[{_now()}] 로그인 성공")
                return True
            else:
                print(f"[{_now()}] 로그인 실패: {r.text[:200]}")
                return False
        except requests.RequestException as e:
            print(f"[{_now()}] 로그인 오류: {e}")
            return False

    def fetch_seatmap(self):
        """
        좌석 배치도 데이터 가져오기.
        원본 POS 페이지에서 config.api + "menu" 로 호출하는 엔드포인트.
        """
        api_url = f"{self.base_url}/api/menu"  # 실제 경로로 교체 필요

        try:
            r = self.session.post(
                api_url,
                data={"cat": "seatmap"},
                timeout=10
            )
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print(f"[{_now()}] seatmap 가져오기 오류: {e}")
            return None
        except json.JSONDecodeError:
            print(f"[{_now()}] JSON 파싱 오류. 세션이 만료되었을 가능성")
            self.logged_in = False
            return None

    def fetch_locker(self):
        """사물함 배치도 데이터 가져오기"""
        api_url = f"{self.base_url}/api/menu"

        try:
            r = self.session.post(
                api_url,
                data={"cat": "locker"},
                timeout=10
            )
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, json.JSONDecodeError):
            return None


# ============================================================
# 공개 저장소 업로드 (GitHub Gist 방식)
# ============================================================
class GistUploader:
    """
    GitHub Gist로 JSON 업로드.
    Gist는 무료이고 CORS가 허용되어 정적 웹페이지에서 바로 읽을 수 있습니다.
    """

    def __init__(self, token, gist_id):
        self.token = token
        self.gist_id = gist_id
        self.api_url = f"https://api.github.com/gists/{gist_id}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def upload(self, data):
        payload = {
            "files": {
                "seats.json": {
                    "content": json.dumps(data, ensure_ascii=False, indent=2)
                }
            }
        }

        try:
            r = requests.patch(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            r.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[{_now()}] 업로드 오류: {e}")
            return False


# ============================================================
# 유틸리티
# ============================================================
def _now():
    return datetime.now().strftime("%H:%M:%S")


def extract_seat_summary(seatmap_data, locker_data):
    """
    원본 JSON에서 회원에게 공개할 정보만 추출.
    개인정보(전화번호, 이름 등)는 제거합니다.
    """
    result = {
        "updated_at": datetime.now().isoformat(),
        "seatmap": {"locations": [], "background": None},
        "locker": {"locations": [], "background": None},
        "summary": {
            "seat_used": 0, "seat_total": 0,
            "studyroom_used": 0, "studyroom_total": 0,
            "locker_used": 0, "locker_total": 0,
        }
    }

    # 좌석 처리
    if seatmap_data and "locations" in seatmap_data:
        for loc in seatmap_data["locations"]:
            if loc.get("map_status") == "n":
                continue

            is_studyroom = loc.get("category") == "스터디룸"
            is_available = loc.get("status") is True

            if is_studyroom:
                result["summary"]["studyroom_total"] += 1
                if not is_available:
                    result["summary"]["studyroom_used"] += 1
            else:
                result["summary"]["seat_total"] += 1
                if not is_available:
                    result["summary"]["seat_used"] += 1

            # 회원 공개용 — 좌석 위치/번호/상태만
            result["seatmap"]["locations"].append({
                "number": loc.get("number"),
                "name": loc.get("name", ""),
                "category": loc.get("category", ""),
                "status": is_available,   # True = 비어있음
                "position": loc.get("position"),
                "size": loc.get("size"),
                "rotate": loc.get("rotate", 0),
                "images": loc.get("images"),
            })

        # 배경 이미지 찾기
        for item in seatmap_data.get("data", []):
            if item.get("category") in ("bg", "seatmap"):
                result["seatmap"]["background"] = item.get("file")
                break

    # 사물함 처리
    if locker_data and "locations" in locker_data:
        for loc in locker_data["locations"]:
            if loc.get("map_status") == "n":
                continue

            result["summary"]["locker_total"] += 1
            if loc.get("status") is False:
                result["summary"]["locker_used"] += 1

            result["locker"]["locations"].append({
                "number": loc.get("number"),
                "name": loc.get("name", ""),
                "status": loc.get("status") is True,
                "position": loc.get("position"),
                "size": loc.get("size"),
                "rotate": loc.get("rotate", 0),
                "images": loc.get("images"),
            })

        for item in locker_data.get("data", []):
            if item.get("category") in ("bg", "lockermap"):
                result["locker"]["background"] = item.get("file")
                break

    return result


# ============================================================
# 메인 루프
# ============================================================
def main():
    print("=" * 60)
    print("  매장 좌석현황 에이전트")
    print("=" * 60)

    config = load_config()

    pos_url = config["pos"]["base_url"]
    pos_id = config["pos"]["username"]
    pos_pw = config["pos"]["password"]
    interval = int(config.get("agent", "interval_seconds", fallback="30"))

    gist_token = config["github"]["token"]
    gist_id = config["github"]["gist_id"]

    client = PosClient(pos_url, pos_id, pos_pw)
    uploader = GistUploader(gist_token, gist_id)

    print(f"대상 POS: {pos_url}")
    print(f"업로드 주기: {interval}초")
    print(f"Ctrl+C로 종료")
    print("=" * 60)

    consecutive_failures = 0

    while True:
        try:
            if not client.logged_in:
                if not client.login():
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        print(f"[{_now()}] 연속 로그인 실패. 5분 대기 후 재시도")
                        time.sleep(300)
                        consecutive_failures = 0
                        continue
                    time.sleep(30)
                    continue
                consecutive_failures = 0

            seatmap = client.fetch_seatmap()
            locker = client.fetch_locker()

            if seatmap is None:
                time.sleep(10)
                continue

            summary = extract_seat_summary(seatmap, locker)

            s = summary["summary"]
            print(f"[{_now()}] "
                  f"좌석 {s['seat_used']}/{s['seat_total']}, "
                  f"스터디룸 {s['studyroom_used']}/{s['studyroom_total']}, "
                  f"사물함 {s['locker_used']}/{s['locker_total']}")

            if uploader.upload(summary):
                pass  # 조용히 성공
            else:
                print(f"[{_now()}] 업로드 실패 (다음 주기에 재시도)")

            time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n[{_now()}] 에이전트 종료")
            break
        except Exception as e:
            print(f"[{_now()}] 예상치 못한 오류: {e}")
            time.sleep(30)


if __name__ == "__main__":
    main()
