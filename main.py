import os
import re
import subprocess
import json
import requests
import time
from http.cookiejar import MozillaCookieJar
from urllib.parse import urlparse, parse_qs
from util import *
from yt_dlp import YoutubeDL
from mutagen.id3 import ID3, ID3NoHeaderError, TDRC, TYER

FFMPEG_PATH = r"C:\ProgramData\chocolatey\bin"
OUTPUT_FOLDER = "output" if os.getcwd() != 'C:\App' else "YTDL\\output"
INCLUDE_AUTO_SUBS = False
BROWSER_COOKIES = None
COOKIE_FILE = r"C:\App\YTDL\cookie\cookies.txt"


def sanitize_filename(filename: str) -> str:
    return re.sub(r'[\\/:*?"<>|ㅣ]', '', filename)


def progress_hook(d):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate')
        downloaded = d.get('downloaded_bytes', 0)
        if total:
            percent = downloaded / total * 100
            print(f"\r다운로드 중: {percent:.1f}% ", end="", flush=True)
    elif d['status'] == 'finished':
        print("\r다운로드 완료, 변환 대기...          ", flush=True)


# 🔥 -------- YouTube 자막 추출 --------

def extract_video_id(url):
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        hostname = hostname.lower().replace("www.", "")

        if hostname in ("youtube.com", "m.youtube.com"):
            query = parse_qs(parsed.query)
            if "v" in query:
                return query["v"][0]
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 2 and parts[0] in ("shorts", "embed"):
                return parts[1]

        if hostname == "youtu.be":
            return parsed.path.lstrip("/")
    except:
        pass
    return None


DEFAULT_YT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Referer": "https://www.youtube.com/",
}


def fetch_caption_tracks(video_id):
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    cookie_jar = load_cookiejar(COOKIE_FILE)
    try:
        with requests.Session() as session:
            if cookie_jar:
                for cookie in cookie_jar:
                    session.cookies.set_cookie(cookie)
            r = session.get(watch_url, headers=DEFAULT_YT_HEADERS, timeout=10)
            if r.status_code != 200:
                return []
            match = re.search(r'captionTracks":(\[.*?\])', r.text, re.DOTALL)
            if not match:
                return []
            tracks = json.loads(match.group(1))
            result = []
            for track in tracks:
                lang = track.get("languageCode")
                base_url = track.get("baseUrl")
                if not lang or not base_url:
                    continue
                result.append({
                    "lang": lang,
                    "url": base_url,
                    "kind": track.get("kind"),
                    "name": track.get("name", {}).get("simpleText") if isinstance(track.get("name"), dict) else track.get("name")
                })
            return result
    except:
        return []


def fetch_timedtext_langs(video_id):
    tracks = fetch_caption_tracks(video_id)
    if tracks:
        langs = []
        for track in tracks:
            if track.get("kind") == "asr":
                continue
            if track["lang"] not in langs:
                langs.append(track["lang"])
        if langs:
            return langs

    url = f"https://www.youtube.com/api/timedtext?v={video_id}&type=list"
    try:
        r = requests.get(url, headers=DEFAULT_YT_HEADERS, timeout=5)
        if r.status_code != 200:
            return []
        langs = re.findall(r'lang_code="([^"]+)"', r.text)
        return list(dict.fromkeys(langs))
    except:
        return []


def load_cookiejar(cookiefile):
    if not cookiefile or not os.path.exists(cookiefile):
        return None
    try:
        jar = MozillaCookieJar(cookiefile)
        jar.load(ignore_discard=True, ignore_expires=True)
        return jar
    except Exception as e:
        print(f"⚠️ 쿠키 파일 로드 실패: {cookiefile}")
        print(f"   오류: {e}")
        return None


def find_caption_track_url(video_id, lang):
    tracks = fetch_caption_tracks(video_id)
    preferred = None
    for track in tracks:
        if track["lang"] == lang and track.get("kind") != "asr":
            return track["url"]
        if track["lang"] == lang and preferred is None:
            preferred = track["url"]
    return preferred


def ensure_vtt_url(url):
    if "fmt=" in url:
        return url
    separator = "&" if "?" in url else "?"
    return url + separator + "fmt=vtt"


def download_timedtext(video_id, lang, title, max_retries=3):
    path = os.path.join(OUTPUT_FOLDER, f"{title}.{lang}.vtt")
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    cookie_jar = load_cookiejar(COOKIE_FILE)
    ua_variants = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    ]

    for attempt in range(max_retries):
        print(f"[자막] timedtext 직접 다운로드 시도 {attempt + 1}/{max_retries} (UA={ua_variants[attempt % len(ua_variants)]})")
        try:
            with requests.Session() as session:
                if cookie_jar:
                    session.cookies = cookie_jar
                headers = DEFAULT_YT_HEADERS.copy()
                headers["User-Agent"] = ua_variants[attempt % len(ua_variants)]
                session.headers.update(headers)
                session.get(watch_url, timeout=10)

                fallback_url = find_caption_track_url(video_id, lang)
                if not fallback_url:
                    print("[자막] captionTracks URL을 찾을 수 없음")
                    return None
                fallback_url = ensure_vtt_url(fallback_url)

                r = session.get(
                    fallback_url,
                    headers={
                        "Referer": watch_url,
                        "Accept": "text/vtt,*/*;q=0.8",
                        "Origin": "https://www.youtube.com",
                    },
                    timeout=15,
                )
                content_type = r.headers.get("Content-Type", "")
                content_length = len(r.content or b"")
                print(f"[자막] timedtext 응답 상태: {r.status_code}, Content-Type={content_type}, 길이={content_length}")
                if r.status_code == 200 and r.content and content_length > 0:
                    body = r.content.decode("utf-8", errors="replace")
                    if body.strip() and not body.lstrip().startswith("<"):
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(body)
                        print(f"[자막] timedtext 다운로드 성공: {path}")
                        return path
                    print(f"[자막] timedtext 본문이 VTT가 아닙니다: {body[:120]!r}")
                if r.status_code == 429:
                    raise Exception("429 Too Many Requests")
        except Exception as e:
            print(f"[자막] timedtext 시도 실패: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 + attempt * 2)
    return None


# 🔥 -------- 자막 목록 --------

def list_subtitles(url):
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    raw_subs = info.get("subtitles") or {}
    auto_subs = info.get("automatic_captions") or {}

    valid_subs = {}

    for lang, tracks in raw_subs.items():
        if tracks:
            valid_subs[lang] = tracks

    if INCLUDE_AUTO_SUBS:
        for lang, tracks in auto_subs.items():
            if tracks:
                valid_subs[lang] = tracks

    # fallback 언어 보강
    video_id = extract_video_id(url)
    if video_id:
        timed_langs = fetch_timedtext_langs(video_id)
        for lang in timed_langs:
            if lang not in valid_subs:
                valid_subs[lang] = [{"ext": "vtt"}]

    title = info.get("title")
    artist = info.get("channel") or info.get("uploader") or info.get("uploader_id") or ""

    year = ""
    upload_date = info.get("upload_date")
    if upload_date and len(upload_date) >= 4:
        year = upload_date[:4]

    return list(valid_subs.keys()), title, artist, year


def remove_names(title: str):
    x_detected = False
    a = not ("hebi" in title.lower())
    for name in REMOVE_NAMES:
        if a and name.lower() == " x " and re.search(re.escape(name), title, re.IGNORECASE):
            x_detected = True
        pattern = rf'[\(\[\{{（【「]\s*{re.escape(name)}\s*[\)\]\}}）】」]'
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        title = re.sub(re.escape(name), '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+', ' ', title).strip()
    return title, x_detected


def normalize_spaces(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


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


def choose_audio_format(url):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception:
        return "bestaudio/best"

    formats = info.get("formats") or []
    audio_formats = [f for f in formats if f.get("vcodec") == "none" and f.get("acodec") != "none"]
    if not audio_formats:
        return "bestaudio/best"

    audio_formats.sort(key=lambda f: (
        -(f.get("abr") or 0),
        -(f.get("tbr") or 0),
        f.get("fps") or 0,
        f.get("filesize") or 0,
        f.get("ext") == "mp3",
        f.get("ext") == "aac",
        f.get("ext") == "opus",
        f.get("ext") == "webm",
    ))
    best = audio_formats[0]
    return best.get("format_id") or "bestaudio/best"


def download_subtitle(url, title, lang):
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    lang_candidates = [lang]
    if "-" in lang:
        lang_candidates.append(lang.split("-")[0])

    video_id = extract_video_id(url)
    if video_id:
        fallback = download_timedtext(video_id, lang, title, max_retries=3)
        if fallback:
            return fallback

    ydl_opts = {
        "skip_download": True,
        "subtitleslangs": lang_candidates,
        "subtitlesformat": "vtt",
        "outtmpl": f"{OUTPUT_FOLDER}/{title}.%(ext)s",
        "quiet": False,
        "no_warnings": False,
        "ffmpeg_location": FFMPEG_PATH,
        "writesubtitles": True,
        "writeautomaticsub": False,
    }

    print(f"\n[자막] yt-dlp 시도: {lang}")
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"[자막] 기본 yt-dlp 시도 실패: {e}")

    for ext in ["vtt", "srt", "ass", "ttml", "srv3"]:
        path = os.path.join(OUTPUT_FOLDER, f"{title}.{lang}.{ext}")
        if os.path.exists(path):
            return path

    for file in os.listdir(OUTPUT_FOLDER):
        if file.startswith(title) and lang in file:
            return os.path.join(OUTPUT_FOLDER, file)

    if BROWSER_COOKIES or COOKIE_FILE:
        ydl_opts_browser = {
            "skip_download": True,
            "subtitleslangs": lang_candidates,
            "subtitlesformat": "vtt",
            "outtmpl": f"{OUTPUT_FOLDER}/{title}.%(ext)s",
            "quiet": False,
            "no_warnings": False,
            "ffmpeg_location": FFMPEG_PATH,
            "writesubtitles": True,
            "writeautomaticsub": False,
        }
        if BROWSER_COOKIES:
            ydl_opts_browser["cookiesfrombrowser"] = BROWSER_COOKIES
        if COOKIE_FILE:
            ydl_opts_browser["cookiefile"] = COOKIE_FILE
        print(f"[자막] 쿠키 기반 yt-dlp 재시도: {lang}")
        try:
            with YoutubeDL(ydl_opts_browser) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"[자막] 쿠키 기반 yt-dlp 시도 실패: {e}")

        for ext in ["vtt", "srt", "ass", "ttml", "srv3"]:
            path = os.path.join(OUTPUT_FOLDER, f"{title}.{lang}.{ext}")
            if os.path.exists(path):
                return path

        for file in os.listdir(OUTPUT_FOLDER):
            if file.startswith(title) and lang in file:
                return os.path.join(OUTPUT_FOLDER, file)

    if video_id:
        print(f"[자막] 직접 timedtext 재시도: {lang}")
        time.sleep(3)
        fallback = download_timedtext(video_id, lang, title, max_retries=5)
        if fallback:
            print(f"[자막] timedtext 재시도 성공: {fallback}")
            return fallback

    return None


def download_audio(url, title):
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    selected_format = choose_audio_format(url)
    initial_opts = {
        "format": selected_format,
        "outtmpl": f"{OUTPUT_FOLDER}/{title}.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "ffmpeg_location": FFMPEG_PATH,
        "socket_timeout": 30,
    }

    try:
        with YoutubeDL(initial_opts) as ydl:
            ydl.download([url])
        return
    except Exception:
        pass

    fallback_opts = initial_opts.copy()
    fallback_opts["format"] = "bestaudio/best"
    fallback_opts["quiet"] = True
    fallback_opts["no_warnings"] = True

    try:
        with YoutubeDL(fallback_opts) as ydl:
            ydl.download([url])
    except Exception:
        pass


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
            return

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


def main():
    url = input("유튜브 링크 입력: ").strip()
    print("\n자막 언어 확인 중...", flush=True)

    langs, title, artist, year = list_subtitles(url)
    langs = [lang for lang in langs if lang != "live_chat"]

    title = sanitize_filename(title)
    title = normalize_title(title)
    title, x_detected = remove_names(title)

    artist, album, album_artist, cover_image = resolve_album_info(artist, x_detected=x_detected)

    print(f"\n영상 제목: {title}")
    print(f"아티스트: {artist}")
    print(f"앨범: {album}")
    print(f"앨범 아티스트: {album_artist}")
    print(f"커버 이미지: {cover_image or '없음'}")
    print(f"연도: {year}")

    if not langs:
        choice = input("\nMP3만 다운로드하시겠습니까? (Y/N, 제목 변경은 0): ").strip().upper()

        if choice == "0":
            new_title = input("새 곡 제목 입력: ").strip()
            if new_title:
                title = sanitize_filename(new_title)
                title = normalize_spaces(title)
            print(f"새 제목: {title}")

        elif choice != "Y":
            print("종료")
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

    print("\n사용 가능한 자막 목록:")
    for i, lang in enumerate(langs):
        print(f"{i+1}. {lang}")

    choice = int(input("\n사용할 자막 번호 선택(제목 변경 시 0 입력): "))

    if choice == 0:
        new_title = input("새 곡 제목 입력: ").strip()
        if new_title:
            title = sanitize_filename(new_title)
            title = normalize_spaces(title)
        print(f"새 제목: {title}")

        for i, lang in enumerate(langs):
            print(f"{i+1}. {lang}")

        choice = int(input("\n사용할 자막 번호 선택: "))

    selected_lang = langs[choice-1]

    print(f"\n선택한 자막 다운로드: {selected_lang}")
    vtt_path = download_subtitle(url, title, selected_lang)
    if vtt_path:
        print(f"다운로드된 자막 파일: {vtt_path}")
    else:
        print("경고: 자막 다운로드에 실패하여 LRC 파일을 생성하지 않습니다.")

    print("\nMP3 다운로드 시작...")
    download_audio(url, title)

    mp3_path = os.path.join(OUTPUT_FOLDER, f"{title}.mp3")
    embed_cover_ffmpeg(mp3_path, cover_image, title, artist, year, album, album_artist)
    fix_single_mp3_title(mp3_path, title)
    normalize_mp3_year(mp3_path)

    if vtt_path:
        lrc_path = os.path.join(OUTPUT_FOLDER, f"{title}.lrc")
        vtt_to_lrc(vtt_path, lrc_path)

    print("\n[작업 완료]")
    print(f"MP3: {OUTPUT_FOLDER}/{title}.mp3")
    if vtt_path:
        print(f"LRC: {OUTPUT_FOLDER}/{title}.lrc")


if __name__ == "__main__":
    main()