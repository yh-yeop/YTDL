import re
import webvtt
import os

def vtt_to_lrc(vtt_path, lrc_path):
    ZERO_WIDTH = r"[\u200B\u200C\u200D\uFEFF]"

    def timestamp_to_ms(ts):
        h, m, s = ts.split(":")
        s, ms = s.split(".")
        return (
            int(h) * 3600 * 1000 +
            int(m) * 60 * 1000 +
            int(s) * 1000 +
            int(ms)
        )

    def ms_to_lrc(ms):
        minutes = ms // 60000
        seconds = (ms % 60000) // 1000
        ms = ms % 1000
        return f"[{minutes:02}:{seconds:02}.{ms:03}]"

    entries = []

    # ------------------------------
    # 1. 정제
    # ------------------------------
    for c in webvtt.read(vtt_path):
        ms = timestamp_to_ms(c.start)

        text = c.text.replace("\n", " ")
        text = text.replace("&nbsp;", "")
        text = re.sub(ZERO_WIDTH, "", text)
        text = text.strip()

        entries.append((ms, text))

    # ------------------------------
    # 2. 노이즈 제거
    # ------------------------------
    def is_noise(text):
        return bool(re.fullmatch(r"[!¡.,…?]+", text))

    cleaned = [(ms, t) for ms, t in entries if t and not is_noise(t)]

    # ------------------------------
    # 3. 문장별 중복 제거 (개선된 방식)
    # ------------------------------
    TH = 800  # ms
    merged = []
    last_seen = {}  # text -> last timestamp

    for ms, t in cleaned:
        if t in last_seen and (ms - last_seen[t]) <= TH:
            # 중복 → 건너뛰기
            continue

        merged.append((ms, t))
        last_seen[t] = ms

    # ------------------------------
    # 4. LRC 저장
    # ------------------------------
    with open(lrc_path, "w", encoding="utf-8") as f:
        for ms, t in merged:
            f.write(f"{ms_to_lrc(ms)}{t}\n")

    try:
        os.remove(vtt_path)
    except:
        pass