import os
import re
import subprocess
from util import *
from yt_dlp import YoutubeDL
from mutagen.id3 import ID3, ID3NoHeaderError, TDRC, TYER

FFMPEG_PATH = r"C:\ProgramData\chocolatey\bin"
OUTPUT_FOLDER = "output" if os.getcwd() != 'C:\\App' else "YTDL\\output"

# -----------------------------
# 파일명 안전화
# -----------------------------
def sanitize_filename(filename: str) -> str:
    return re.sub(r'[\\/:*?"<>|ㅣ]', '', filename)

# -----------------------------
# 진행률 표시용 Hook
# -----------------------------
def progress_hook(d):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate')
        downloaded = d.get('downloaded_bytes', 0)
        if total:
            percent = downloaded / total * 100
            print(f"\r다운로드 중: {percent:.1f}% ", end="", flush=True)
    elif d['status'] == 'finished':
        print("\r다운로드 완료, 변환 대기...          ", flush=True)

# -----------------------------
# 자막 + 메타데이터 확인
# -----------------------------
def list_subtitles(url):
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    subtitles = info.get("subtitles", {})
    title = info.get("title")
    artist = info.get("channel") or info.get("uploader") or info.get("uploader_id") or ""
    year = ""
    upload_date = info.get("upload_date")
    if upload_date and len(upload_date) >= 4:
        year = upload_date[:4]
    return subtitles.keys(), title, artist, year

# -----------------------------
# 곡 제목에서 특정 이름 제거 + X 감지
# -----------------------------
def remove_names(title: str):
    x_detected = False
    a = not ("hebi" in title.lower())
    for name in REMOVE_NAMES:
        if a and name.lower() == " x " and re.search(re.escape(name), title, re.IGNORECASE):
            x_detected = True
        pattern = rf'[\(\[\{{（【]\s*{re.escape(name)}\s*[\)\]\}}）】]'
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        title = re.sub(re.escape(name), '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+', ' ', title).strip()
    return title, x_detected

def normalize_spaces(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

# -----------------------------
# 아티스트 → 앨범 정보 결정
# -----------------------------
def resolve_album_info(artist, x_detected=False):
    if x_detected:
        return X_DETECTED_ARTIST, DEFAULT_ALBUM, X_DETECTED_ARTIST, "covers/StelLive.png"
    artist_lower = artist.lower()
    for rule in ARTIST_RULES:
        for key in rule["keys"]:
            if key.lower() in artist_lower:
                return (
                    rule.get("artist", artist),
                    rule["album"],
                    rule.get("album_artist", artist),
                    rule.get("cover_image")
                )
    return artist, DEFAULT_ALBUM, artist, None

# -----------------------------
# 자막 다운로드
# -----------------------------
def download_subtitle(url, title, lang):
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "subtitleslangs": [lang],
        "subtitlesformat": "vtt",
        "outtmpl": f"{OUTPUT_FOLDER}/{title}.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": FFMPEG_PATH
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(OUTPUT_FOLDER, f"{title}.{lang}.vtt")

# -----------------------------
# MP3 다운로드
# -----------------------------
def download_audio(url, title):
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{OUTPUT_FOLDER}/{title}.%(ext)s",
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }
        ],
        "ffmpeg_location": FFMPEG_PATH
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# -----------------------------
# FFmpeg로 MP3에 커버 + 메타데이터 삽입
# -----------------------------
def embed_cover_ffmpeg(mp3_path, cover_image, title, artist, year, album, album_artist):
    if not cover_image or not os.path.exists(cover_image):
        return
    tmp_file = mp3_path[:-4] + "_tmp.mp3"
    cmd = [
        os.path.join(FFMPEG_PATH, "ffmpeg"),
        "-y",
        "-i", mp3_path,
        "-i", cover_image,
        "-map", "0:a",
        "-map", "1:v",
        "-c:a", "copy",
        "-id3v2_version", "3",
        "-metadata", f"title={title}",
        "-metadata", f"artist={artist}",
        "-metadata", f"album={album}",
        "-metadata", f"album_artist={album_artist}",
        "-metadata", f"date={year}",
        "-disposition:v", "attached_pic",
        tmp_file
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.replace(tmp_file, mp3_path)

# -----------------------------
# MP3 제목 수정
# -----------------------------
def fix_single_mp3_title(mp3_path, title):
    tmp_file = mp3_path[:-4] + "_title.mp3"
    cmd = [
        os.path.join(FFMPEG_PATH, "ffmpeg"),
        "-y",
        "-i", mp3_path,
        "-c", "copy",
        "-metadata", f"title={title}",
        tmp_file
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.replace(tmp_file, mp3_path)



def normalize_mp3_year(mp3_path: str):
    try:
        try:
            tags = ID3(mp3_path)
        except ID3NoHeaderError:
            return  # 태그 없으면 스킵

        year = None

        if "TDRC" in tags:
            year = str(tags["TDRC"])
        elif "TYER" in tags:
            year = str(tags["TYER"])

        if not year:
            return

        tags.add(TDRC(encoding=3, text=year))
        tags.add(TYER(encoding=3, text=year))
        tags.save(mp3_path, v2_version=4)

    except Exception:
        pass


# -----------------------------
# 프로그램 실행
# -----------------------------
def main():
    url = input("유튜브 링크 입력: ").strip()
    print("\n자막 언어 확인 중...", flush=True)
    langs, title, artist, year = list_subtitles(url)
    langs = [lang for lang in langs if lang != "live_chat"]

    title = sanitize_filename(title)
    title = normalize_title(title)
    title, x_detected = remove_names(title)

    if not langs:
        artist, album, album_artist, cover_image = resolve_album_info(artist, x_detected=x_detected)
        print(f"\n영상 제목: {title}")
        print(f"아티스트: {artist}")
        print(f"앨범: {album}")
        print(f"앨범 아티스트: {album_artist}")
        print(f"커버 이미지: {cover_image or '없음'}")
        print(f"연도: {year}\n")
        choice = input("업로드 자막이 없습니다. MP3만 다운로드할까요? (Y/N): ").strip().upper()
        if choice != "Y":
            print("종료합니다.")
            return
        print("\nMP3 다운로드 시작...")
        download_audio(url, title)
        mp3_path = os.path.join(OUTPUT_FOLDER, f"{title}.mp3")
        embed_cover_ffmpeg(mp3_path, cover_image, title, artist, year, album, album_artist)
        fix_single_mp3_title(mp3_path, title)
        normalize_mp3_year(mp3_path)
        print("\n[작업 완료]")
        print(f"MP3: {OUTPUT_FOLDER}/{title}.mp3")
        return

    artist, album, album_artist, cover_image = resolve_album_info(artist, x_detected=x_detected)
    print(f"\n영상 제목: {title}")
    print(f"아티스트: {artist}")
    print(f"앨범: {album}")
    print(f"앨범 아티스트: {album_artist}")
    print(f"커버 이미지: {cover_image or '없음'}")
    print(f"연도: {year}")

    print("\n사용 가능한 자막 목록:")
    for i, lang in enumerate(langs):
        print(f"{i+1}. {lang}")

    choice = int(input("\n사용할 자막 번호 선택(제목 변경 시 0 입력): "))
    if not choice:
        new_title = input("새 곡 제목 입력: ").strip()
        if new_title:
            title = sanitize_filename(new_title)
            title = normalize_spaces(title)
        print(f'새 제목: {title}')
        for i, lang in enumerate(langs):
            print(f"{i+1}. {lang}")
        choice = int(input("\n사용할 자막 번호 선택: "))

    selected_lang = langs[choice-1]
    print(f"\n선택한 언어 자막 다운로드: {selected_lang}")
    vtt_path = download_subtitle(url, title, selected_lang)

    print("\nMP3 다운로드 시작...")
    download_audio(url, title)
    mp3_path = os.path.join(OUTPUT_FOLDER, f"{title}.mp3")
    embed_cover_ffmpeg(mp3_path, cover_image, title, artist, year, album, album_artist)
    fix_single_mp3_title(mp3_path, title)
    normalize_mp3_year(mp3_path)

    lrc_path = os.path.join(OUTPUT_FOLDER, f"{title}.lrc")
    vtt_to_lrc(vtt_path, lrc_path)

    print("\n[작업 완료]")
    print(f"MP3: {OUTPUT_FOLDER}/{title}.mp3")
    print(f"LRC: {OUTPUT_FOLDER}/{title}.lrc")

if __name__ == "__main__":
    main()