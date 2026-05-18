import sys
import platform
import mediapipe as mp

def run_diagnostics():
    print("=" * 40)
    print("[시스템 및 아키텍처 진단]")
    print(f"Python Version : {sys.version.split()[0]}")
    print(f"Machine Arch : {platform.machine()}")
    print(f"Platform : {platform.platform()}")
    print("-" * 40)

    print("[MediaPipe 패키지 진단]")
    try:
        print(f"Location : {mp.__file__}")
        print(f"Loaded Modules : {dir(mp)}")

        if 'solutions' in dir(mp):
            print("Status       : 'solutions' 모듈 적재 완료")
        else:
            print("Status       : 'solutions' 모듈 적재 적재 (C++ 바이너리 로드 에러 의심)")
    except Exception as e:
        print(f"Error during inspection: {e}")
    print("=" * 40)

if __name__ == "__main__":
    run_diagnostics()