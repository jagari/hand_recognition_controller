# 🌟 AI Vision Hand-Tracking Mouse Controller (God Hand Center)

> **카메라 화면을 통해 손의 움직임을 실시간으로 추적하고 정밀 제어하여 마우스 커서와 클릭/드래그 동작을 수행하는 데스크톱 제어 시스템입니다.**
> 본 프로젝트는 알고리즘 검증용 **Python Modular Core (AI Engine v7.0)**와 크로스 플랫폼 데스크톱 패키징 및 고성능 OS 이벤트 에뮬레이션을 위한 **Tauri GUI Desktop App (React + TS + Rust)**의 **Dual-Track 하이브리드 아키텍처**로 구현되어 있습니다.

---

## 📂 목차
1. [시스템 아키텍처 (Dual-Track)](#1-시스템-아키텍처-dual-track)
2. [핵심 지능형 알고리즘 분석 (12대 Premium Features)](#2-핵심-지능형-알고리즘-분석-12대-premium-features)
3. [프로젝트 디렉터리 구조 및 파일 역할](#3-프로젝트-디렉터리-구조-및-파일-역할)
4. [현재까지의 진행 상황 및 검증 상태](#4-현재까지의-진행-상황-및-검증-상태)
5. [로컬 빌드 및 실행 방법](#5-로컬-빌드-및-실행-방법)
6. [배포 및 서버 다운로드 서비스 구축 방안 (핵심 요구사항)](#6-배포-및-서버-다운로드-서비스-구축-방안-핵심-요구사항)

---

## 1. 시스템 아키텍처 (Dual-Track)

본 프로젝트는 고성능 이미지 프로세싱 및 AI 모델 추론은 웹 브라우저(WASM) 레이어에서 처리하고, 실제 마우스 입력 제어 및 OS 레벨 통합은 저지연 시스템 언어인 Rust 및 Python OS 레이어에서 전담하는 이원화 모델을 채택하였습니다.

```
┌───────────────────────────────────────────────────────────────────┐
│                       Frontend (React 19 / TS)                    │
│  - Web Video Stream Capture & CLAHE/Auto Contrast                 │
│  - MediaPipe WASM Landmark Detection (Complexity=1)               │
│  - Interactive Glassmorphism Dashboard UI & Real-time Telemetry  │
│  - Canvas HUD Overlay Drawing & MouseEngine v3.0 (TS Core)        │
└─────────────────────────────────┬─────────────────────────────────┘
                                  │
                          Tauri IPC (Invoke)
                                  │
                                  v
┌───────────────────────────────────────────────────────────────────┐
│                       Backend (Tauri / Rust)                      │
│  - Tauri Commands Listener (move_mouse, click_mouse, set_drag)     │
│  - Enigo Driver & OS-Level Event Emulation                        │
│  - macOS CoreGraphics Integration & Windows SendInput API         │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                Python AI Acceleration Engine (v7.0)               │
│  - camera.py: CLAHE Contrast Adjustment                           │
│  - tracker.py: MediaPipe Hands Complexity=1                       │
│  - controller.py: Hysteresis, Intent Gate, Neural Drift           │
│  - calibration.py: IQR Outlier & Neural Drift Cluster Manager     │
└───────────────────────────────────────────────────────────────────┘
```

---

## 2. 핵심 지능형 알고리즘 분석 (12대 Premium Features)

단순한 손가락 끝 좌표 매핑을 넘어, 실사용 환경에서 발생하는 노이즈와 신체적 특성에 대응하기 위해 12가지 프리미엄 알고리즘이 Python Engine 및 Tauri TypeScript Engine에 구현되어 있습니다.

### ① 3D Rotation-Invariant Ratio Extraction (회전 불변 비율 계산)
* **목적**: 손의 방향(회전, 기울임)에 무관하게 일정한 클릭 판단 기준을 확보합니다.
* **원리**: MediaPipe의 `World Landmarks`(물리적인 미터 단위 3D 좌표)를 기반으로, 손가락 끝과 손가락 마디의 비율을 연산합니다. 
* **구현식**:
  $$\text{d3\_base} = \text{dist3d}(\text{wlm}[5], \text{wlm}[0])$$
  $$\text{index\_ratio} = \frac{\text{dist3d}(\text{wlm}[8], \text{wlm}[4])}{\text{d3\_base}}$$

### ② Intention Gate (조작 의도 필터)
* **목적**: 턱을 괴거나 단순히 화면을 가리키는 손동작 등 마우스를 제어할 의도가 없는 상태에서의 오작동을 원천 봉재합니다.
* **원리**: 손목(0번)과 중지 시작 마디(9번)의 3D 벡터를 추적하여 손이 지나치게 수평으로 누워 있거나 손목보다 아래에 처진 경우 커서 이동을 차단합니다.
```typescript
const handDirX = wlm[9].x - wlm[0].x;
const handDirY = wlm[9].y - wlm[0].y;
this.isResting = (Math.abs(handDirX) > Math.abs(handDirY) * 1.5) || (handDirY > 0);
```

### ③ Predictive Kinematics (지연 보정 예측기)
* **목적**: 필터 연산 및 웹캠 프레임 딜레이(30~50ms)로 발생하는 물리적인 커서 밀림 현상을 극복하여 실시간 동기화를 구현합니다.
* **원리**: 등속도/등가속도 물리 법칙에 기반해 45ms 뒤의 미래 좌표를 연산하여 커서를 한발 앞서 이동시킵니다.
```typescript
const lookAhead = 0.045; // 45ms 미래 예측
const predX = rawScreenX + instVelX * lookAhead;
const predY = rawScreenY + instVelY * lookAhead;
```

### ④ Sticky Targeting (자석 조준 보조)
* **목적**: 미세한 크기의 버튼이나 입력창에 접근할 때 손떨림으로 마우스가 미끄러지는 현상을 방지합니다.
* **원리**: 커서의 속도가 초당 150픽셀 이하로 느려질 경우 마우스 감도에 70%의 의도적 저항(Viscosity = 0.3)을 부여하여 표적에 흡착되는 효과를 구현합니다.

### ⑤ Sniper Mode (초정밀 클릭 횡이동 튀기 차단)
* **목적**: 검지와 엄지를 모으는(Pinch) 순간 검지 끝의 궤적이 흔들려 클릭 타깃이 미세하게 옆으로 빗나가는 현상을 원천 방지합니다.
* **원리**: 클릭 임계값 직전 단계(예: 임계값의 1.4배 이내)에 돌입하면 마우스 이동 점착력(Viscosity)을 즉시 0.03으로 낮추어 커서를 화면에 거의 고정시킵니다.

### ⑥ Neural Drift Update (자동 보정 학습기)
* **목적**: 사용자의 자세 변화, 피로도 상승, 웹캠과의 거리 변화 등으로 인해 손을 펼쳤을 때와 오므렸을 때의 절대 임계값이 달라지는 문제를 실시간으로 적응합니다.
* **원리**: 매 프레임 입력 데이터를 받아 클릭 상태일 때는 최소 임계값을, 핀 상태일 때는 최대 임계값을 매우 미세한 학습률(Learning Rate = 0.0005)로 동적 갱신하여 클러스터 범위를 재조정합니다.

### ⑦ Dynamic Deadzone (동적 데드존)
* **목적**: 손가락을 쥐는 세기(압력)에 비례해 커서의 좌표 락(Lock) 범위를 동적으로 확장하여 원치 않는 커서 튐을 억제합니다.
* **원리**: 손을 강하게 오므려 클릭 상태에 진입할수록 락 한계 영역을 최소 1.5px에서 최대 9.5px까지 동적으로 넓혀 흔들림을 상쇄합니다.

### ⑧ Adaptive Hysteresis Expansion (드래그 탈출 잠금)
* **목적**: 파일이나 폴더를 잡고 드래그 앤 드롭하는 과정에서 손가락 간격이 미세하게 벌어져 원치 않는 위치에 파일이 드롭되는 오작동을 해결합니다.
* **원리**: 클릭이 활성화되어 드래그 상태(Drag Mode)로 전환되면 클릭 해제(OFF) 기준선의 범위를 30~40% 강제로 넓혀주어, 손을 완전히 펴기 전까지는 홀딩 상태를 안정적으로 유지합니다.

### ⑨ Release Boost (속도 기반 해제 가속)
* **목적**: 사용자가 클릭을 해제하고 손가락을 뗄 때, 마커의 인지 딜레이를 최소화하여 즉각적으로 마우스 버튼을 놓도록 가속합니다.
* **원리**: 손가락이 벌어지는 변화 속도(Velocity)를 분석하여 속도가 빠를수록 해제 임계값(offThreshold)을 임시로 낮추어 즉시 해제를 유도합니다.

### ⑩ Fist Scroll Mode (주먹 쥐기 스크롤)
* **목적**: 스크롤 조작의 편의성을 극대화합니다.
* **원리**: 손가락 중 3개 이상이 굽혀진 상태(Fist)가 감지되면 스크롤 모드를 발동하며, 이 상태에서 손목 전체를 위/아래로 움직여 자연스럽게 스크롤을 트리거합니다.

### ⑪ Web Worker 60fps 정밀 틱 타이머
* **목적**: 브라우저 탭 비활성화 또는 렌더링 락으로 인해 `requestAnimationFrame` 주기가 밀려 마우스 추적이 끊기는 현상을 방지합니다.
* **원리**: 별도의 독립 스레드인 **Web Worker** 내에 16ms 주기(60fps)의 인터벌 타이머를 가동하여 프론트엔드가 언제나 균일한 속도로 AI 랜드마크 분석 및 OS 통신 틱을 실행하도록 보장합니다.

### ⑫ App Nap 방지를 위한 Silent Audio Loop 기법
* **목적**: macOS 환경 등에서 창이 포커스를 잃거나 백그라운드로 전환될 때 OS가 브라우저 코어에 주는 자원 제약(App Nap / Energy Saver)으로 인해 마우스가 먹통이 되는 현상을 우려해 고안되었습니다.
* **원리**: 백그라운드에서 용량이 극소화된 무음 오디오 파일(base64)을 무한 루프로 재생하여 브라우저 엔진이 항상 액티브 미디어 세션 상태를 유지하도록 해 가동성을 확보합니다.

---

## 3. 프로젝트 디렉터리 구조 및 파일 역할

```
hand_tracking_mouse/
├── HANDOVER_GUIDE.md          # 📄 공동 개발 및 인수인계용 기술 백서
├── previous_chat.md           # 📄 v2.0 이전 버전의 알고리즘 튜닝 이력
├── config.json                # ⚙️ Python Core용 Gaussian 캘리브레이션 임계값 저장소 (Git 제외)
├── main.py                    # 🐍 Python 네이티브 7.0 버전 메인 실행부 (알고리즘 레퍼런스)
├── core/                      # 🐍 Python Core 수학/필터 알고리즘 디렉터리
│   ├── calibration.py         # Outlier(IQR) 제거 및 실시간 Neural Drift 군집 관리자
│   └── filter.py              # 속도 감응형 OneEuroFilter 필터
├── backend/                   # 🐍 Python 마우스 제어 & 카메라 제어 로직
│   ├── camera.py              # CLAHE 조도 보정 및 멀티프로세싱 카메라 버퍼 큐
│   ├── tracker.py             # MediaPipe Python Wrapper (Complexity=1)
│   └── controller.py          # 지능형 감도 제어, 예측 제어, 상태 머신
├── ai_mouse_tauri/            # 📦 Tauri 기반 크로스 플랫폼 데스크톱 애플리케이션 (핵심 실무용)
│   ├── package.json           # React & Vite & Tauri CLI 의존성 정의
│   ├── src/                   # 🌐 React 19 / TypeScript 프론트엔드 소스
│   │   ├── main.tsx           # 진입점 및 리액트 마운트
│   │   ├── App.tsx            # 웹캠 라이브 캡처 및 HUD 오버레이, 제어 센터 대시보드
│   │   ├── styles/            # 프리미엄 뷰를 위한 CSS 및 Glassmorphism 스타일시트
│   │   └── lib/               # ⚙️ TS 이식 버전 엔진 (calibration.ts, engine.ts, filter.ts)
│   └── src-tauri/             # 🦀 Rust 백엔드 소스 (마우스 드라이버)
│       ├── Cargo.toml         # Rust 의존성 (enigo, tauri)
│       └── src/main.rs        # Rust OS 제어 명령 구현 (move_mouse, click_mouse, set_drag, scroll_mouse)
└── test/                      # 🧪 안정화 검증용 구버전 테스트 코드
```

---

## 4. 현재까지의 진행 상황 및 검증 상태

### 1) Python Core v7.0 검증 완료
* `python main.py`를 실행하여 직접 카메라 화면과 마우스 제어 감도 체크 가능.
* 3D 월드 좌표계 기반 회전 불변 알고리즘 및 예측 제어, 자석 조준 동작 검증 완료.

### 2) Tauri 데스크톱 앱 마이그레이션 및 UI 구현 완료
* React 19 대시보드 구조에 맞춰 **유리모피즘(Glassmorphism) 기반의 제어 대시보드** 완성.
* 실시간 텔레메트리 게이지(Tracking Quality, AIM Vector, DPI Indicator 등) 정상 표출.
* Tauri IPC를 사용하여 프론트엔드의 `MouseEngine`이 측정한 타깃 좌표와 동작 이벤트를 Rust 백엔드로 주입하는 구조 확립.
* macOS 최적화를 위해 가상 화면 전환 시에도 앱 창이 자동으로 모든 워크스페이스에 연동되도록 `set_visible_on_all_workspaces` 처리 완료.

---

## 5. 로컬 빌드 및 실행 방법

### 1) Python Native 실행
```bash
# 가상환경 활성화 후 의존성 설치
pip install opencv-python mediapipe pynput pyautogui numpy
python main.py
```
* 디버그 창 포커스 상태에서 단축키:
  * `c`: 실시간 캘리브레이션 시작 (손 활짝 펴기 -> 꽉 쥐기 순서로 안내선 제공)
  * `w`/`s`: 좌클릭 트리거 임계값 미세 증가/감소
  * `e`/`d`: 좌클릭 해제 임계값 미세 증가/감소

### 2) Tauri GUI Desktop App 실행
```bash
cd ai_mouse_tauri
npm install
# 개발 모드 기동 (React 개발 서버 + Tauri 앱 동시 기동)
npm run tauri dev
```

---

## 6. 배포 및 서버 다운로드 서비스 구축 방안

사용자가 서버에서 본 애플리케이션을 손쉽게 다운로드받아 설치하고 실행할 수 있도록 하는 최적의 3단계 배포 방안을 제시합니다.

### Step 1. OS별 네이티브 설치 패키지 릴리즈 빌드

Tauri는 OS별 컴파일 환경을 제공하여 최적화된 설치 본을 자동으로 빌드해 줍니다. 릴리즈 빌드를 뽑기 위해 아래 과정을 실행합니다.

```bash
cd ai_mouse_tauri
# 릴리즈 버전 빌드 실행
npm run tauri build
```

#### OS별 출력물 및 주의 사항
* **macOS (Apple Silicon & Intel)**
  * **출력물**: `ai_mouse_tauri_0.1.0_x64.dmg` (또는 `aarch64.dmg`), `.app` 번들
  * **주의사항**: macOS는 Gatekeeper 보안 정책상 Code Signing 및 Notarization(공증)을 거치지 않은 앱은 실행 시 경고창이 뜨며 차단됩니다. 정식 배포를 위해서는 Apple Developer Account가 필요하며, 빌드 환경변수에 `APPLE_SIGNING_IDENTITY` 및 공증 자격 증명을 입력해야 합니다.
* **Windows (x64)**
  * **출력물**: `ai_mouse_tauri_0.1.0_x64_en-US.msi` (Wix Toolset 필요) 또는 `ai_mouse_tauri_0.1.0_x64-setup.exe` (NSIS)
  * **주의사항**: Windows Defender SmartScreen에 차단되지 않으려면 EV 코드 사인 인증서(Code Signing Certificate) 서명이 필요합니다.

---

### Step 2. 다운로드 서버 및 랜딩 페이지 배포 아키텍처

사용자가 접속하여 한 번의 클릭으로 본인의 OS에 맞는 설치 파일을 즉시 다운로드받을 수 있는 **하이브리드 웹 서버 아키텍처**를 구축합니다.

```
                  ┌──────────────────────────────┐
                  │      사용자 웹 브라우저       │
                  └──────────────┬───────────────┘
                                 │ 접속 (HTTPS)
                                 v
   ┌───────────────────────────────────────────────────────────┐
   │ 1. 정적 랜딩 웹 서버 (Vercel / Netlify / Cloudflare Pages) │
   │   - 프리미엄 유리모피즘 디자인의 소개 UI                  │
   │   - 접속 브라우저 OS 자동 감지 (OS-Detection Script)       │
   │   - 다운로드 클릭 시 최신 OS 패키지 바이너리로 리다이렉트 │
   └─────────────────────────────┬─────────────────────────────┘
                                 │ 바이너리 요청
                                 v
   ┌───────────────────────────────────────────────────────────┐
   │ 2. 객체 스토리지 및 릴리즈 저장소 (AWS S3 / GitHub Release)│
   │   - macOS: ai_mouse_tauri.dmg                             │
   │   - Windows: ai_mouse_tauri_setup.exe                     │
   │   - Tauri Auto-Updater를 위한 updates.json 매니페스트      │
   └───────────────────────────────────────────────────────────┘
```

#### ① 다운로드 유도형 프런트엔드 스크립트 (OS 자동 감지)
정적 랜딩 페이지에 아래 스크립트를 삽입하여 사용자가 접속한 OS에 최적화된 다운로드 링크를 첫 화면에 메인 버튼으로 자동 표출해 줍니다.
```javascript
function getDownloadLink() {
  const userAgent = window.navigator.userAgent.toLowerCase();
  const baseUrl = "https://your-storage-bucket.s3.ap-northeast-2.amazonaws.com/releases/v0.1.0/";
  
  if (userAgent.indexOf("mac") !== -1) {
    // Apple Silicon 여부 체크 후 분기 가능
    return { os: "macOS", url: baseUrl + "ai_mouse_tauri_0.1.0_x64.dmg" };
  } else if (userAgent.indexOf("win") !== -1) {
    return { os: "Windows", url: baseUrl + "ai_mouse_tauri_0.1.0_x64-setup.exe" };
  }
  return { os: "Unknown", url: "https://github.com/yourorg/ai-mouse/releases" };
}
```

---

### Step 3. GitHub Actions 기반의 자동 빌드 및 배포 CI/CD 파이프라인

개발 버전 코드를 `main` 브랜치에 푸시하거나 `v*.*.*` 태그를 생성할 때, OS별 설치 파일을 클라우드에 자동 빌드하여 업로드하는 GitHub Actions 워크플로를 제공합니다.

`.github/workflows/release.yml` 파일을 프로젝트 루트에 생성하여 연동합니다.

```yaml
name: Release CI/CD Pipeline

on:
  push:
    tags:
      - 'v*'

jobs:
  publish:
    permissions:
      contents: write
    strategy:
      fail-fast: false
      matrix:
        include:
          - platform: 'macos-latest' # macOS 빌드용
            args: '--target universal-apple-darwin'
          - platform: 'windows-latest' # Windows 빌드용
            args: ''

    runs-on: ${{ matrix.platform }}
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'
          cache-dependency-path: 'ai_mouse_tauri/package-lock.json'

      - name: Install Rust Toolchain
        uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.platform == 'macos-latest' && 'aarch64-apple-darwin,x86_64-apple-darwin' || '' }}

      - name: Install Node Dependencies
        run: |
          cd ai_mouse_tauri
          npm ci

      - name: Build Tauri Application
        uses: tauri-apps/tauri-action@v0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          # macOS 인증서가 있는 경우 아래 시크릿을 통해 공증 가능
          # APPLE_CERTIFICATE: ${{ secrets.APPLE_CERTIFICATE }}
          # APPLE_CERTIFICATE_PASSWORD: ${{ secrets.APPLE_CERTIFICATE_PASSWORD }}
          # APPLE_SIGNING_IDENTITY: ${{ secrets.APPLE_SIGNING_IDENTITY }}
          # APPLE_ID: ${{ secrets.APPLE_ID }}
          # APPLE_PASSWORD: ${{ secrets.APPLE_PASSWORD }}
        with:
          tagName: ${{ github.ref_name }}
          releaseName: 'God Hand v${{ github.ref_name }}'
          releaseBody: '자동 빌드된 God Hand AI 마우스 패키지 릴리즈 릴리즈입니다.'
          releaseDraft: false
          prerelease: false
          projectPath: './ai_mouse_tauri'
```

#### 파이프라인의 이점
1. **버전 일관성**: 태그 발행 시점(`v0.1.0`)에 코드 수정 없이 자동으로 빌드 완료.
2. **배포 확장성**: 생성된 GitHub Release URL을 랜딩 페이지 다운로드 버튼과 다이렉트로 링크하여 스토리지 비용 없이 배포 가능.
3. **Tauri Auto-Updater 지원**: Tauri의 `updater` 플러그인을 활성화하고 릴리즈 시 생성되는 `.json` 파일을 설정된 엔드포인트에 발행하면, 기설치된 앱이 서버를 호출하여 자동으로 백그라운드 무중단 업데이트를 진행하게 만듭니다.

---

> 💡 **추천 협업 워크플로**:
> 1. 각 운영체제(Mac/Windows)에서 빌드된 설치 본을 사내 혹은 공용 클라우드 스토리지(S3 등)에 업로드합니다.
> 2. Vercel/Netlify를 통해 `https://download.godhand-ai.com`과 같은 정적 URL을 개설하고 위 다운로드 스크립트를 연결하여 신속히 배포를 완료합니다.
