import re
import webvtt
import os
from mutagen.id3 import ID3, ID3NoHeaderError, TDRC, TYER

FFMPEG_PATH = r"C:\ProgramData\chocolatey\bin"
OUTPUT_FOLDER = "output" if os.getcwd() != r"C:\App" else "YTDL\output"

ARTIST_RULES = [
    {
        "keys": ["아이리 칸나 Music Official", "Airi Kanna"],
        "artist": "아이리 칸나",
        "album": "Covers",
        "album_artist": "아이리 칸나",
        "cover_image": "covers/Kanna.png"
    },
    {
        "keys": ["Hebi.", "Hebi"],
        "artist": "Hebi",
        "album": "Hebi. Cover",
        "album_artist": "Hebi",
        "cover_image": "covers/Hebi.png"
    },
    {
        "keys": ["아야츠노 유니 AYATSUNO YUNI", "Ayatsuno Yuni - Topic"],
        "artist": "아야츠노 유니",
        "album": "Covers",
        "album_artist": "아야츠노 유니",
        "cover_image": "covers/Yuni.png"
    },
    {
        "keys": ["사키하네 후야 SAKIHANE HUYA"],
        "artist": "사키하네 후야",
        "album": "Covers",
        "album_artist": "사키하네 후야",
        "cover_image": "covers/Huya.png"
    },
    {
        "keys": ["시라유키 히나 SHIRAYUKI HINA"],
        "artist": "시라유키 히나",
        "album": "Covers",
        "album_artist": "시라유키 히나",
        "cover_image": "covers/Hina.png"
    },
    {
        "keys": ["네네코 마시로 NENEKO MASHIRO"],
        "artist": "네네코 마시로",
        "album": "Covers",
        "album_artist": "네네코 마시로",
        "cover_image": "covers/Mashiro.png"
    },
    {
        "keys": ["아카네 리제 AKANE LIZE"],
        "artist": "아카네 리제",
        "album": "Covers",
        "album_artist": "아카네 리제",
        "cover_image": "covers/Lize.png"
    },
    {
        "keys": ["아라하시 타비 ARAHASHI TABI"],
        "artist": "아라하시 타비",
        "album": "Covers",
        "album_artist": "아라하시 타비",
        "cover_image": "covers/Tabi.png"
    },
    {
        "keys": ["텐코 시부키 TENKO SHIBUKI"],
        "artist": "텐코 시부키",
        "album": "Covers",
        "album_artist": "텐코 시부키",
        "cover_image": "covers/Shibuki.png"
    },
    {
        "keys": ["아오쿠모 린 AOKUMO RIN"],
        "artist": "아오쿠모 린",
        "album": "Covers",
        "album_artist": "아오쿠모 린",
        "cover_image": "covers/Rin.png"
    },
    {
        "keys": ["하나코 나나 HANAKO NANA"],
        "artist": "하나코 나나",
        "album": "Covers",
        "album_artist": "하나코 나나",
        "cover_image": "covers/Nana.png"
    },
    {
        "keys": ["유즈하 리코 YUZUHA RIKO"],
        "artist": "유즈하 리코",
        "album": "Covers",
        "album_artist": "유즈하 리코",
        "cover_image": "covers/Riko.png"
    },
    {
        "keys": ["스텔라이브 StelLive Official"],
        "artist": "스텔라이브",
        "album": "Covers",
        "album_artist": "스텔라이브",
        "cover_image": "covers/StelLive.png"
    }
]

DEFAULT_ALBUM = "Covers"

REMOVE_NAMES = [
    "스텔라이브", "StelLive",
    "아이리 칸나", "AIRI KANNA",
    "아야츠노 유니", "AYATSUNO YUNI",
    "사키하네 후야", "SAKIHANE HUYA",
    "시라유키 히나", "SHIRAYUKI HINA",
    "네네코 마시로", "NENEKO MASHIRO",
    "아카네 리제",  "AKANE LIZE",
    "아라하시 타비", "ARAHASHI TABI",
    "텐코 시부키", "TENKO SHIBUKI",
    "아오쿠모 린", "AOKUMO RIN",
    "하나코 나나", "HANAKO NANA",
    "유즈하 리코", "YUZUHA RIKO",
    "헤비", "Hebi", 
    " x ", " - "
]

X_DETECTED_ARTIST = "스텔라이브"

def normalize_title(title: str) -> str:
    # cover / COVER / CoVeR → Cover
    return re.sub(r'cover', 'Cover', title, flags=re.IGNORECASE)

def vtt_to_lrc(vtt_path, lrc_path):
    ZERO_WIDTH = r"[\u200B\u200C\u200D\uFEFF]"

    def timestamp_to_ms(ts):
        h, m, s = ts.split(":")
        s, ms = s.split(".")
        return int(h)*3600*1000 + int(m)*60*1000 + int(s)*1000 + int(ms)

    def ms_to_lrc(ms):
        minutes = ms // 60000
        seconds = (ms % 60000) // 1000
        ms = ms % 1000
        return f"[{minutes:02}:{seconds:02}.{ms:03}]"

    entries = []

    for c in webvtt.read(vtt_path):
        ms = timestamp_to_ms(c.start)
        text = c.text.replace("\n", " ").replace("&nbsp;", "")
        text = re.sub(r'<[^>]+>', '', text)  # HTML 태그 제거 (특수효과 태그)
        text = re.sub(ZERO_WIDTH, "", text).strip()
        entries.append((ms, text))

    def is_noise(text):
        return bool(re.fullmatch(r"[!¡.,…?]+", text))

    cleaned = [(ms, t) for ms, t in entries if t and not is_noise(t)]

    # ------------------------------
    # 3. 연속 중복 제거 (TH 이하, 마지막 추가 기준)
    # ------------------------------
    TH = 110  # 코드에서 직접 조정 가능
    merged = []
    last_added_ms = {}  # text -> 마지막 LRC에 추가된 ms

    for ms, t in cleaned:
        if t in last_added_ms and (ms - last_added_ms[t]) <= TH:
            continue  # 마지막 추가 이후 TH 이하면 제거
        merged.append((ms, t))
        last_added_ms[t] = ms

    with open(lrc_path, "w", encoding="utf-8") as f:
        for ms, t in merged:
            f.write(f"{ms_to_lrc(ms)}{t}\n")

    try:
        os.remove(vtt_path)
    except:
        pass


def srv3_to_lrc(srv3_path, lrc_path):
    from xml.etree import ElementTree as ET

    def timestamp_to_ms(ts):
        return int(float(ts) * 1000)

    def ms_to_lrc(ms):
        minutes = ms // 60000
        seconds = (ms % 60000) // 1000
        ms = ms % 1000
        return f"[{minutes:02}:{seconds:02}.{ms:03}]"

    try:
        tree = ET.parse(srv3_path)
        root = tree.getroot()
    except:
        print(f"[오류] srv3 파싱 실패: {srv3_path}")
        return

    entries = []
    for text_elem in root:
        if text_elem.tag == 'text':
            start = text_elem.get('start')
            dur = text_elem.get('dur')  # 사용하지 않음
            text = text_elem.text or ''
            text = re.sub(r'<[^>]+>', '', text).strip()  # 특수 효과 태그 제거
            if text:
                ms = timestamp_to_ms(start)
                entries.append((ms, text))

    def is_noise(text):
        return bool(re.fullmatch(r"[!¡.,…?]+", text))

    cleaned = [(ms, t) for ms, t in entries if t and not is_noise(t)]

    TH = 110
    merged = []
    last_added_ms = {}

    for ms, t in cleaned:
        if t in last_added_ms and (ms - last_added_ms[t]) <= TH:
            continue
        merged.append((ms, t))
        last_added_ms[t] = ms

    with open(lrc_path, "w", encoding="utf-8") as f:
        for ms, t in merged:
            f.write(f"{ms_to_lrc(ms)}{t}\n")

    try:
        os.remove(srv3_path)
    except:
        pass


def year_fix(path):
    try:
        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            tags = ID3()

        year = None

        # 1. 기존 연도 가져오기
        if "TDRC" in tags:
            year = str(tags["TDRC"])
        elif "TYER" in tags:
            year = str(tags["TYER"])

        if not year:
            print(f"[SKIP] 연도 없음: {path}")

        # 3. TDRC로 재설정
        tags.add(TDRC(encoding=3, text=year))
        tags.add(TYER(encoding=3, text=year))

        # 4. ID3v2.4로 저장
        tags.save(path, v2_version=4)

        print(f"[OK] {path} → DATE={year}")

    except Exception as e:
        print(f"[ERR] {path} ({e})")