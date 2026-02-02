import os
import subprocess
import re
import tempfile
from mutagen.id3 import ID3

FFMPEG = r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"
TARGET_DIR = r".\output\003\Test"
YEAR_RE = re.compile(r'(19|20)\d{2}')

def get_year(path):
    try:
        tags = ID3(path)
        if "TDRC" in tags:
            m = YEAR_RE.search(str(tags["TDRC"]))
            if m:
                return m.group(0)
    except:
        pass
    return None

for root, _, files in os.walk(TARGET_DIR):
    for f in files:
        if not f.lower().endswith(".mp3"):
            continue

        src = os.path.join(root, f)
        year = get_year(src)
        if not year:
            continue

        # 임시 파일 (같은 디스크)
        tmp = src + ".__tmp__.mp3"

        cmd = [
            FFMPEG, "-y",
            "-i", src,
            "-map_metadata", "-1",
            "-vn",
            "-acodec", "copy",
            "-metadata", f"date={year}",
            "-id3v2_version", "4",
            tmp
        ]

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if os.path.exists(tmp):
            os.replace(tmp, src)  # 원자적 교체
            print(f"[FIX] {src} → TDRC={year}")
        else:
            print(f"[FAIL] {src}")