from mutagen.id3 import ID3, TPE1, TPE2, TALB, TIT2, TDRC
import os

# 1. MP3 정보 수집
folder_path = r".\output\003\Favorite"
mp3_list = []

for root, dirs, files in os.walk(folder_path):
    for file in files:
        if file.lower().endswith(".mp3"):
            path = os.path.join(root, file)
            try:
                audio = ID3(path)
            except:
                continue

            album_tag = audio.get('TALB')
            album_artist_tag = audio.get('TPE2')
            title_tag = audio.get('TIT2')
            year_tag = audio.get('TDRC')

            if not (album_tag and album_artist_tag and title_tag):
                continue

            album = album_tag.text[0]
            album_artist = album_artist_tag.text[0]
            title = title_tag.text[0]
            year = year_tag.text[0] if year_tag else None

            if album == "Covers":
                mp3_list.append({
                    'path': path,
                    'album_artist': album_artist,
                    'album': album,
                    'title': title,
                    'year': year
                })

# 2. 앨범 아티스트 + 앨범명으로 그룹핑
from collections import defaultdict

albums = defaultdict(list)
for mp3 in mp3_list:
    key = (mp3['album_artist'], mp3['album'])
    albums[key].append(mp3)

# 3. 그룹 안에서 연도 → 제목 기준 정렬
for key, tracks in albums.items():
    sorted_tracks = sorted(
        tracks,
        key=lambda x: (x['year'] if x['year'] else '9999', x['title'])
    )
    print(f"\n앨범 아티스트: {key[0]} | 앨범: {key[1]}")
    for i, track in enumerate(sorted_tracks, 1):
        print(f"{i:02d}. {track['title']} ({track['year']})")
