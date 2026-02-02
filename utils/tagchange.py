import os
import subprocess

# 여기 경로만 바꿔서 사용
folder_path = r".\output\001"

for filename in os.listdir(folder_path):
    if filename.lower().endswith(".mp3"):
        file_path = os.path.join(folder_path, filename)
        title = os.path.splitext(filename)[0]  # 확장자 제거한 파일명을 제목으로
        tmp_file = file_path + ".tmp.mp3"

        # ffmpeg 명령 실행 (오디오 재인코딩 없이 메타데이터만 변경)
        cmd = [
            "ffmpeg",
            "-i", file_path,
            "-metadata", f"title={title}",
            "-codec", "copy",
            tmp_file
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 원본 파일 덮어쓰기
        os.replace(tmp_file, file_path)
        print(f"{filename} 변경 완료")