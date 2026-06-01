# AI Vision Hand-Tracking Mouse Controller 공동 개발 및 인수인계 가이드
> 이 가이드는 Mac용 데모 버전을 바탕으로 **Windows용 상용급 제품**을 빌드할 프론트엔드 및 백엔드 팀원들을 위한 기술 인수인계서입니다.

---

## 1. 프로젝트 아키텍처 개요 (Dual-Track)

본 프로젝트는 알고리즘 검증 및 고성능 연산을 담당하는 **Python Modular Core (AI Engine)**와 웹/데스크톱 크로스 플랫폼 패키징을 위한 **Tauri GUI Desktop App**의 이원화 구조로 설계되어 있습니다.

```
+-------------------------------------------------+
|               Frontend (React/TS)               |
|  - Webcam Frame Capture                         |
|  - MediaPipe WASM Landmark Detection            |
|  - Canvas HUD Visualizer & MouseEngine v3.0     |
+------------------------+------------------------+
                         |
                Tauri IPC (Invoke)
                         |
                         v
+-------------------------------------------------+
|               Backend (Tauri/Rust)              |
|  - Tauri Commands Listener                      |
|  - Enigo Driver (move_mouse, click, drag)       |
|  - OS-Level Event Emulation                     |
+-------------------------------------------------+

+-------------------------------------------------+
|      Python AI Acceleration Engine (v7.0)       |
|  - camera.py: CLAHE Contrast Adjustment         |
|  - tracker.py: MediaPipe Hands Complexity=1     |
|  - controller.py: Hysteresis, Intent Gate, etc. |
|  - calibration.py: IQR Outlier & Neural Drift   |
+-------------------------------------------------+
```

### 핵심 협업 모델
1. **Mac용 데스크톱 앱 (본인 담당)**: Tauri 플랫폼을 바탕으로 React 프론트엔드와 Rust OS 레이어를 연동하여 빌드합니다.
2. **Windows용 데스크톱 앱 (팀원 담당)**: 
   * **프론트엔드**: React + TypeScript + MediaPipe WASM을 사용하여 웹캠 프레임 캡처 및 AI 핸드 랜드마크 추출을 전담합니다.
   * **백엔드**: 추출된 랜드마크 데이터를 기반으로 마우스 가속, 예측 필터, 캘리브레이션을 처리하고 Windows API를 통해 OS 레벨의 부드러운 마우스 이벤트를 에뮬레이션합니다.

---

## 2. 프로젝트 폴더 구조 및 파일 역할

```
hand_tracking_mouse/
├── HANDOVER_GUIDE.md          # 📄 [본 문서] 팀 협업 및 기술 가이드라인
├── previous_chat.md           # 📄 이전 버전 엔진 개발 및 알고리즘 튜닝 이력
├── config.json                # ⚙️ Gaussian 캘리브레이션 임계값 자동 영속성 파일 (Git 제외)
├── main.py                    # 🐍 Python 네이티브 7.0 버전 메인 실행 파일 (레퍼런스)
├── core/                      # 🐍 Python Core 수학 알고리즘 디렉터리
│   ├── calibration.py         # Outlier(IQR) 제거 및 실시간 Neural Drift 군집 관리자
│   └── filter.py              # 속도 감응형 OneEuroFilter 필터
├── backend/                   # 🐍 Python 마우스 제어 & 카메라 제어 로직
│   ├── camera.py              # CLAHE 조도 보정 및 멀티프로세싱 카메라 버퍼 큐
│   ├── tracker.py             # MediaPipe Python Wrapper (Complexity=1)
│   └── controller.py          # 지능형 감도 제어, 예측 제어, 상태 머신
├── ai_mouse_tauri/            # 📦 Tauri 기반 데스크톱 애플리케이션 (Mac-Windows 공유 가능)
│   ├── package.json           # React & Vite & Tauri CLI 의존성 정의
│   ├── src/                   # 🌐 React 19 / TypeScript 프론트엔드 소스
│   │   ├── main.tsx           # 진입점 및 리액트 마운트
│   │   ├── App.tsx            # 웹캠 라이브 및 Canvas HUD 제어부
│   │   └── lib/               # ⚙️ TS 이식 버전 엔진 (calibration.ts, engine.ts, filter.ts)
│   └── src-tauri/             # 🦀 Rust 백엔드 소스 (마우스 드라이버)
│       ├── Cargo.toml         # Rust 의존성 (enigo, tauri)
│       └── src/main.rs        # Rust OS 제어 명령 구현 (move_mouse, click_mouse, set_drag)
└── test/                      # 🧪 안정화 검증용 구버전 테스트 코드
```

---

## 3. 프론트엔드 개발자 가이드 (React + MediaPipe WASM)

프론트엔드 팀원은 **웹캠으로부터 초고속(30fps 이상) 프레임을 수집하고, MediaPipe WASM 라이브러리를 통해 손동작 랜드마크를 추출하여 실시간 Canvas HUD를 드로잉하고 백엔드로 넘겨주는 역할**을 담당합니다.

### 🛠️ 추천 도구 및 기술 스택
* **Core**: React 19, TypeScript 5.x, Vite 7.x
* **AI Vision**: `@mediapipe/tasks-vision` (최신 WASM 파일셋 로컬 혹은 CDN 연동)
* **CSS / UI**: Vanilla CSS 기반의 유리모피즘(Glassmorphism) 및 애니메이션 적용. 

### 💡 핵심 구현 포인트
1. **WASM 로딩 비동기 최적화**: 
   * 앱 로딩 시 MediaPipe CDN 혹은 로컬 퍼블릭 경로에서 `hand_landmarker.task` 모델 및 WASM 런타임을 빠르게 적재하도록 로딩 상태창(HUD)을 세련되게 스타일링해야 합니다. (현재 `App.tsx`에 구현 완료)
2. **저지연(Low-latency) 웹캠 프레임 캡처**:
   * 웹 브라우저(`navigator.mediaDevices.getUserMedia`) 비디오 스트림 해상도는 연산 최소화를 위해 **1280x720 (720p)**을 추천합니다.
   * `requestAnimationFrame`을 사용하여 매 프레임마다 WASM 추론 엔진을 호출하고, 추론 결과를 Canvas 오버레이에 시각화해 줍니다.
3. **Tauri IPC를 통한 Rust 백엔드 연결**:
   * 매 프레임에서 손동작 랜드마크가 검출되면 프론트엔드의 `MouseEngine`(`engine.ts`)에 랜드마크 배열을 전달합니다.
   * 계산된 목표 좌표와 상태 변화를 Tauri의 `invoke("move_mouse", {x, y})` 등을 통해 Rust OS 단으로 빠르게 보냅니다.

---

## 4. 백엔드 개발자 가이드 (Windows Native / Rust OS Layer)

Windows 환경의 백엔드 개발자는 **Tauri 앱의 Rust 백엔드 연동 및 Windows 환경에 특화된 초저지연 마우스 에뮬레이션**을 개발합니다.

### 🛠️ 추천 도구 및 기술 스택
* **시스템 언어**: Rust (Tauri 프레임워크와 결합 시 최상) 또는 C# (Windows API 제어에 특화)
* **마우스 시뮬레이션 라이브러리**: Rust `enigo` 크레이트 또는 C# `Windows InputSimulator`
* **시스템 API**: Windows Native `SendInput` API (최고 속도 및 드라이버 필터 우회용)

### 💡 Windows 환경 특화 구현 가이드
1. **Windows 하드웨어 가속 및 고해상도 모니터 대응**:
   * Windows는 디스플레이 배율(DPI Scaling - e.g., 125%, 150%)이 다양하므로, 마우스 좌표 계산 시 물리 픽셀과 논리 픽셀 간 오차가 생깁니다.
   * Rust 백엔드 개발 시 Windows API(`GetSystemMetrics` 혹은 `GetDeviceCaps`)를 사용해 현재 활성화된 모니터의 해상도와 배율을 계산해 스케일링 오차를 해결해야 합니다.
2. **`SendInput` API 사용 권장**:
   * 단순히 커서 좌표만 대입하는 `SetCursorPos`는 OS의 메시지 큐를 타기 때문에 지연이 있거나 일부 게임/어플리케이션 내에서 마우스 반응이 무시됩니다.
   * Rust `enigo`를 사용하거나 Windows Native API인 `SendInput`을 직접 호출하여 저수준 하드웨어 인터럽트에 가깝게 마우스 이벤트를 주입해야 합니다.
3. **설정 영속화 (Config Persistence)**:
   * 캘리브레이션으로 저장된 사용자의 골든 경계값(`config.json`)을 윈도우 사용자 로컬 디렉터리(`%APPDATA%`)에 안전하게 기록하고 자동 보정 학습 버퍼를 읽고 쓰도록 구현해야 합니다.

---

## 5. [v7.0] 프리미엄 알고리즘 Windows 이식 명세서

Python 레퍼런스 코드(`backend/controller.py`, `core/calibration.py`)에 반영되어 있는 상용급 6대 지능형 알고리즘을 이식할 수 있도록 원리와 구현 로직을 제공합니다.

### ① Intention Gate (조작 의도 필터)
*   **목적**: 사용자가 턱을 괴고 있거나 화면을 단순히 가리킬 때 커서가 멋대로 움직이거나 오작동하는 상황을 원천 방지합니다.
*   **원리**: 손목 랜드마크(0)와 중지 시작 마디(9)의 3D 벡터를 계산하여 기울기를 측정합니다.
*   **구현식 (TS)**:
    ```typescript
    const handDirX = lm[9].x - lm[0].x;
    const handDirY = lm[9].y - lm[0].y;
    // 손이 심하게 눕거나(가로 1.5배 이상), 손목보다 아래에 있으면 조작 의사 없음
    const isResting = (Math.abs(handDirX) > Math.abs(handDirY) * 1.5) || (handDirY > 0);
    ```

### ② Predictive Kinematics (지연 보정 예측기)
*   **목적**: OneEuroFilter 및 WASM 연산으로 인해 발생하는 물리적인 프레임 딜레이(약 30~50ms)를 극복하여 실시간 동기화를 맞춥니다.
*   **원리**: 등가속도 물리 법칙을 단순화하여 45ms 앞선 커서 좌표를 추정합니다.
*   **구현식 (TS)**:
    ```typescript
    const lookAhead = 0.045; // 45ms 미래 예측
    const instVelX = (rawScreenX - prevRawX) / dt;
    const instVelY = (rawScreenY - prevRawY) / dt;
    
    const predX = rawScreenX + instVelX * lookAhead;
    const predY = rawScreenY + instVelY * lookAhead;
    ```

### ③ Sticky Targeting (자석 조준 보조)
*   **목적**: 세밀한 버튼 클릭 시 손떨림으로 마우스가 빗나가는 현상을 억제합니다.
*   **원리**: 마우스 조작 속도가 초당 150픽셀 미만으로 느려지면 의도적으로 조작 감도를 30% 수준으로 억제(Viscosity=0.3)하여 표적에 끈적하게 달라붙게 만듭니다.
*   **구현식 (TS)**:
    ```typescript
    const speed = Math.hypot(instVelX, instVelY);
    let viscosity = 1.0;
    if (speed < 150 && !dragMode) {
        viscosity = 0.3; // 70% 물리 저항 추가로 정조준 유도
    }
    const diffX = (predX - prevX) * currentSensitivity * viscosity;
    ```

### ④ Neural Drift Update (자동 보정 학습기)
*   **목적**: 사용 시간 경과에 따른 손의 피로도나 웹캠 거리 변화로 손의 보정치가 달라지는 현상을 실시간 자동 학습합니다.
*   **원리**: 매끄러운 갱신을 위해 학습률(Learning Rate = 0.0005)을 적용해 실시간 가우시안 갱신 및 임계 경계를 가변 조정합니다.
*   **구현식 (TS)**:
    ```typescript
    const learningRate = 0.0005;
    if (isPinched) {
        if (ratio < pinchStats.mean) {
            pinchStats.mean = (pinchStats.mean * (1 - learningRate)) + (ratio * learningRate);
        }
    } else {
        if (ratio > openStats.mean) {
            openStats.mean = (openStats.mean * (1 - learningRate)) + (ratio * learningRate);
        }
    }
    ```

### ⑤ Dynamic Deadzone (동적 데드존)
*   **목적**: 사용자가 클릭을 발동할 때 손끝이 모이면서 커서가 미세하게 튀거나 흔들려 빗나가는 현상을 무력화시킵니다.
*   **원리**: 손을 강하게 쥘수록 마우스 이동 락 강도(Deadzone)의 반경을 최대 9px까지 확대하여 미동하지 않도록 락을 쏩니다.
*   **구현식 (TS)**:
    ```typescript
    const distMoved = Math.hypot(txFiltered - prevX, tyFiltered - prevY);
    const dynamicLimit = 1.5 + brakeFactor * 8.0; // 강하게 쥘수록 데드존 확장
    if (distMoved < dynamicLimit) {
        txFiltered = prevX;
        tyFiltered = prevY;
    }
    ```

### ⑥ Adaptive Hysteresis Expansion (드래그 탈출 잠금)
*   **목적**: 폴더/아이콘을 드래그하여 이동할 때, 실수로 엄지와 검지 간격이 약간 벌어져 발생하는 원치 않는 파일 낙하를 방지합니다.
*   **원리**: 클릭 중일 때는 해제 기준선(`off_threshold`) 영역을 자동 보정을 통해 30% 넓혀주어 손을 완전히 펴기 전까지는 드래그가 끊기지 않도록 가두어 둡니다.

---

## 6. 팀 협업 및 검증 프로토콜

제품의 퀄리티 유지를 위해 아래의 절차를 통해 단계적으로 완성해 나갑니다.

1. **Python Native 엔진 검증 (`main.py`)**:
   * 먼저 모든 개발자가 본인의 PC에서 `python main.py`를 실행하여 v7.0 최신 알고리즘의 동작 느낌과 마찰력, 자석 조준의 완성도를 직접 체험합니다.
2. **React WASM 이식 및 렌더러 구현 (`App.tsx`)**:
   * 웹캠 프레임 캡처 후 MediaPipe WASM의 구동 연산 저하(Jerkiness)가 없는지 먼저 브라우저 상에서 HUD 그래프를 띄워 점검합니다.
3. **Tauri Rust 드라이버 빌드 및 배포 테스트**:
   * Rust 백엔드 개발자는 Windows 머신에서 Node 및 Rust 환경을 구성하고 다음 명령을 통해 릴리즈 빌드를 추출합니다.
   ```bash
   cd ai_mouse_tauri
   npm install
   npm run tauri build
   ```
   * 생성된 `msi` 또는 `exe` 설치 프로그램 패키지를 통해 마우스 좌표 이동에 DPI 누락 오류가 발생하지 않는지 검증합니다.

---

> 💡 **문의 및 피드백**: 추가적인 세부 수학식 보정이나 알고리즘 이식 과정에서 궁금한 점이 생기면 언제든 세부 모듈의 상세 리포트를 생성해 상호 교차 검증을 진행해 주시기 바랍니다.
