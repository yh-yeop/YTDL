import os
import re
from mutagen import File
from mutagen.id3 import ID3, ID3NoHeaderError

# TARGET_DIR = r".\output\003\Favorite"
# TARGET_DIR = r".\output\003\Test"
TARGET_DIR = r".\output\001"
YEAR_RE = re.compile(r'(19|20)\d{2}')

def extract_year(value):
    if not value:
        return None
    m = YEAR_RE.search(str(value))
    return m.group(0) if m else None

for root, _, files in os.walk(TARGET_DIR):
    for file in files:
        if not file.lower().endswith(".mp3"):
            continue

        path = os.path.join(root, file)
        found = []

        try:
            audio = File(path, easy=False)
        except Exception as e:
            print(f"[ERR] {path} ({e})")
            continue

        # 1️⃣ ID3v2
        try:
            tags = ID3(path)
            for key in ("TDRC", "TYER", "TDAT"):
                if key in tags:
                    y = extract_year(tags[key])
                    if y:
                        found.append(f"ID3v2:{key}={y}")
        except ID3NoHeaderError:
            pass

        # 2️⃣ ID3v1
        if audio and audio.tags:
            y = extract_year(audio.tags.get("YEAR"))
            if y:
                found.append(f"ID3v1:YEAR={y}")

        # 3️⃣ APEv2
        if audio and audio.tags:
            for k in ("Year", "Date"):
                if k in audio.tags:
                    y = extract_year(audio.tags[k])
                    if y:
                        found.append(f"APEv2:{k}={y}")

        # 4️⃣ RIFF INFO (mutagen에선 raw 접근)
        if audio and hasattr(audio, "info") and hasattr(audio, "tags"):
            for k in audio.tags.keys():
                if "ICRD" in k:
                    y = extract_year(audio.tags[k])
                    if y:
                        found.append(f"RIFF:{k}={y}")

        if not found:
            print(f"[MISS] {path}")
        else:
            print(f"[FOUND] {path}")
            for f in found:
                print(f"    └─ {f}")