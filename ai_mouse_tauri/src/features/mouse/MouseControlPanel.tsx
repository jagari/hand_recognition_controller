import { Metric } from "../../components/Metric";
import { Panel } from "../../components/Panel";
import { StatusPill } from "../../components/StatusPill";
import type { MouseRuntimeState } from "../../lib/controlCenterTypes";

type Props = {
  mouse: MouseRuntimeState;
  onToggle: () => void;
};

export function MouseControlPanel({ mouse, onToggle }: Props) {
  const bridgeReady = mouse.bridge === "ready";

  return (
    <Panel
      title="마우스 제어"
      eyebrow="출력"
      action={<StatusPill label={mouse.enabled ? "활성" : "비활성"} tone={mouse.enabled ? "green" : "neutral"} />}
    >
      <div className="metric-grid metric-grid--two">
        <Metric label="IPC 브리지" value={bridgeReady ? "연결됨" : mouse.bridge === "checking" ? "확인 중" : "연결 실패"} tone={bridgeReady ? "green" : "orange"} />
        <Metric label="화면" value={mouse.screen ? `${mouse.screen.width} x ${mouse.screen.height}` : "-"} />
        <Metric label="커서 목표" value={mouse.position ? `${mouse.position.x}, ${mouse.position.y}` : "-"} tone="blue" />
        <Metric label="마지막 동작" value={mouse.lastAction} />
      </div>
      <button className="panel-button" onClick={onToggle} disabled={!bridgeReady}>
        {mouse.enabled ? "마우스 제어 끄기" : "마우스 제어 켜기"}
      </button>
      {mouse.error ? <p className="panel-error">{mouse.error}</p> : null}
    </Panel>
  );
}
