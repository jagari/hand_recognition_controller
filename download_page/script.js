// OS Detection & Button Update
document.addEventListener("DOMContentLoaded", () => {
  detectOSAndUpdateButton();
  initPortal();
  initMacModal();
});

function detectOSAndUpdateButton() {
  const userAgent = window.navigator.userAgent.toLowerCase();
  const btn = document.getElementById("download-btn");
  const iconSpan = document.getElementById("btn-icon");
  const titleSpan = document.getElementById("btn-title");
  const subtitleSpan = document.getElementById("btn-subtitle");
  
  const winLink = "https://github.com/cksdyd3786/god-hand/raw/main/ai_mouse_tauri/src-tauri/target/release/bundle/nsis/God%20Hand_0.1.0_x64-setup.exe";
  const macArmLink = "https://github.com/jagari/hand_recognition_controller/raw/develop/download_page/files/ai_mouse_tauri_0.1.0_aarch64.dmg";
  const macIntelLink = "https://github.com/jagari/hand_recognition_controller/raw/develop/download_page/files/ai_mouse_tauri_0.1.0_x64.dmg";
  
  // Set default links on the small alternative text links
  if (document.getElementById("link-win")) document.getElementById("link-win").href = winLink;
  if (document.getElementById("link-mac-arm")) document.getElementById("link-mac-arm").href = macArmLink;
  if (document.getElementById("link-mac-intel")) document.getElementById("link-mac-intel").href = macIntelLink;

  if (userAgent.indexOf("mac") !== -1) {
    // Detect Apple Silicon vs Intel
    let arch = "intel";
    try {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
      if (gl) {
        const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
        if (debugInfo) {
          const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL).toLowerCase();
          if (renderer.includes("apple") || renderer.includes("m1") || renderer.includes("m2") || renderer.includes("m3") || renderer.includes("m4") || renderer.includes("silicon")) {
            arch = "arm64";
          }
        }
      }
    } catch (e) {}

    if (arch === "arm64") {
      btn.href = macArmLink;
      iconSpan.textContent = "🍏";
      titleSpan.textContent = "macOS용 다운로드 (.dmg)";
      subtitleSpan.textContent = "Apple Silicon 전용 빌드 v0.1.0";
    } else {
      btn.href = macIntelLink;
      iconSpan.textContent = "🍏";
      titleSpan.textContent = "macOS용 다운로드 (.dmg)";
      subtitleSpan.textContent = "Intel CPU 전용 빌드 v0.1.0";
    }
  } else if (userAgent.indexOf("win") !== -1) {
    btn.href = winLink;
    iconSpan.textContent = "🪟";
    titleSpan.textContent = "Windows용 다운로드 (.exe)";
    subtitleSpan.textContent = "x64 데스크톱 설치 패키지 v0.1.0";
  } else {
    // Default fallback
    btn.href = "https://github.com/jagari/hand_recognition_controller/releases";
    iconSpan.textContent = "📦";
    titleSpan.textContent = "최신 릴리즈 다운로드";
    subtitleSpan.textContent = "모든 OS 플랫폼 아카이브 지원";
  }

  // 🚀 깃허브 Releases 최신 업로드 자산 동적 연결 시도 (비동기)
  upgradeLinksToGitHubReleases();
}

async function upgradeLinksToGitHubReleases() {
  const linkWin = document.getElementById("link-win");
  const linkMacArm = document.getElementById("link-mac-arm");
  const linkMacIntel = document.getElementById("link-mac-intel");
  const btn = document.getElementById("download-btn");
  const userAgent = window.navigator.userAgent.toLowerCase();

  // 1. Fetch macOS Releases from jagari/hand_recognition_controller
  try {
    const response = await fetch("https://api.github.com/repos/jagari/hand_recognition_controller/releases/latest");
    if (response.ok) {
      const data = await response.json();
      if (data.assets && data.assets.length > 0) {
        let macArmLink = "";
        let macIntelLink = "";

        data.assets.forEach(asset => {
          const name = asset.name.toLowerCase();
          const url = asset.browser_download_url;
          if (name.endsWith(".dmg")) {
            if (name.includes("aarch64") || name.includes("arm64")) {
              macArmLink = url;
            } else {
              macIntelLink = url;
            }
          }
        });

        if (macArmLink && linkMacArm) {
          linkMacArm.href = macArmLink;
          if (userAgent.indexOf("mac") !== -1 && isAppleSilicon() && btn) {
            btn.href = macArmLink;
          }
        }
        if (macIntelLink && linkMacIntel) {
          linkMacIntel.href = macIntelLink;
          if (userAgent.indexOf("mac") !== -1 && !isAppleSilicon() && btn) {
            btn.href = macIntelLink;
          }
        }
      }
    }
  } catch (err) {
    console.warn("macOS GitHub Release API 호출 실패:", err);
  }

  // 2. Fetch Windows Releases from cksdyd3786/god-hand
  try {
    const response = await fetch("https://api.github.com/repos/cksdyd3786/god-hand/releases/latest");
    if (response.ok) {
      const data = await response.json();
      if (data.assets && data.assets.length > 0) {
        let winLink = "";

        data.assets.forEach(asset => {
          const name = asset.name.toLowerCase();
          const url = asset.browser_download_url;
          if (name.endsWith(".exe") || name.endsWith(".msi")) {
            winLink = url;
          }
        });

        if (winLink && linkWin) {
          linkWin.href = winLink;
          if (userAgent.indexOf("win") !== -1 && btn) {
            btn.href = winLink;
          }
        }
      }
    }
  } catch (err) {
    console.warn("Windows GitHub Release API 호출 실패:", err);
  }
}

// Helper function to detect Apple Silicon
function isAppleSilicon() {
  try {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
    if (gl) {
      const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
      if (debugInfo) {
        const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL).toLowerCase();
        if (renderer.includes("apple") || renderer.includes("m1") || renderer.includes("m2") || renderer.includes("m3") || renderer.includes("m4") || renderer.includes("silicon")) {
          return true;
        }
      }
    }
  } catch (e) {}
  return false;
}

// 🖐️ God Hand Interactive Portal Controls
function initPortal() {
  // 1. Tab Switching Control
  const tabs = document.querySelectorAll(".tab-btn");
  const contents = document.querySelectorAll(".portal-tab-content");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      // Deactivate all
      tabs.forEach(t => t.classList.remove("active"));
      contents.forEach(c => c.classList.remove("active"));

      // Activate clicked
      tab.classList.add("active");
      const targetId = tab.getAttribute("data-tab");
      const activeContent = document.getElementById(targetId);
      if (activeContent) {
        activeContent.classList.add("active");
        
        // Trigger resize / canvas setup if mockup tab is opened
        if (targetId === "tab-mockup") {
          window.dispatchEvent(new Event("resize"));
          const stopBtn = document.getElementById("stop-diag-btn");
          if (stopBtn && stopBtn.style.display !== "none") {
            stopBtn.click();
          }
        }
      }
    });
  });

  // OS Info Telemetry Auto Detect
  const telOs = document.getElementById("tel-os");
  if (telOs) {
    const platform = window.navigator.platform || "";
    if (platform.toLowerCase().includes("mac")) {
      telOs.textContent = "macOS (" + (navigator.userAgent.includes("Macintosh") ? "Intel & Apple Silicon" : "Universal") + ")";
    } else if (platform.toLowerCase().includes("win")) {
      telOs.textContent = "Windows (x64)";
    } else {
      telOs.textContent = platform || "Linux / Unknown OS";
    }
  }

  // 2. Tab 1: Webcam Diagnostics Logic
  const startDiagBtn = document.getElementById("start-diag-btn");
  const stopDiagBtn = document.getElementById("stop-diag-btn");
  const webcamVideo = document.getElementById("webcam-video");
  const viewportPlaceholder = document.getElementById("viewport-placeholder");
  const viewportOverlay = document.getElementById("viewport-overlay");
  const diagBadge = document.getElementById("diag-badge");
  const telCam = document.getElementById("tel-cam");
  const telRes = document.getElementById("tel-res");
  const telAi = document.getElementById("tel-ai");

  let webcamStream = null;

  if (startDiagBtn) {
    startDiagBtn.addEventListener("click", async () => {
      try {
        startDiagBtn.textContent = "카메라 연결 시도 중...";
        
        webcamStream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480, facingMode: "user" }
        });

        // Binding stream
        webcamVideo.srcObject = webcamStream;
        webcamVideo.style.display = "block";
        viewportPlaceholder.style.display = "none";
        viewportOverlay.style.display = "block";
        if (stopDiagBtn) {
          stopDiagBtn.style.display = "flex";
        }

        diagBadge.textContent = "ACTIVE";
        diagBadge.className = "status-badge active";

        telCam.textContent = "CONNECTED (60FPS)";
        telAi.textContent = "ACTIVE (READY)";
        
        // Retrieve stream properties
        webcamVideo.onloadedmetadata = () => {
          const w = webcamVideo.videoWidth;
          const h = webcamVideo.videoHeight;
          telRes.textContent = `${w} x ${h}`;
        };
      } catch (err) {
        console.error("Camera Diagnostics Failed:", err);
        startDiagBtn.textContent = "웹캠 진단 다시 시작";
        
        diagBadge.textContent = "ERROR";
        diagBadge.className = "status-badge error";

        telCam.textContent = "DISCONNECTED / RESTRICTED";
        telAi.textContent = "FAILED";
        
        // Show error notice in placeholder
        const pTitle = viewportPlaceholder.querySelector(".placeholder-title");
        const pSub = viewportPlaceholder.querySelector(".placeholder-sub");
        if (pTitle) pTitle.textContent = "카메라 연결에 실패했습니다.";
        if (pSub) pSub.textContent = "브라우저 카메라 접근 권한을 확인하시거나,\n연결된 웹캠 기기가 다른 앱에서 사용 중인지 체크해 주세요.";
      }
    });
  }

  if (stopDiagBtn) {
    stopDiagBtn.addEventListener("click", () => {
      if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
      }
      webcamVideo.srcObject = null;
      webcamVideo.style.display = "none";
      viewportPlaceholder.style.display = "flex";
      viewportOverlay.style.display = "none";
      stopDiagBtn.style.display = "none";

      diagBadge.textContent = "STANDBY";
      diagBadge.className = "status-badge";
      
      telCam.textContent = "NOT CONNECTED";
      telRes.textContent = "N/A";
      telAi.textContent = "STANDBY";
      
      startDiagBtn.textContent = "웹캠 진단 시작";
    });
  }

  // 3. Tab 2: Tauri GUI App Mockup Simulator
  initMockupScreen();
}

function initMockupScreen() {
  const canvas = document.getElementById("mockup-screen-canvas");
  if (!canvas) return;
  
  const ctx = canvas.getContext("2d");
  const screenArea = canvas.parentElement;
  
  // UI controls
  const sensitivityInput = document.getElementById("param-sensitivity");
  const sensitivityValueText = document.getElementById("val-sensitivity");
  const togglePredictive = document.getElementById("param-predictive");
  const toggleSniper = document.getElementById("param-sniper");
  const toggleGate = document.getElementById("param-gate");
  const screenHud = document.getElementById("screen-hud-status");

  let width = (canvas.width = screenArea.clientWidth);
  let height = (canvas.height = screenArea.clientHeight);

  window.addEventListener("resize", () => {
    width = canvas.width = screenArea.clientWidth;
    height = canvas.height = screenArea.clientHeight;
  });

  // Simulator target cursor position
  let mouse = { x: width / 2, y: height / 2 };
  let currentTarget = { x: width / 2, y: height / 2 };
  let isMouseDown = false;
  let isMouseOver = false;

  // Track pointer interaction within screen area
  screenArea.addEventListener("mousemove", (e) => {
    const rect = screenArea.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
    isMouseOver = true;
  });

  screenArea.addEventListener("mouseleave", () => {
    isMouseOver = false;
  });

  screenArea.addEventListener("mousedown", () => {
    isMouseDown = true;
  });

  screenArea.addEventListener("mouseup", () => {
    isMouseDown = false;
  });

  // Slider change detection
  sensitivityInput.addEventListener("input", (e) => {
    sensitivityValueText.textContent = parseFloat(e.target.value).toFixed(1);
  });

  // Loop simulation
  function loop() {
    ctx.clearRect(0, 0, width, height);

    // 1. Draw Virtual Desktop Elements
    drawVirtualDesktop();

    // 2. Control values and parameters mapping
    const sensVal = parseFloat(sensitivityInput.value);
    
    // Lerp factor mapping (Higher sensitivity = higher lerp factor)
    let lerpFactor = sensVal * 0.038 + 0.015;

    // Sniper mode click viscosity overrides tracking speed
    const sniperActive = toggleSniper.checked && isMouseDown && isMouseOver;
    if (sniperActive) {
      lerpFactor = 0.012; // Very slow coordinate movement
    }

    // Move current target cursor towards user pointer
    if (isMouseOver) {
      currentTarget.x += (mouse.x - currentTarget.x) * lerpFactor;
      currentTarget.y += (mouse.y - currentTarget.y) * lerpFactor;
    }

    // 3. Render tracking graphics
    if (isMouseOver) {
      // Draw Predictive lookahead line
      if (togglePredictive.checked) {
        drawPredictiveKinematics();
      }

      // Draw virtual Cursor Dot
      drawVirtualCursor(sniperActive);

      // Draw Sniper locked Reticle
      if (sniperActive) {
        drawSniperLockReticle();
      }
    }

    // 4. Update HUD state based on settings and clicks
    updateMockupHUD(sniperActive);

    requestAnimationFrame(loop);
  }

  // Draw cyber grid and OS desktop mockup elements
  function drawVirtualDesktop() {
    // Cyber Grid background
    ctx.strokeStyle = "rgba(255, 255, 255, 0.015)";
    ctx.lineWidth = 1;
    const grid = 25;
    for (let x = 0; x < width; x += grid) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke();
    }
    for (let y = 0; y < height; y += grid) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
    }

    // Draw mockup OS file icons (glassmorphism boxes)
    drawMockupIcon(30, 30, "📁 System");
    drawMockupIcon(30, 90, "🌐 Browser");
    drawMockupIcon(30, 150, "🎮 Game.exe");
  }

  function drawMockupIcon(x, y, label) {
    ctx.fillStyle = "rgba(255, 255, 255, 0.02)";
    ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    if (ctx.roundRect) {
      ctx.roundRect(x, y, 50, 40, 6);
    } else {
      ctx.rect(x, y, 50, 40);
    }
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = "rgba(148, 163, 184, 0.6)";
    ctx.font = "8px Outfit";
    ctx.textAlign = "center";
    ctx.fillText(label, x + 25, y + 52);
    ctx.textAlign = "left"; // reset
  }

  function drawVirtualCursor(clicked) {
    // Glow shadow
    ctx.shadowBlur = 8;
    ctx.shadowColor = clicked ? "rgba(16, 185, 129, 0.6)" : "rgba(14, 165, 233, 0.6)";
    
    // Core Cursor pointer (neon arrowhead shape)
    ctx.fillStyle = clicked ? "#10b981" : "#0ea5e9";
    ctx.beginPath();
    ctx.moveTo(currentTarget.x, currentTarget.y);
    ctx.lineTo(currentTarget.x + 8, currentTarget.y + 12);
    ctx.lineTo(currentTarget.x + 3, currentTarget.y + 11);
    ctx.lineTo(currentTarget.x, currentTarget.y + 16);
    ctx.closePath();
    ctx.fill();
    
    ctx.shadowBlur = 0; // reset
  }

  function drawPredictiveKinematics() {
    const dx = mouse.x - currentTarget.x;
    const dy = mouse.y - currentTarget.y;
    
    // Prediction lookahead vector
    const px = currentTarget.x + dx * 1.5;
    const py = currentTarget.y + dy * 1.5;

    ctx.strokeStyle = "rgba(14, 165, 233, 0.35)";
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 3]);

    ctx.beginPath();
    ctx.moveTo(currentTarget.x, currentTarget.y);
    ctx.lineTo(px, py);
    ctx.stroke();
    ctx.setLineDash([]);

    // Prediction point circle
    ctx.strokeStyle = "rgba(14, 165, 233, 0.65)";
    ctx.beginPath();
    ctx.arc(px, py, 3, 0, 2 * Math.PI);
    ctx.stroke();

    if (Math.hypot(dx, dy) > 3) {
      ctx.fillStyle = "rgba(14, 165, 233, 0.5)";
      ctx.font = "7px monospace";
      ctx.fillText("PRED +45ms", px + 8, py + 3);
    }
  }

  function drawSniperLockReticle() {
    const angle = Date.now() * 0.007;
    ctx.strokeStyle = "rgba(16, 185, 129, 0.7)";
    ctx.lineWidth = 1;
    
    // Outer rotating reticle
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.arc(currentTarget.x, currentTarget.y, 16, angle, angle + 2 * Math.PI);
    ctx.stroke();
    ctx.setLineDash([]);

    // Inner crosshair target
    ctx.beginPath();
    ctx.arc(currentTarget.x, currentTarget.y, 6, 0, 2 * Math.PI);
    ctx.stroke();

    // Small lock-on text
    ctx.fillStyle = "rgba(16, 185, 129, 0.8)";
    ctx.font = "8px Outfit";
    ctx.fillText("LOCK ON", currentTarget.x + 20, currentTarget.y - 4);
  }

  function updateMockupHUD(sniperActive) {
    if (!toggleGate.checked) {
      screenHud.textContent = "FILTER OFF";
      screenHud.style.color = "#ef4444";
      screenHud.style.background = "rgba(239, 68, 68, 0.1)";
      screenHud.style.borderColor = "rgba(239, 68, 68, 0.3)";
    } else if (sniperActive) {
      screenHud.textContent = "LOCKED";
      screenHud.style.color = "#10b981";
      screenHud.style.background = "rgba(16, 185, 129, 0.15)";
      screenHud.style.borderColor = "rgba(16, 185, 129, 0.4)";
    } else {
      screenHud.textContent = "PASS";
      screenHud.style.color = "#38bdf8";
      screenHud.style.background = "rgba(56, 189, 248, 0.1)";
      screenHud.style.borderColor = "rgba(56, 189, 248, 0.3)";
    }
  }

  loop();
}

// 🍏 macOS Gatekeeper Guide Modal
function initMacModal() {
  const modal = document.getElementById("mac-guide-modal");
  const modalCloseBtn = document.getElementById("modal-close-btn");
  const modalConfirmBtn = document.getElementById("modal-confirm-btn");
  const copyCmdBtn = document.getElementById("copy-cmd-btn");
  let pendingDownloadUrl = "";

  function openMacModal(url, event) {
    if (url && url.endsWith(".dmg")) {
      event.preventDefault();
      pendingDownloadUrl = url;
      if (modal) modal.classList.add("active");
    }
  }

  // Intercept main button clicks
  const mainBtn = document.getElementById("download-btn");
  if (mainBtn) {
    mainBtn.addEventListener("click", (e) => {
      const url = mainBtn.getAttribute("href");
      openMacModal(url, e);
    });
  }

  // Intercept alternative links
  const linkMacArm = document.getElementById("link-mac-arm");
  if (linkMacArm) {
    linkMacArm.addEventListener("click", (e) => {
      const url = linkMacArm.getAttribute("href");
      openMacModal(url, e);
    });
  }

  const linkMacIntel = document.getElementById("link-mac-intel");
  if (linkMacIntel) {
    linkMacIntel.addEventListener("click", (e) => {
      const url = linkMacIntel.getAttribute("href");
      openMacModal(url, e);
    });
  }

  // Modal actions
  if (modalCloseBtn) {
    modalCloseBtn.addEventListener("click", () => {
      if (modal) modal.classList.remove("active");
    });
  }

  if (modalConfirmBtn) {
    modalConfirmBtn.addEventListener("click", () => {
      if (modal) modal.classList.remove("active");
      if (pendingDownloadUrl) {
        window.location.href = pendingDownloadUrl;
      }
    });
  }

  // Modal Tab switching
  const modalTabs = document.querySelectorAll(".modal-tab-btn");
  const modalTabContents = document.querySelectorAll(".modal-tab-content");

  modalTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      modalTabs.forEach(t => t.classList.remove("active"));
      modalTabContents.forEach(c => c.classList.remove("active"));

      tab.classList.add("active");
      const targetId = tab.getAttribute("data-modal-tab");
      const activeContent = document.getElementById(targetId);
      if (activeContent) {
        activeContent.classList.add("active");
      }
    });
  });

  // Copy command button
  if (copyCmdBtn) {
    copyCmdBtn.addEventListener("click", () => {
      const cmdText = document.getElementById("cmd-text").textContent;
      navigator.clipboard.writeText(cmdText).then(() => {
        copyCmdBtn.textContent = "복사 완료!";
        setTimeout(() => {
          copyCmdBtn.textContent = "복사하기";
        }, 2000);
      });
    });
  }
}
