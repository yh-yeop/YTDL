import re

INPUT_FILE = r".\utils\srt_to_lrc\input.srt"
OUTPUT_FILE = r".\utils\srt_to_lrc\output.lrc"

def srt_to_lrc(srt_path, lrc_path):
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = re.split(r'\n\s*\n', content.strip())
    lrc_lines = []

    for block in blocks:
        lines = block.split('\n')

        if len(lines) < 2:
            continue

        # 시간 파싱
        time_line = lines[1]
        match = re.match(r'(\d+):(\d+):(\d+),(\d+)', time_line)

        if not match:
            continue

        h, m, s, ms = map(int, match.groups())

        # LRC는 mm:ss.xx (centisecond 단위)
        total_minutes = h * 60 + m
        cs = int(ms / 10)  # 밀리초 → 센티초(2자리)

        lrc_time = f"[{total_minutes:02d}:{s:02d}.{cs:02d}]"

        text = ' '.join(lines[2:]).strip()

        lrc_lines.append(f"{lrc_time}{text}")

    with open(lrc_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lrc_lines))


# 사용 예시
srt_to_lrc(INPUT_FILE, OUTPUT_FILE)