import os
import time
import requests
from datetime import datetime

# =========================================================
# 설정
# =========================================================

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "10"))

# 메가박스 상영정보 조회 API
MEGABOX_URL = (
    "https://www.megabox.co.kr/on/oh/ohb/"
    "SimpleBooking/selectBokdList.do"
)

# 감시 대상
THEATER_NAME = "메가박스 수원역"
MOVIE_NAME = "오디세이"

# 앞에서 메가박스 개발자도구에서 확인한 값
BRANCH_NO = "0052"
MOVIE_NO = "26018900"

# 감시 날짜
WATCH_DATES = [
    "20260828",
    "20260829",
    "20260830",
]

# =========================================================
# HTTP 세션
# =========================================================

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://www.megabox.co.kr",
    "Referer": "https://www.megabox.co.kr/booking",
    "X-Requested-With": "XMLHttpRequest",
})


# =========================================================
# Discord
# =========================================================

def send_discord(message):
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL이 설정되지 않았습니다.")
        return

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": message},
            timeout=10,
        )

        if response.status_code in (200, 204):
            print("Discord 알림 전송 완료")
        else:
            print(
                f"Discord 전송 실패: "
                f"{response.status_code} {response.text[:200]}"
            )

    except Exception as e:
        print(f"Discord 전송 오류: {e}")


# =========================================================
# 메가박스 조회
# =========================================================

def get_schedules(play_date):

    payload = {
        "arrMovieNo": MOVIE_NO,
        "playDe": play_date,

        "areaCd1": "30",
        "areaCd2": "",
        "areaCd3": "",
        "areaCd4": "",
        "areaCd5": "",

        "arrMovieNo1": MOVIE_NO,

        "brchAll": "30",
        "brchNo1": BRANCH_NO,
        "brchNo2": "",
        "brchNo3": "",
        "brchNo4": "",
        "brchNo5": "",

        "brchNoListCnt": "1",
        "brchSpcl": "",

        "movieNo1": MOVIE_NO,
        "movieNo2": "",
        "movieNo3": "",

        "sellChnlCd": "",
        "spclbYn1": "N",
        "spclbYn2": "",
        "spclbYn3": "",
        "spclbYn4": "",
        "spclbYn5": "",

        "theabKindCd1": "30",
        "theabKindCd2": "",
        "theabKindCd3": "",
        "theabKindCd4": "",
        "theabKindCd5": "",
    }

    response = session.post(
        MEGABOX_URL,
        data=payload,
        timeout=15,
    )

    print(f"[{play_date}] HTTP {response.status_code}")

    response.raise_for_status()

    data = response.json()

    # 실제 상영 회차 목록
    schedules = data.get("movieFormList", [])

    if schedules is None:
        schedules = []

    return schedules


# =========================================================
# 회차 고유값 생성
# =========================================================

def schedule_id(item):

    # 메가박스 응답에서 회차번호가 있으면 최우선 사용
    play_schedule_no = str(
        item.get("playSchdlNo")
        or item.get("playScheduleNo")
        or ""
    )

    if play_schedule_no:
        return play_schedule_no

    # 회차번호가 없는 경우 대비
    return "|".join([
        str(item.get("playDe", "")),
        str(item.get("playStartTime", "")),
        str(item.get("playEndTime", "")),
        str(item.get("theabNo", "")),
        str(item.get("theabNm", "")),
    ])


# =========================================================
# 회차 표시
# =========================================================

def schedule_description(item):

    start = (
        item.get("playStartTime")
        or item.get("playStartTm")
        or item.get("playStartTimeText")
        or ""
    )

    theater = (
        item.get("theabExpoNm")
        or item.get("theabNm")
        or item.get("theabKindNm")
        or ""
    )

    if start and len(str(start)) == 4:
        start = f"{str(start)[:2]}:{str(start)[2:]}"

    if theater and start:
        return f"{theater} / {start}"

    if start:
        return str(start)

    if theater:
        return str(theater)

    return "새로운 상영 회차"


# =========================================================
# 시작
# =========================================================

print("=" * 45)
print("메가박스 예매 오픈 감시 시작")
print(f"극장: {THEATER_NAME}")
print(f"영화: {MOVIE_NAME}")
print(f"감시 날짜: {WATCH_DATES}")
print(f"확인 주기: {CHECK_INTERVAL}초")
print("=" * 45)


# 날짜별 기존 회차 저장
known_schedules = {}

# 최초 조회
for date in WATCH_DATES:

    try:
        schedules = get_schedules(date)

        ids = {
            schedule_id(item)
            for item in schedules
        }

        known_schedules[date] = ids

        print(
            f"[{datetime.now()}] "
            f"{date} 현재 회차 {len(schedules)}개"
        )

    except Exception as e:
        print(f"[{date}] 최초 조회 오류: {e}")
        known_schedules[date] = set()


# 시작 확인 알림
date_text = "\n".join(
    f"📅 {d[:4]}.{d[4:6]}.{d[6:]}"
    for d in WATCH_DATES
)

send_discord(
    "✅ **메가박스 감시 시작**\n\n"
    f"🏢 {THEATER_NAME}\n"
    f"🎬 {MOVIE_NAME}\n\n"
    f"{date_text}\n\n"
    f"⏱️ 확인 주기: {CHECK_INTERVAL}초"
)


# =========================================================
# 반복 감시
# =========================================================

while True:

    for date in WATCH_DATES:

        try:
            schedules = get_schedules(date)

            current = {
                schedule_id(item): item
                for item in schedules
            }

            current_ids = set(current.keys())

            previous_ids = known_schedules.get(date, set())

            new_ids = current_ids - previous_ids

            print(
                f"[{datetime.now()}] "
                f"{date} 현재 회차 {len(schedules)}개"
            )

            # 새 회차 발견
            if new_ids:

                new_items = [
                    current[sid]
                    for sid in new_ids
                ]

                details = "\n".join(
                    f"🎟️ {schedule_description(item)}"
                    for item in new_items
                )

                formatted_date = (
                    f"{date[:4]}.{date[4:6]}.{date[6:]}"
                )

                message = (
                    "🚨🚨 **메가박스 예매 오픈!** 🚨🚨\n\n"
                    f"🏢 **{THEATER_NAME}**\n"
                    f"🎬 **{MOVIE_NAME}**\n"
                    f"📅 **{formatted_date}**\n\n"
                    f"🔥 새로운 회차: **{len(new_ids)}개**\n\n"
                    f"{details}\n\n"
                    "⚡ 메가박스 앱에서 바로 확인하세요!"
                )

                send_discord(message)

                print(
                    f"!!! {date} 새로운 회차 "
                    f"{len(new_ids)}개 발견 !!!"
                )

            known_schedules[date] = current_ids

        except Exception as e:

            print(
                f"[{datetime.now()}] "
                f"[{date}] 조회 오류: {e}"
            )

    time.sleep(CHECK_INTERVAL)
