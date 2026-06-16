import { Metric } from "../../components/Metric";
import { Panel } from "../../components/Panel";
import { StatusPill } from "../../components/StatusPill";
import type { CameraRuntimeState } from "../../lib/controlCenterTypes";

type Props = {
  camera: CameraRuntimeState;
};

const statusLabel = {
  idle: "대기",
  requesting: "권한 요청 중",
  streaming: "실행 중",
  error: "오류",
};

export function CameraStatusPanel({ camera }: Props) {
  const tone = camera.status === "streaming" ? "green" : camera.status === "error" ? "orange" : "neutral";

  return (
    <Panel title="카메라 상태" eyebrow="입력" action={<StatusPill label={statusLabel[camera.status]} tone={tone} />}>
      <div className="metric-grid metric-grid--two">
        <Metric label="장치" value={camera.device} tone={camera.status === "streaming" ? "blue" : "neutral"} />
        <Metric label="해상도" value={camera.resolution} />
        <Metric label="프레임" value={camera.frameRate ? `${camera.frameRate} fps` : "-"} />
        <Metric label="상태" value={camera.error ?? statusLabel[camera.status]} tone={tone} />
      </div>
    </Panel>
  );
}
