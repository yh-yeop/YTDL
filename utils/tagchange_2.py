import os
from mutagen.id3 import ID3, ID3NoHeaderError, TDRC, TYER

TARGET_DIR = r".\output\001"

for root, _, files in os.walk(TARGET_DIR):
    print('a')
    for file in files:
        if not file.lower().endswith(".mp3"):
            continue

        path = os.path.join(root, file)

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
                continue

            # 3. TDRC로 재설정
            tags.add(TDRC(encoding=3, text=year))
            tags.add(TYER(encoding=3, text=year))

            # 4. ID3v2.4로 저장
            tags.save(path, v2_version=4)

            print(f"[OK] {path} → DATE={year}")

        except Exception as e:
            print(f"[ERR] {path} ({e})")