import re

# LRC 파일 경로
input_file = "input.lrc"
output_file = "output.lrc"

# 1초를 빼기 위해 정의
shift = -1.0  # 1초 앞당기기

def shift_time(match):
    time_str = match.group(1)  # mm:ss.xxx
    mm, ss = time_str.split(":")
    ss, ms = ss.split(".")
    total_sec = int(mm)*60 + int(ss) + int(ms)/1000
    total_sec += shift
    if total_sec < 0:
        total_sec = 0
    mm_new = int(total_sec // 60)
    ss_new = int(total_sec % 60)
    ms_new = int((total_sec - int(total_sec)) * 1000)
    return f"[{mm_new:02d}:{ss_new:02d}.{ms_new:03d}]"

with open(input_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = [re.sub(r"\[(\d+:\d+\.\d+)\]", shift_time, line) for line in lines]

with open(output_file, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("LRC 타임라인이 1초 앞당겨진 파일이 저장됨:", output_file)