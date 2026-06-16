import { useEffect, useRef, useState } from "react";
import { FilesetResolver, HandLandmarker } from "@mediapipe/tasks-vision";
import { MouseEngine } from "./lib/engine";

// Windows UI Components
import { ActivityLog } from "./features/activity/ActivityLog";
import { CalibrationPanel } from "./features/calibration/CalibrationPanel";
import { CameraStatusPanel } from "./features/camera/CameraStatusPanel";
import { GestureRecognitionPanel } from "./features/gesture/GestureRecognitionPanel";
import { MouseControlPanel } from "./features/mouse/MouseControlPanel";
import { SettingsPanel } from "./features/settings/SettingsPanel";
import { SystemHealthPanel } from "./features/system/SystemHealthPanel";
import type {
  ActivityEvent,
  CalibrationRuntimeState,
  CameraRuntimeState,
  MouseRuntimeState,
  VisionRuntimeState,
} from "./lib/controlCenterTypes";

function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [engine] = useState(() => new MouseEngine());
  const [isLoaded, setIsLoaded] = useState(false);
  const [status, setStatus] = useState("Initializing AI Core...");
  
  // Real-time telemetry metrics state (Original Mac Logic)
  const [metrics, setMetrics] = useState({
    status: "IDLE",
    isResting: false,
    isPinching: false,
    dragMode: false,
    isRightPinching: false,
    isScrollMode: false,
    structuralIntegrity: 1.0,
    iVec: 0.0,
    mVec: 0.0,
    iScore: 0.0,
    mScore: 0.0,
    indexRatio: 0.5,
    middleRatio: 0.5,
    onThreshold: 0.18,
    offThreshold: 0.28,
    isCalibrating: false,
    calibStep: 0,
    calibProgress: 0,
    fps: 0,
    deviceLabel: "선택된 카메라 없음",
    resolution: "-",
  });

  const [events, setEvents] = useState<ActivityEvent[]>([]);

  useEffect(() => {
    // 🔌 [v8.4] 백그라운드 App Nap 방지를 위한 무음 오디오 루프 재생 기법
    const audio = new Audio("data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAAA");
    audio.loop = true;
    audio.volume = 0.001;

    const playAudio = () => {
      audio.play().catch(err => {
        console.warn("Silent audio loop playback deferred until user interaction:", err);
      });
    };

    window.addEventListener("click", playAudio, { once: true });
    window.addEventListener("keydown", playAudio, { once: true });

    let handLandmarker: HandLandmarker;
    let worker: Worker | null = null;
    let workerUrl = "";
    let frameCount = 0;
    let lastFpsUpdateTime = performance.now();
    let currentFps = 0;
    let isProcessing = false;
    let streamLabel = "카메라";
    let streamRes = "1280 x 720";

    const initMediaPipe = async () => {
      try {
        setStatus("Loading MediaPipe WASM...");
        const vision = await FilesetResolver.forVisionTasks("/wasm");
        
        setStatus("Loading Hand Tracking Model...");
        handLandmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: `/model/hand_landmarker.task`,
          },
          runningMode: "VIDEO",
          numHands: 1,
          minHandDetectionConfidence: 0.7,
          minHandPresenceConfidence: 0.7,
          minTrackingConfidence: 0.5,
        });

        setStatus("Requesting Web Camera...");
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { 
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: "user"
          },
        });
        
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          
          const track = stream.getVideoTracks()[0];
          const settings = track.getSettings();
          streamLabel = track.label || "사용 중인 카메라";
          streamRes = `${settings.width ?? 1280} x ${settings.height ?? 720}`;
          
          // 🚀 [v8.4] Web Worker 기반의 60fps 정밀 틱 타이머 도입
          const workerCode = `
            let timer = null;
            self.onmessage = function(e) {
              if (e.data === 'start') {
                if (timer) clearInterval(timer);
                timer = setInterval(() => {
                  self.postMessage('tick');
                }, 16);
              } else if (e.data === 'stop') {
                if (timer) clearInterval(timer);
              }
            };
          `;
          const blob = new Blob([workerCode], { type: "application/javascript" });
          workerUrl = URL.createObjectURL(blob);
          worker = new Worker(workerUrl);

          worker.onmessage = (e) => {
            if (e.data === "tick") {
              predictWebcam();
            }
          };

          videoRef.current.play()
            .then(() => {
              if (worker) worker.postMessage("start");
              playAudio();
            })
            .catch(err => {
              console.error("Video play failed, attempting fallback:", err);
              if (worker) worker.postMessage("start");
            });
        }
        
        setIsLoaded(true);
        setStatus("System Live");
      } catch (error: any) {
        console.error("Initialization failed", error);
        setStatus(`Init Failed: ${error.message || error.toString()}`);
      }
    };

    const predictWebcam = async () => {
      if (!videoRef.current || !canvasRef.current || !handLandmarker) return;
      if (isProcessing) return;
      isProcessing = true;

      try {
        const now = performance.now();
        frameCount++;
        if (now - lastFpsUpdateTime >= 1000) {
          currentFps = Math.round((frameCount * 1000) / (now - lastFpsUpdateTime));
          frameCount = 0;
          lastFpsUpdateTime = now;
        }

        const results = handLandmarker.detectForVideo(videoRef.current, now);

        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          
          const isCalibrating = engine.calibManager.isActive;
          const calibStep = engine.calibManager.step;
          let calibProgress = 0;
          if (isCalibrating) {
            const elapsed = (Date.now() / 1000) - engine.calibManager.startTime;
            calibProgress = Math.min(100, Math.max(0, (elapsed / engine.calibManager.scanTime) * 100));
          }

          if (results.landmarks && results.landmarks.length > 0) {
            const landmarks = results.landmarks[0];
            const worldLandmarks = results.worldLandmarks && results.worldLandmarks.length > 0
              ? results.worldLandmarks[0]
              : [];
            
            await engine.process(landmarks, worldLandmarks, window.screen.width, window.screen.height);
            
            // 기존 Mac 버전의 고품질 HUD 그리기 함수 호출
            drawHUD(ctx, landmarks);

            setMetrics({
              status: engine.isResting 
                ? "RESTING" 
                : isCalibrating 
                  ? `CALIBRATING STEP ${calibStep}` 
                  : engine.isScrollMode 
                    ? "SCROLL" 
                    : engine.dragMode 
                      ? "DRAG" 
                      : engine.isPinching 
                        ? "L-PINCH" 
                        : engine.isRightPinching 
                          ? "R-PINCH" 
                          : "ACTIVE",
              isResting: engine.isResting,
              isPinching: engine.isPinching,
              dragMode: engine.dragMode,
              isRightPinching: engine.isRightPinching,
              isScrollMode: engine.isScrollMode,
              structuralIntegrity: engine.structuralIntegrity,
              iVec: engine.iVec,
              mVec: engine.mVec,
              iScore: engine.iScore,
              mScore: engine.mScore,
              indexRatio: engine.indexRatio,
              middleRatio: engine.middleRatio,
              onThreshold: engine.calibManager.onThreshold,
              offThreshold: engine.calibManager.offThreshold,
              isCalibrating,
              calibStep,
              calibProgress,
              fps: currentFps,
              deviceLabel: streamLabel,
              resolution: streamRes
            });
          } else {
            setMetrics(prev => ({
              ...prev,
              status: isCalibrating ? `CALIBRATING STEP ${calibStep}` : "NO HAND DETECTED",
              isResting: false,
              structuralIntegrity: 0.0,
              isCalibrating,
              calibStep,
              calibProgress,
              fps: currentFps,
              deviceLabel: streamLabel,
              resolution: streamRes
            }));
          }
        }
      } catch (err) {
        console.error("Frame processing error:", err);
      } finally {
        isProcessing = false;
      }
    };

    const drawHUD = (ctx: CanvasRenderingContext2D, landmarks: any[]) => {
      const connections = [
        [0, 1], [1, 2], [2, 3], [3, 4], // Thumb
        [0, 5], [5, 6], [6, 7], [7, 8], // Index
        [5, 9], [9, 10], [10, 11], [11, 12], // Middle
        [9, 13], [13, 14], [14, 15], [15, 16], // Ring
        [13, 17], [17, 18], [18, 19], [19, 20], // Pinky
        [0, 17], [5, 9], [9, 13], [13, 17] // Palm bottom
      ];

      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
      ctx.lineWidth = 3.5;
      ctx.shadowBlur = 10;
      ctx.shadowColor = "rgba(14, 165, 233, 0.8)";
      
      connections.forEach(([s, e]) => {
        const ptStart = landmarks[s];
        const ptEnd = landmarks[e];
        if (ptStart && ptEnd) {
          ctx.beginPath();
          ctx.moveTo(ptStart.x * 640, ptStart.y * 360);
          ctx.lineTo(ptEnd.x * 640, ptEnd.y * 360);
          ctx.stroke();
        }
      });
      
      ctx.shadowBlur = 0;

      landmarks.forEach((p, idx) => {
        let color = "rgba(255, 255, 255, 0.9)";
        let radius = 2.5;

        if (idx === 4) {
          color = "#34d399";
          radius = 4.5;
        } else if (idx === 8) {
          color = "#38bdf8";
          radius = 4.5;
        } else if (idx === 12) {
          color = "#fb7185";
          radius = 4.5;
        } else if (idx === 0) {
          color = "#a78bfa";
          radius = 5.5;
        }

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(p.x * 640, p.y * 360, radius, 0, 2 * Math.PI);
        ctx.fill();

        if (idx === 4 || idx === 8 || idx === 12) {
          ctx.strokeStyle = color;
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(p.x * 640, p.y * 360, radius + 5, 0, 2 * Math.PI);
          ctx.stroke();
        }
      });

      if (engine.isResting) {
        ctx.fillStyle = "rgba(239, 68, 68, 0.12)";
        ctx.fillRect(0, 0, 640, 360);
        ctx.strokeStyle = "rgba(239, 68, 68, 0.6)";
        ctx.lineWidth = 2;
        ctx.strokeRect(10, 10, 620, 340);
      }
    };

    initMediaPipe();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "c" || e.key === "C") {
        engine.calibManager.start();
      }
    };
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("click", playAudio);
      if (worker) {
        worker.postMessage("stop");
        worker.terminate();
      }
      if (workerUrl) {
        URL.revokeObjectURL(workerUrl);
      }
      audio.pause();
      if (handLandmarker) handLandmarker.close();
    };
  }, [engine]);

  // Push Event Helper for UI
  const pushEvent = (message: string, tone: ActivityEvent["tone"] = "neutral") => {
    setEvents((current) => {
        const id = crypto.randomUUID();
        const time = new Intl.DateTimeFormat("ko-KR", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: false,
        }).format(new Date());
        return [{ id, time, message, tone }, ...current].slice(0, 10);
    });
  };

  // State Mapping for Windows UI Components
  const cameraState: CameraRuntimeState = {
    status: isLoaded ? "streaming" : "requesting",
    device: metrics.deviceLabel,
    resolution: metrics.resolution,
    frameRate: metrics.fps || 0,
    error: null,
  };

  const visionState: VisionRuntimeState = {
    status: isLoaded ? "detecting" : "loading",
    gesture: metrics.status,
    landmarks: metrics.status === "NO HAND DETECTED" ? 0 : 21,
    confidence: metrics.structuralIntegrity,
    pinchDistance: metrics.indexRatio, // Windows UI uses this for gauge
    error: null,
  };

  const mouseState: MouseRuntimeState = {
    enabled: true, // Native Mac app is always enabled while running
    bridge: "ready", // Mac version relies on built-in native communication
    screen: { width: window.screen.width, height: window.screen.height },
    position: { x: engine.prevX, y: engine.prevY },
    lastAction: metrics.status,
    error: null,
  };

  const calibrationState: CalibrationRuntimeState = {
    active: metrics.isCalibrating,
    samples: metrics.calibStep, // UI uses samples to show step usually
    progress: metrics.calibProgress,
    bounds: null,
  };

  const toggleMouse = () => {
    pushEvent("Mac 버전은 항상 마우스를 직접 제어합니다.", "blue");
  };

  const handleCalibStart = () => {
    engine.calibManager.start();
    pushEvent("캘리브레이션 시작됨.", "blue");
  };

  const handleCalibReset = () => {
    if ((engine.calibManager as any).reset) {
        (engine.calibManager as any).reset();
    }
    pushEvent("캘리브레이션 초기화됨.", "neutral");
  };

  return (
    <main className="app-shell">
      <section className="hero-panel">


        <div className="hero-copy">
          <p className="eyebrow">God Hand / Aetheris Engine</p>
          <h1>God Hand Control Center</h1>
          <p>MediaPipe WASM으로 손을 인식하고 Tauri IPC를 통해 Rust가 마우스를 제어합니다.</p>
        </div>

        <div className="hero-actions">
          <button
            className="primary-button"
            onClick={() => pushEvent("웹캠 연결은 시작 시 자동 처리됩니다.", "neutral")}
          >
            카메라 자동 연동 중
          </button>
          <button
            className="secondary-button"
            onClick={toggleMouse}
          >
            마우스 제어 중
          </button>
        </div>
      </section>

      <section className="camera-workspace">
        <div className="live-camera">
          <video ref={videoRef} autoPlay playsInline muted style={{ transform: "scaleX(-1)" }} />
          <canvas ref={canvasRef} width={640} height={360} className="hand-overlay" style={{ transform: "scaleX(-1)" }} />
          {!isLoaded ? (
            <div className="camera-empty">
              <strong>시스템 및 카메라를 초기화 중입니다...</strong>
              <span>{status}</span>
            </div>
          ) : null}
        </div>
        <CameraStatusPanel camera={cameraState} />
      </section>

      <section className="dashboard-grid" aria-label="제어 센터 패널">
        <GestureRecognitionPanel vision={visionState} />
        <MouseControlPanel mouse={mouseState} onToggle={toggleMouse} />
        <CalibrationPanel
          calibration={calibrationState}
          isCameraActive={cameraState.status === "streaming"}
          onStart={handleCalibStart}
          onReset={handleCalibReset}
        />
        <ActivityLog events={events} />
        <SystemHealthPanel cameraStatus={cameraState.status} visionStatus={visionState.status} mouse={mouseState} />
        <SettingsPanel mouse={mouseState} />
      </section>
    </main>
  );
}

export default App;
