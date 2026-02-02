import os
from mutagen.easyid3 import EasyID3

TARGET_DIR = r".\output\000"

# NAMES = [
#     "아이리 칸나 AIRI KANNA",
#     "아야츠노 유니 AYATSUNO YUNI",
#     "사키하네 후야 SAKIHANE HUYA",
#     "시라유키 히나 SHIRAYUKI HINA",
#     "네네코 마시로 NENEKO MASHIRO",
#     "아카네 리제 AKANE LIZE",
#     "아라하시 타비 ARAHASHI TABI",
#     "텐코 시부키 TENKO SHIBUKI",
#     "아오쿠모 린 AOKUMO RIN",
#     "하나코 나나 HANAKO NANA",
#     "유즈하 리코 YUZUHA RIKO",
# ]

NAMES=["스텔라이브 StelLive"]

# 매핑: 전체이름 -> 한글만
# NAME_MAP = {n: n.split(" ")[0] + " " + n.split(" ")[1] for n in NAMES}
NAME_MAP = {n: n.split(" ")[0]for n in NAMES}

for root, _, files in os.walk(TARGET_DIR):
    for file in files:
        if not file.lower().endswith(".mp3"):
            continue

        path = os.path.join(root, file)

        try:
            audio = EasyID3(path)
        except Exception:
            continue

        changed = False

        for tag in ("artist", "albumartist"):
            if tag not in audio:
                continue

            value = audio[tag][0]

            for full, kor in NAME_MAP.items():
                if full in value:
                    audio[tag] = kor
                    changed = True
                    break

        if changed:
            audio.save()
