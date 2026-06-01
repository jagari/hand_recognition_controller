import { useEffect, useRef, useState } from "react";
import { FilesetResolver, HandLandmarker } from "@mediapipe/tasks-vision";
import { MouseEngine } from "./lib/engine";
import "./App.css";

function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [engine] = useState(() => new MouseEngine());
  const [isLoaded, setIsLoaded] = useState(false);
  const [status, setStatus] = useState("Initializing AI...");

  useEffect(() => {
    let handLandmarker: HandLandmarker;
    let animationId: number;

    const initMediaPipe = async () => {
      try {
        setStatus("Loading MediaPipe WASM...");
        const vision = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
        );
        
        setStatus("Loading Hand Tracking Model...");
        handLandmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`,
          },
          runningMode: "VIDEO",
          numHands: 1,
        });

        setStatus("Requesting Camera...");
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { 
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: "user"
          },
        });
        
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.addEventListener("loadeddata", predictWebcam);
        }
        
        setIsLoaded(true);
        setStatus("System Ready");
      } catch (error: any) {
        console.error("Initialization failed", error);
        setStatus(`Init Failed: ${error.message || error.toString()}`);
      }
    };

    const predictWebcam = async () => {
      if (!videoRef.current || !canvasRef.current || !handLandmarker) return;

      const startTimeMs = performance.now();
      const results = handLandmarker.detectForVideo(videoRef.current, startTimeMs);

      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (results.landmarks && results.landmarks.length > 0) {
          const landmarks = results.landmarks[0];
          
          // 엔진 프로세싱 호출 (비동기)
          engine.process(landmarks, window.screen.width, window.screen.height);
          
          // HUD 그리기
          drawHUD(ctx, landmarks);
        }
      }

      animationId = requestAnimationFrame(predictWebcam);
    };

    const drawHUD = (ctx: CanvasRenderingContext2D, landmarks: any[]) => {
      // 랜드마크 포인트 시각화
      ctx.fillStyle = "#00FF00";
      landmarks.forEach((p) => {
        ctx.beginPath();
        ctx.arc(p.x * 640, p.y * 360, 2, 0, 2 * Math.PI);
        ctx.fill();
      });

      // 상태 표시
      ctx.fillStyle = "white";
      ctx.font = "16px Arial";
      if (engine.calibManager.isActive) {
        ctx.fillText("CALIBRATING...", 20, 40);
      }
    };

    initMediaPipe();

    return () => {
      cancelAnimationFrame(animationId);
      if (handLandmarker) handLandmarker.close();
    };
  }, [engine]);

  return (
    <div className="container">
      <div className="video-wrapper">
        <video ref={videoRef} autoPlay playsInline className="input-video" />
        <canvas ref={canvasRef} width={640} height={360} className="output-canvas" />
      </div>
      
      <div className="controls">
        <h1>AI Mouse v3.0</h1>
        <p className="status-text">{status}</p>
        <button 
          onClick={() => engine.calibManager.start()} 
          disabled={!isLoaded}
          className="btn-calib"
        >
          Start Calibration ('C')
        </button>
        
        <div className="info-panel">
          <p>L-Click: Pinch Index</p>
          <p>R-Click: Pinch Middle</p>
          <p>Drag: Hold Pinch</p>
        </div>
      </div>
    </div>
  );
}

export default App;
