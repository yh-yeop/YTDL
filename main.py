import os
import re
from util import *
from yt_dlp import YoutubeDL

FFMPEG_PATH = r"C:\ProgramData\chocolatey\bin"
OUTPUT_FOLDER = "output"

# -----------------------------
# 파일명 안전화
# -----------------------------
def sanitize_filename(filename: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '_', filename)

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
# 자막 언어 리스트 확인
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
    return subtitles.keys(), info.get("title")

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
    vtt_path = os.path.join(OUTPUT_FOLDER, f"{title}.{lang}.vtt")
    return vtt_path

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
# 프로그램 실행
# -----------------------------
def main():
    url = input("유튜브 링크 입력: ").strip()
    print("\n자막 언어 확인 중...", flush=True)

    langs, title = list_subtitles(url)
    if not langs:
        print("❌ 업로드 자막이 없습니다.")
        return

    title = sanitize_filename(title)

    print(f"\n영상 제목: {title}")
    print("\n사용 가능한 자막 목록:")
    langs = list(langs)
    for i, lang in enumerate(langs):
        print(f"{i+1}. {lang}")

    choice = int(input("\n사용할 자막 번호 선택: ")) - 1
    selected_lang = langs[choice]

    print(f"\n선택한 언어 자막 다운로드: {selected_lang}")
    vtt_path = download_subtitle(url, title, selected_lang)

    print("\nMP3 다운로드 시작...")
    download_audio(url, title)

    lrc_path = os.path.join(OUTPUT_FOLDER, f"{title}.lrc")
    vtt_to_lrc(vtt_path, lrc_path)

    print("\n🎉 작업 완료!")
    print(f"MP3: {OUTPUT_FOLDER}/{title}.mp3")
    print(f"LRC: {OUTPUT_FOLDER}/{title}.lrc")

if __name__ == "__main__":
    main()