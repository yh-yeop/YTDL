from mutagen.id3 import ID3, TRCK
import os

def remove_track_number(mp3_path):
    try:
        audio = ID3(mp3_path)
    except:
        print(f"{mp3_path} : ID3 태그 없음, 건너뜀")
        return

    if 'TRCK' in audio:
        del audio['TRCK']
        audio.save()
        print(f"{mp3_path} : 곡 번호(TRCK) 삭제 완료")

# 특정 폴더 내 모든 mp3 처리
folder_path = r".\output\003\Favorite"
for root, dirs, files in os.walk(folder_path):
    for file in files:
        if file.lower().endswith(".mp3"):
            remove_track_number(os.path.join(root, file))
