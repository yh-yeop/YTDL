import os
import re
from util import *
from yt_dlp import YoutubeDL


# -----------------------------
# 파일명 안전화
# -----------------------------
def sanitize_filename(filename: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '_', filename)

# -----------------------------
# 자막 목록 확인
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
# 선택된 자막 다운로드
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
        "no_warnings": True
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    vtt_path = os.path.join(OUTPUT_FOLDER, f"{title}.{lang}.vtt")
    return vtt_path

# -----------------------------
# 메인 실행
# -----------------------------
def main():
    url = input("유튜브 링크 입력: ").strip()
    print("\n자막 언어 확인 중...\n", flush=True)

    langs, title = list_subtitles(url)
    if not langs:
        print("❌ 업로드된 자막이 없음")
        return

    title = sanitize_filename(title)

    print(f"영상 제목: {title}\n")
    print("사용 가능한 자막 목록:")
    langs = list(langs)
    for i, lang in enumerate(langs):
        print(f"{i+1}. {lang}")

    choice = int(input("\n사용할 자막 번호 선택: ")) - 1
    selected_lang = langs[choice]

    print(f"\n선택한 언어 자막 다운로드 중: {selected_lang}")
    vtt_path = download_subtitle(url, title, selected_lang)

    lrc_path = os.path.join(OUTPUT_FOLDER, f"{title}.lrc")
    vtt_to_lrc(vtt_path, lrc_path)

    print("\n🎉 LRC 생성 완료!")
    print(f"LRC 파일: {OUTPUT_FOLDER}/{title}.lrc")

if __name__ == "__main__":
    main()