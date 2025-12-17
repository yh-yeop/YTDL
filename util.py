import re
import webvtt
import os

FFMPEG_PATH = r"C:\ProgramData\chocolatey\bin"
OUTPUT_FOLDER = "output" if os.getcwd()!='C:\App' else "YTDL\output"

ARTIST_RULES = [
    {
        "keys": [
            "아이리 칸나 Music Official",
        ],
        "artist": "아이리 칸나 AIRI KANNA",
        "album": "Covers",
        "album_artist": "스텔라이브 StelLive"
    },
    {
        "keys": [
            "아야츠노 유니 AYATSUNO YUNI",
            "사키하네 후야 SAKIHANE HUYA",
            "시라유키 히나 SHIRAYUKI HINA",
            "네네코 마시로 NENEKO MASHIRO",
            "아카네 리제 AKANE LIZE",
            "아라하시 타비 ARAHASHI TABI",
            "텐코 시부키 TENKO SHIBUKI",
            "아오쿠모 린 AOKUMO RIN",
            "하나코 나나 HANAKO NANA",
            "유즈하 리코 YUZUHA RIKO",
        ],
        "album": "Covers",
        "album_artist": "스텔라이브 StelLive"
    }
]

DEFAULT_ALBUM = "YTDL"


REMOVE_NAMES = [
    "아이리 칸나", "AIRI KANNA",
    "아야츠노 유니", "AYATSUNO YUNI",
    "사키하네 후야", "SAKIHANE HUYA",
    "시라유키 히나", "SHIRAYUKI HINA",
    "네네코 마시로", "NENEKO MASHIRO",
    "아카네 리제", "AKANE LIZE",
    "아라하시 타비", "ARAHASHI TABI",
    "텐코 시부키", "TENKO SHIBUKI",
    "아오쿠모 린", "AOKUMO RIN",
    "하나코 나나", "HANAKO NANA",
    "유즈하 리코", "YUZUHA RIKO",
    " x "
]

X_DETECTED_ARTIST = "스텔라이브 StelLive"

def normalize_title(title: str) -> str:
    # cover / COVER / CoVeR → Cover
    return re.sub(r'cover', 'Cover', title, flags=re.IGNORECASE)


def vtt_to_lrc(vtt_path, lrc_path):
    ZERO_WIDTH = r"[\u200B\u200C\u200D\uFEFF]"

    def timestamp_to_ms(ts):
        h, m, s = ts.split(":")
        s, ms = s.split(".")
        return (
            int(h) * 3600 * 1000 +
            int(m) * 60 * 1000 +
            int(s) * 1000 +
            int(ms)
        )

    def ms_to_lrc(ms):
        minutes = ms // 60000
        seconds = (ms % 60000) // 1000
        ms = ms % 1000
        return f"[{minutes:02}:{seconds:02}.{ms:03}]"

    entries = []

    # ------------------------------
    # 1. 정제
    # ------------------------------
    for c in webvtt.read(vtt_path):
        ms = timestamp_to_ms(c.start)

        text = c.text.replace("\n", " ")
        text = text.replace("&nbsp;", "")
        text = re.sub(ZERO_WIDTH, "", text)
        text = text.strip()

        entries.append((ms, text))

    # ------------------------------
    # 2. 노이즈 제거
    # ------------------------------
    def is_noise(text):
        return bool(re.fullmatch(r"[!¡.,…?]+", text))

    cleaned = [(ms, t) for ms, t in entries if t and not is_noise(t)]

    # ------------------------------
    # 3. 문장별 중복 제거 (개선된 방식)
    # ------------------------------
    TH = 50  # ms
    merged = []
    last_seen = {}  # text -> last timestamp

    for ms, t in cleaned:
        if t in last_seen and (ms - last_seen[t]) <= TH:
            # 중복 → 건너뛰기
            continue

        merged.append((ms, t))
        last_seen[t] = ms

    # ------------------------------
    # 4. LRC 저장
    # ------------------------------
    with open(lrc_path, "w", encoding="utf-8") as f:
        for ms, t in merged:
            f.write(f"{ms_to_lrc(ms)}{t}\n")

    try:
        os.remove(vtt_path)
    except:
        pass