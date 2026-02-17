import os

folder = r"C:\Users\hoyaj\Music\Musics\Favorite"

# 파일 목록 수집
files = os.listdir(folder)

# 확장자별로 분리
mp3_names = {os.path.splitext(f)[0] for f in files if f.lower().endswith(".mp3")}
lrc_names = {os.path.splitext(f)[0] for f in files if f.lower().endswith(".lrc")}

# lrc 없는 mp3만 필터링
mp3_without_lrc = sorted(mp3_names - lrc_names)

# 출력
for name in mp3_without_lrc:
    print(name)