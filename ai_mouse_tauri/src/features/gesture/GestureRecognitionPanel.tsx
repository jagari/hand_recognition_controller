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
      {vision.error ? <p className="panel-error">{vision.error}</p> : null}
    </Panel>
  );
}
