# 📝 AI Vision Hand-Tracking Mouse 프로젝트 요약서 (SUMMARY)

본 문서는 프로젝트의 핵심 아키텍처, 기능 및 구동 방식을 1페이지 분량으로 핵심만 요약 정리한 요약서입니다. 상세한 전체 가이드는 [README.md](file:///Users/injinsung/hand_tracking_mouse/README.md) 또는 [HANDOVER_GUIDE.md](file:///Users/injinsung/hand_tracking_mouse/HANDOVER_GUIDE.md)를 참고하시기 바랍니다.

---

## 1. 프로젝트 개요 (Overview)
* **목표**: 일반 웹캠 비디오 입력에서 사용자 손동작(랜드마크)을 추적해 화면 마우스 커서 이동 및 좌/우클릭, 드래그, 스크롤, 단축키 동작을 정밀 시뮬레이션합니다.
* **특징**: 웹캠의 저가역 노이즈, 클릭 발동 시의 미세 떨림, 원거리 혼선 등을 극복하기 위한 수학적 예측 및 필터링 제어 알고리즘이 내장된 상용급 솔루션입니다.

---

## 2. 하이브리드 이원화 아키텍처 (Dual-Track)
* **Python Modular Core (AI Engine v7.0)**: OpenCV 기반 영상 전처리(CLAHE 보정) 및 MediaPipe Python 추론, OneEuroFilter 제어가 구현된 수학적 레퍼런스 모듈입니다.
* **Tauri Desktop App (React + TS + Rust)**: React 19 UI 대시보드를 통해 상태를 실시간 모니터링하며, 브라우저 스레드(WASM)에서 추출한 좌표 데이터를 Tauri IPC를 거쳐 시스템 백엔드(Rust)의 Enigo 드라이버에 넘겨 마우스를 제어하는 데스크톱 전용 앱입니다.

---

## 3. 핵심 6대 알고리즘 및 편의 기능
1. **Intention Gate (조작 의도 판별)**: 손목-손가락 벡터 방향을 분석하여 턱을 괴는 등 조작 의도가 없는 편안한 휴식 상태에서는 마우스 제어를 자동으로 잠급니다.
2. **Predictive Kinematics (지연 보정 예측기)**: 속도와 가속도를 계산해 45ms 미래의 좌표로 커서를 이동시켜 화면 딜레이 체감을 상쇄합니다.
3. **Sticky Targeting & Sniper Mode**: 저속 조작 시 정조준을 보완하고, 클릭 직전 검지와 엄지가 모일 때 커서를 고정(Viscosity = 0.03)하여 빗나감을 완벽히 차단합니다.
4. **Neural Drift Update (실시간 보정 학습기)**: 사용 습관 및 피로도에 따라 달라지는 손가락 펴짐/꼬집음 임계값을 학습률 0.0005로 배경에서 실시간 보정합니다.
5. **Adaptive Hysteresis & Release Boost**: 드래그 잠금 시 해제 임계 범위를 30% 확장하여 안정성을 보장하고, 핑거 릴리즈 가속을 추적하여 빠른 뗌 동작을 감지합니다.
6. **기타 제스처**: 주먹 쥐기(Fist)를 통한 화면 스크롤 제어, 세 손가락 펼쳐 새끼 접기 제스처를 통한 macOS 미션 컨트롤 단축키 구동.

---

## 4. 퀵 실행 가이드 (Quick Start)

### ① Python Native Core 실행
```bash
pip install opencv-python mediapipe pynput pyautogui numpy
python main.py
# (디버그창 활성화 중 단축키) c: 캘리브레이션 시작 / w,s: ON임계값 증감 / e,d: OFF임계값 증감
```

### ② Tauri 데스크톱 앱 빌드 및 실행
```bash
cd ai_mouse_tauri
npm install
npm run tauri dev   # 개발 모드 기동 (Vite Dev Server + App Window)
```

---

## 5. 배포 및 다운로드 서비스 구성 방안
* **설치 프로그램 빌드**: `npm run tauri build`를 수행하여 macOS용 `.dmg` 및 Windows용 `.msi` (또는 `.exe`) 설치 프로그램 패키지를 빌드합니다.
* **다운로드 서버 아키텍처**:
  * **랜딩 페이지**: Vercel/Netlify 호스팅 정적 웹 페이지를 구성하여 접속자의 OS를 감지해 알맞은 다운로드 버튼을 띄웁니다.
  * **저장소**: 대용량 설치 파일은 GitHub Releases 또는 AWS S3 저장소에 업로드하여 다이렉트 다운로드 링크를 제공합니다.
  * **CI/CD 파이프라인**: `.github/workflows/release.yml`을 설정하여 깃허브 버젼 태그 푸시 시 자동으로 크로스 플랫폼 바이너리가 빌드 및 릴리즈되도록 자동화합니다.
