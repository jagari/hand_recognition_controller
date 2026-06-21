import { Metric } from "../../components/Metric";
import { Panel } from "../../components/Panel";
import { StatusPill } from "../../components/StatusPill";
import type { VisionRuntimeState } from "../../lib/controlCenterTypes";

type Props = {
  vision: VisionRuntimeState;
};

const statusLabel = {
  idle: "대기",
  loading: "모델 로딩",
  ready: "준비됨",
  detecting: "인식 중",
  error: "오류",
};

export function GestureRecognitionPanel({ vision }: Props) {
  const tone = vision.status === "detecting" ? "green" : vision.status === "error" ? "orange" : "blue";

  return (
    <Panel title="제스처 인식" eyebrow="비전" action={<StatusPill label={statusLabel[vision.status]} tone={tone} />}>
      <div className="metric-grid metric-grid--two">
        <Metric label="현재 제스처" value={vision.gesture} tone={vision.status === "detecting" ? "green" : "neutral"} />
        <Metric label="랜드마크" value={vision.landmarks ? `${vision.landmarks}개` : "-"} />
        <Metric label="신뢰도" value={vision.confidence ? `${Math.round(vision.confidence * 100)}%` : "-"} tone="blue" />
        <Metric label="핀치 거리" value={vision.pinchDistance ? vision.pinchDistance.toFixed(3) : "-"} />
      </div>
      <div className="gesture-guide" style={{ marginTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '12px' }}>
        <h5 style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '8px', fontWeight: 600 }}>제스처 조작 가이드</h5>
        <ul style={{ fontSize: '11px', color: '#cbd5e1', paddingLeft: '16px', margin: 0, lineHeight: '1.6', listStyleType: 'none' }}>
          <li>🖐️ <strong>이동</strong>: 손바닥을 펴고 움직임</li>
          <li>👌 <strong>좌클릭</strong>: 엄지와 검지를 맞잡음</li>
          <li>✊ <strong>스크롤</strong>: 주먹을 쥐고 위아래로 움직임</li>
        </ul>
      </div>
      {vision.error ? <p className="panel-error">{vision.error}</p> : null}
    </Panel>
  );
}
