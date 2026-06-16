import { Metric } from "../../components/Metric";
import { Panel } from "../../components/Panel";
import { StatusPill } from "../../components/StatusPill";
import type { CameraRuntimeState, MouseRuntimeState, VisionRuntimeState } from "../../lib/controlCenterTypes";

type Props = {
  cameraStatus: CameraRuntimeState["status"];
  visionStatus: VisionRuntimeState["status"];
  mouse: MouseRuntimeState;
};

export function SystemHealthPanel({ cameraStatus, visionStatus, mouse }: Props) {
  const ready = cameraStatus === "streaming" && visionStatus === "detecting" && mouse.bridge === "ready";

  return (
    <Panel title="시스템 상태" eyebrow="런타임" action={<StatusPill label={ready ? "동작 중" : "준비 중"} tone={ready ? "green" : "blue"} />}>
      <div className="metric-grid metric-grid--two">
        <Metric label="카메라" value={cameraStatus} />
        <Metric label="MediaPipe" value={visionStatus} tone={visionStatus === "detecting" ? "green" : "blue"} />
        <Metric label="Tauri IPC" value={mouse.bridge} tone={mouse.bridge === "ready" ? "green" : "orange"} />
        <Metric label="마우스" value={mouse.enabled ? "켜짐" : "꺼짐"} />
      </div>
    </Panel>
  );
}
