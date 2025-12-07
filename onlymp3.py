import os
import re
from util import *
from yt_dlp import YoutubeDL

FFMPEG_PATH = r"C:\ProgramData\chocolatey\bin"  # ffmpeg.exe와 ffprobe.exe 경로
OUTPUT_FOLDER = "output"

# -----------------------------
# 파일명 안전화
# -----------------------------
def sanitize_filename(filename: str) -> str:
    # Windows에서 허용되지 않는 문자: \ / : * ? " < > |
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

def get_title(url):
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info.get("title")

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
        "outtmpl": f"{OUTPUT_FOLDER}/%(title)s.%(ext)s",
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
def download_audio(url,title):
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{OUTPUT_FOLDER}/%(title)s.%(ext)s",
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

    print("\n영상 정보 확인 중...", flush=True)
    title = get_title(url)

    # 안전한 파일명으로 변환
    title = sanitize_filename(title)

    print(f"\n영상 제목: {title}")

    print("\nMP3 다운로드 시작...", flush=True)
    download_audio(url, title)

    print("\n🎉 작업 완료!")
    print(f"MP3: {OUTPUT_FOLDER}/{title}.mp3")

if __name__ == "__main__":
    main()