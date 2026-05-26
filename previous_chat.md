# Project: AI Vision Hand-Tracking Mouse Controller

## 1. 프로젝트 개요
웹캠 입력을 기반으로 한 상용급 핸드 트래킹 마우스 에이전트.

## 2. 현재 시스템 아키텍처 (AI Mouse Engine v2.0)
단순 거리 측정을 넘어 사용자의 '의도'를 수학적으로 분석하는 **Intent-Driven Clustering** 엔진으로 업그레이드 완료.

### 핵심 구성 요소:
1. **Gaussian Clustering Calibration**: 수집된 데이터를 통계적으로 분석하여 '펴짐'과 '꼬집음' 군집을 완벽히 분리.
2. **Velocity-based Intent Detection**: 손가락이 모이는 속도를 분석하여 클릭 의도가 강할 때 반응성을 순간적으로 증폭.
3. **Adaptive Hysteresis**: 손떨림과 조작 습관에 따라 ON/OFF 임계값을 지능적으로 가변 관리.
4. **Occlusion-Resistant Fusion**: 다중 관절 참조를 통해 손의 회전 및 겹침 상황에서도 안정적인 인식 유지.

---

## 5. 작업 기록 (Activity Log)

### [2026-05-18] 설정 영속성(Persistence) 구현
*   **config.json 시스템**: 캘리브레이션 임계값을 로컬 파일에 저장하고 앱 재시작 시 자동으로 로드하는 기능을 추가.
*   **자동 저장**: 캘리브레이션 종료 및 키보드 수동 조절 시 실시간으로 설정을 저장하도록 개선.
*   **VCS 보안**: 사용자별 최적화 데이터가 공유되지 않도록 `.gitignore`에 `config.json` 추가.

### [2026-05-18] AI Mouse Engine v2.0 구현 및 손가락 구분 강화
*   **지능형 군집 분석**: `core/calibration.py`에 Gaussian Clustering 방식을 도입하여 사용자별 '펴짐'과 '꼬집음' 상태를 수학적으로 분리.
*   **의도 기반 반응성(Intent Boost)**: 손가락이 모이는 속도를 분석하여 클릭 의사가 강할 때 임계값을 순간적으로 완화, 반응 속도를 획기적으로 향상.
*   **이중 채널 지배력 판정**: 검지와 중지 중 엄지에 더 가까운 손가락에 우선권을 주는 'Dominance Margin' 로직을 통해 좌/우클릭 오작동 해결.
*   **HUD v2.0**: 검지(I)와 중지(M)의 상태를 실시간으로 모니터링할 수 있는 듀얼 바 HUD 구축.
*   **디버깅**: HUD 호출 시 발생하던 인자 누락 에러 및 'SIDE' 뷰 오인식 인덱스 오류 수정.

### [2026-05-18] 원천 인식률(Landmark Detection) 강화
*   **모델 복잡도 상향**: MediaPipe 모델 복잡도를 0에서 1로 높여 손가락 관절의 정밀도 향상.
*   **신뢰도 최적화**: Detection/Tracking Confidence를 재조정하여 흔들림 최소화.
