// OS Detection & Button Update
document.addEventListener("DOMContentLoaded", () => {
  detectOSAndUpdateButton();
  initHandSimulator();
});

function detectOSAndUpdateButton() {
  const userAgent = window.navigator.userAgent.toLowerCase();
  const btn = document.getElementById("download-btn");
  const iconSpan = document.getElementById("btn-icon");
  const titleSpan = document.getElementById("btn-title");
  const subtitleSpan = document.getElementById("btn-subtitle");
  
  const winLink = "https://github.com/jagari/hand_recognition_controller/releases/download/v0.1.0/ai_mouse_tauri_0.1.0_x64-setup.exe";
  const macLink = "https://github.com/jagari/hand_recognition_controller/releases/download/v0.1.0/ai_mouse_tauri_0.1.0_x64.dmg";
  
  // Set default links on the small alternative text links
  document.getElementById("link-win").href = winLink;
  document.getElementById("link-mac").href = macLink;

  if (userAgent.indexOf("mac") !== -1) {
    btn.href = macLink;
    iconSpan.textContent = "🍏";
    titleSpan.textContent = "macOS용 다운로드 (.dmg)";
    subtitleSpan.textContent = "Intel & Apple Silicon 범용 가속 빌드 v0.1.0";
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
}

// 🖐️ Interactive 3D Hand Simulator
function initHandSimulator() {
  const canvas = document.getElementById("hand-canvas");
  const ctx = canvas.getContext("2d");
  const container = canvas.parentElement;
  const ripple = document.getElementById("click-ripple");
  const hud = document.getElementById("hud-status");

  let width = (canvas.width = container.clientWidth);
  let height = (canvas.height = container.clientHeight);

  window.addEventListener("resize", () => {
    width = canvas.width = container.clientWidth;
    height = canvas.height = container.clientHeight;
  });

  // Target mouse coordinates
  let mouse = { x: width / 2, y: height / 2 };
  let currentTarget = { x: width / 2, y: height / 2 };
  let isMouseDown = false;

  // Track cursor coordinates
  container.addEventListener("mousemove", (e) => {
    const rect = container.getBoundingClientRect();
    mouse.x = e.clientX - rect.left;
    mouse.y = e.clientY - rect.top;
  });

  container.addEventListener("mousedown", (e) => {
    isMouseDown = true;
    hud.textContent = "STATE: L-PINCH (LEFT CLICK)";
    hud.style.color = "#10B981";
    hud.style.background = "rgba(16, 185, 129, 0.15)";
    hud.style.borderColor = "rgba(16, 185, 129, 0.4)";

    // Trigger ripple
    const rect = container.getBoundingClientRect();
    const rippleX = e.clientX - rect.left;
    const rippleY = e.clientY - rect.top;
    
    ripple.style.left = `${rippleX}px`;
    ripple.style.top = `${rippleY}px`;
    ripple.classList.remove("animate");
    void ripple.offsetWidth; // Trigger reflow to restart animation
    ripple.classList.add("animate");
  });

  container.addEventListener("mouseup", () => {
    isMouseDown = false;
    hud.textContent = "STATE: ACTIVE (TRACKING)";
    hud.style.color = "#38bdf8";
    hud.style.background = "rgba(56, 189, 248, 0.1)";
    hud.style.borderColor = "rgba(56, 189, 248, 0.3)";
  });

  // Render loop
  function draw() {
    ctx.clearRect(0, 0, width, height);

    // Lerp tracking target for natural fluid motion (OneEuroFilter mock-up)
    currentTarget.x += (mouse.x - currentTarget.x) * 0.15;
    currentTarget.y += (mouse.y - currentTarget.y) * 0.15;

    // Draw coordinate grids
    drawGrid();

    // 🖐️ Compute joint coordinates dynamically relative to target cursor position
    const hand = computeHandSkeleton(currentTarget.x, currentTarget.y, isMouseDown);

    // Draw hand skeleton lines
    drawSkeleton(hand);

    // Draw joint highlights
    drawJoints(hand);

    // Draw Predictive Kinematics preview (looks ahead of target)
    drawPredictiveKinematics(currentTarget.x, currentTarget.y);

    requestAnimationFrame(draw);
  }

  // Draw technological background grid
  function drawGrid() {
    ctx.strokeStyle = "rgba(255, 255, 255, 0.02)";
    ctx.lineWidth = 1;
    const gridSize = 40;
    
    for (let x = 0; x < width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  }

  function computeHandSkeleton(tx, ty, clicked) {
    // Wrist base position (drifts slightly horizontally to mimic arm lag)
    const wrist = { x: width * 0.5, y: height - 10 };
    wrist.x += (tx - wrist.x) * 0.35;

    // Angle and distance to target cursor
    const dx = tx - wrist.x;
    const dy = ty - wrist.y;
    const angle = Math.atan2(dy, dx);
    const dist = Math.hypot(dx, dy);

    // Dynamic scale of hand based on distance from wrist (clamps to human proportions)
    const maxHandLen = Math.min(200, Math.max(110, dist * 0.8));
    const palmLen = maxHandLen * 0.45;
    const fingerLen = maxHandLen * 0.55;

    // Knuckles (MCP joints) positioned radially along the wrist-to-target angle
    const indexMcp = { 
      x: wrist.x + Math.cos(angle - 0.12) * palmLen, 
      y: wrist.y + Math.sin(angle - 0.12) * palmLen 
    };
    const middleMcp = { 
      x: wrist.x + Math.cos(angle - 0.02) * (palmLen * 1.05), 
      y: wrist.y + Math.sin(angle - 0.02) * (palmLen * 1.05) 
    };
    const ringMcp = { 
      x: wrist.x + Math.cos(angle + 0.08) * palmLen, 
      y: wrist.y + Math.sin(angle + 0.08) * palmLen 
    };
    const pinkyMcp = { 
      x: wrist.x + Math.cos(angle + 0.18) * (palmLen * 0.95), 
      y: wrist.y + Math.sin(angle + 0.18) * (palmLen * 0.95) 
    };

    // 1. Index Finger (reaching towards the cursor)
    const idx_dx = tx - indexMcp.x;
    const idx_dy = ty - indexMcp.y;
    const idx_dist = Math.hypot(idx_dx, idx_dy);
    const idx_ang = Math.atan2(idx_dy, idx_dx);
    const idx_ext = Math.min(fingerLen, idx_dist);

    const indexTip = { 
      x: indexMcp.x + Math.cos(idx_ang) * idx_ext, 
      y: indexMcp.y + Math.sin(idx_ang) * idx_ext 
    };
    const indexPip = { 
      x: indexMcp.x + (indexTip.x - indexMcp.x) * 0.38, 
      y: indexMcp.y + (indexTip.y - indexMcp.y) * 0.38 
    };
    const indexDip = { 
      x: indexMcp.x + (indexTip.x - indexMcp.x) * 0.72, 
      y: indexMcp.y + (indexTip.y - indexMcp.y) * 0.72 
    };

    // 2. Other fingers (Middle, Ring, Pinky) - fold into palm if clicked
    let middleTip, ringTip, pinkyTip;
    const curlFactor = clicked ? 0.38 : 1.0;
    const curlAngleOffset = clicked ? 0.35 : 0.0;

    middleTip = {
      x: middleMcp.x + Math.cos(angle - 0.02 + curlAngleOffset) * (fingerLen * 1.06 * curlFactor),
      y: middleMcp.y + Math.sin(angle - 0.02 + curlAngleOffset) * (fingerLen * 1.06 * curlFactor)
    };
    ringTip = {
      x: ringMcp.x + Math.cos(angle + 0.08 + curlAngleOffset * 1.2) * (fingerLen * 0.96 * curlFactor),
      y: ringMcp.y + Math.sin(angle + 0.08 + curlAngleOffset * 1.2) * (fingerLen * 0.96 * curlFactor)
    };
    pinkyTip = {
      x: pinkyMcp.x + Math.cos(angle + 0.18 + curlAngleOffset * 1.5) * (fingerLen * 0.76 * curlFactor),
      y: pinkyMcp.y + Math.sin(angle + 0.18 + curlAngleOffset * 1.5) * (fingerLen * 0.76 * curlFactor)
    };

    // Interpolate joints for middle, ring, pinky
    const middlePip = { x: middleMcp.x + (middleTip.x - middleMcp.x) * 0.38, y: middleMcp.y + (middleTip.y - middleMcp.y) * 0.38 };
    const middleDip = { x: middleMcp.x + (middleTip.x - middleMcp.x) * 0.72, y: middleMcp.y + (middleTip.y - middleMcp.y) * 0.72 };
    
    const ringPip = { x: ringMcp.x + (ringTip.x - ringMcp.x) * 0.38, y: ringMcp.y + (ringTip.y - ringMcp.y) * 0.38 };
    const ringDip = { x: ringMcp.x + (ringTip.x - ringMcp.x) * 0.72, y: ringMcp.y + (ringTip.y - ringMcp.y) * 0.72 };

    const pinkyPip = { x: pinkyMcp.x + (pinkyTip.x - pinkyMcp.x) * 0.38, y: pinkyMcp.y + (pinkyTip.y - pinkyMcp.y) * 0.38 };
    const pinkyDip = { x: pinkyMcp.x + (pinkyTip.x - pinkyMcp.x) * 0.72, y: pinkyMcp.y + (pinkyTip.y - pinkyMcp.y) * 0.72 };

    // 3. Thumb
    const thumbMcp = { 
      x: wrist.x + Math.cos(angle - 0.48) * (palmLen * 0.55), 
      y: wrist.y + Math.sin(angle - 0.48) * (palmLen * 0.55) 
    };
    
    let thumbTip, thumbPip;
    if (clicked) {
      // Pinch state: Thumb tip meets the index tip
      thumbTip = { x: indexTip.x - 3, y: indexTip.y + 4 };
      thumbPip = { 
        x: (thumbMcp.x + thumbTip.x) * 0.5 - Math.cos(angle) * (maxHandLen * 0.12), 
        y: (thumbMcp.y + thumbTip.y) * 0.5 - Math.sin(angle) * (maxHandLen * 0.12) 
      };
    } else {
      // Idle state: Thumb spreads naturally to the left
      thumbPip = { 
        x: thumbMcp.x + Math.cos(angle - 0.48) * (palmLen * 0.42), 
        y: thumbMcp.y + Math.sin(angle - 0.48) * (palmLen * 0.42) 
      };
      thumbTip = { 
        x: thumbPip.x + Math.cos(angle - 0.75) * (fingerLen * 0.45), 
        y: thumbPip.y + Math.sin(angle - 0.75) * (fingerLen * 0.45) 
      };
    }

    return {
      wrist,
      thumb: [wrist, thumbMcp, thumbPip, thumbTip],
      index: [wrist, indexMcp, indexPip, indexTip],
      middle: [wrist, middleMcp, middlePip, middleTip],
      ring: [wrist, ringMcp, ringPip, ringTip],
      pinky: [wrist, pinkyMcp, pinkyPip, pinkyTip],
      palmBase: [indexMcp, middleMcp, ringMcp, pinkyMcp, wrist, indexMcp]
    };
  }

  function drawSkeleton(hand) {
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.shadowBlur = 8;
    ctx.shadowColor = "rgba(139, 92, 246, 0.4)";
    ctx.strokeStyle = "rgba(255, 255, 255, 0.45)";

    const fingers = [hand.thumb, hand.index, hand.middle, hand.ring, hand.pinky, hand.palmBase];
    fingers.forEach(finger => {
      ctx.beginPath();
      ctx.moveTo(finger[0].x, finger[0].y);
      for (let i = 1; i < finger.length; i++) {
        ctx.lineTo(finger[i].x, finger[i].y);
      }
      ctx.stroke();
    });
    ctx.shadowBlur = 0;
  }

  function drawJoints(hand) {
    const allJoints = [
      ...hand.thumb, ...hand.index, ...hand.middle, ...hand.ring, ...hand.pinky
    ];

    allJoints.forEach((joint) => {
      ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
      ctx.beginPath();
      ctx.arc(joint.x, joint.y, 3.5, 0, 2 * Math.PI);
      ctx.fill();
    });

    // Highlight critical tip nodes
    const highlights = [
      { pt: hand.index[3], color: "#38bdf8" }, // Index (blue)
      { pt: hand.thumb[3], color: "#34d399" }, // Thumb (green)
      { pt: hand.middle[3], color: "#fb7185" }, // Middle (rose)
      { pt: hand.wrist, color: "#a78bfa" }      // Wrist (purple)
    ];

    highlights.forEach(({ pt, color }) => {
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 5, 0, 2 * Math.PI);
      ctx.fill();

      // Outer rings
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 10, 0, 2 * Math.PI);
      ctx.stroke();
    });
  }

  // Draw Predictive Kinematics ghost cursor looking ahead
  function drawPredictiveKinematics(tx, ty) {
    // Simulate a predictive offset (lookahead) based on current target velocity
    const dx = mouse.x - tx;
    const dy = mouse.y - ty;
    const px = tx + dx * 1.5;
    const py = ty + dy * 1.5;

    ctx.strokeStyle = "rgba(14, 165, 233, 0.3)";
    ctx.setLineDash([4, 4]);
    ctx.lineWidth = 1.5;
    
    // Draw line from index tip to predictive point
    ctx.beginPath();
    ctx.moveTo(tx, ty);
    ctx.lineTo(px, py);
    ctx.stroke();
    
    // Draw predictive circle
    ctx.beginPath();
    ctx.arc(px, py, 6, 0, 2 * Math.PI);
    ctx.stroke();
    
    ctx.fillStyle = "rgba(14, 165, 233, 0.5)";
    ctx.font = "9px Outfit";
    ctx.fillText("PREDICTION (45ms)", px + 12, py + 3);
    ctx.setLineDash([]);
  }

  draw();
}
