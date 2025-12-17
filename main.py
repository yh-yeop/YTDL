import os
import re
from util import *
from yt_dlp import YoutubeDL

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

    artist = (
        info.get("channel")
        or info.get("uploader")
        or info.get("uploader_id")
        or ""
    )

    year = ""
    upload_date = info.get("upload_date")  # YYYYMMDD
    if upload_date and len(upload_date) >= 4:
        year = upload_date[:4]

    return subtitles.keys(), title, artist, year

# -----------------------------
# 아티스트 → 앨범 정보 결정
# -----------------------------
def resolve_album_info(artist):
    artist_lower = artist.lower()

    for rule in ARTIST_RULES:
        for key in rule["keys"]:
            if key.lower() in artist_lower:
                new_artist = rule.get("artist", artist)
                return (
                    new_artist,
                    rule["album"],
                    rule["album_artist"]
                )

    return artist, DEFAULT_ALBUM, artist

def normalize_spaces(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def remove_names(title: str) -> str:
    x_detected = False

    for name in REMOVE_NAMES:
        # (), [], {} , 일본식 （）
        if name.lower() == " x " and re.search(re.escape(name), title, re.IGNORECASE):
            x_detected = True
        pattern = rf'[\(\[\{{（]\s*{re.escape(name)}\s*[\)\]\}}）]'
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        title = re.sub(re.escape(name), '', title, flags=re.IGNORECASE)

    title = normalize_spaces(title)
    
    return title, x_detected

# -----------------------------
# 선택한 언어의 자막 다운로드
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
# MP3 다운로드 + 메타데이터
# -----------------------------
def download_audio(url, title, artist, year, album, album_artist):
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    metadata_args = [
        "-metadata", f"artist={artist}",
        "-metadata", f"album={album}",
        "-metadata", f"album_artist={album_artist}",
    ]

    if year:
        metadata_args += ["-metadata", f"date={year}"]
    
    # ID3v2.3 강제
    metadata_args += ["-id3v2_version", "3"]

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
            },
            {
                "key": "FFmpegMetadata",
                "add_metadata": True,
            }
        ],
        "postprocessor_args": metadata_args,
        "ffmpeg_location": FFMPEG_PATH
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# -----------------------------
# 프로그램 실행
# -----------------------------
def main():
    url = input("유튜브 링크 입력: ").strip()
    print("\n자막 언어 확인 중...", flush=True)

    langs, title, artist, year = list_subtitles(url)
    if not langs:
        print("❌ 업로드 자막이 없습니다.")
        return

    title = sanitize_filename(title)
    title = normalize_title(title)
    title, x_detected = remove_names(title)
    artist, album, album_artist = resolve_album_info(artist)
    if x_detected: artist = X_DETECTED_ARTIST

    print(f"\n영상 제목: {title}")
    print(f"아티스트: {artist}")
    print(f"앨범: {album}")
    print(f"앨범 아티스트: {album_artist}")
    print(f"연도: {year}")

    print("\n사용 가능한 자막 목록:")
    langs = list(langs)
    for i, lang in enumerate(langs):
        print(f"{i+1}. {lang}")

    choice = int(input("\n사용할 자막 번호 선택: ")) - 1
    selected_lang = langs[choice]

    print(f"\n선택한 언어 자막 다운로드: {selected_lang}")
    vtt_path = download_subtitle(url, title, selected_lang)

    print("\nMP3 다운로드 시작...")
    download_audio(url, title, artist, year, album, album_artist)

    lrc_path = os.path.join(OUTPUT_FOLDER, f"{title}.lrc")
    vtt_to_lrc(vtt_path, lrc_path)

    print("\n🎉 작업 완료!")
    print(f"MP3: {OUTPUT_FOLDER}/{title}.mp3")
    print(f"LRC: {OUTPUT_FOLDER}/{title}.lrc")

if __name__ == "__main__":
    main()