from mutagen.id3 import ID3, TPE1, TPE2, TALB
import os

def fix_album_artist(mp3_path):
    try:
        audio = ID3(mp3_path)
    except:
        print(f"{mp3_path} : ID3 태그 없음, 건너뜀")
        return

    artist_tag = audio.get('TPE1')  # 아티스트
    album_tag = audio.get('TALB')   # 앨범
    album_artist_tag = audio.get('TPE2')  # 앨범 아티스트

    if not (artist_tag and album_tag):
        print(f"{mp3_path} : 아티스트 또는 앨범 정보 없음, 건너뜀")
        return

    artist = artist_tag.text[0]
    album = album_tag.text[0]
    album_artist = album_artist_tag.text[0] if album_artist_tag else ""

    if album == "Covers" and album_artist=="스텔라이브 StelLive" and artist!="스텔라이브 StelLive":
        print(f"{mp3_path} : 앨범 아티스트 '{album_artist}' → '{artist}'")
        audio['TPE2'] = TPE2(encoding=3, text=artist)
        audio.save()

# 특정 폴더 내 모든 mp3 처리
folder_path = r".\output\003\Favorite"  # 여기에 폴더 경로
for root, dirs, files in os.walk(folder_path):
    for file in files:
        if file.lower().endswith(".mp3"):
            fix_album_artist(os.path.join(root, file))