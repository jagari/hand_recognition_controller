import { Panel } from "../../components/Panel";
import { StatusPill } from "../../components/StatusPill";
import type { MouseRuntimeState } from "../../lib/controlCenterTypes";

type Props = {
  mouse: MouseRuntimeState;
};

export function SettingsPanel({ mouse }: Props) {
  return (
    <Panel title="설정" eyebrow="앱">
      <div className="settings-list">
        <div className="settings-list__item">
          <span>실행 환경</span>
          <strong>Tauri 데스크톱 앱</strong>
        </div>
        <div className="settings-list__item">
          <span>손 인식</span>
          <strong>MediaPipe WASM</strong>
        </div>
        <div className="settings-list__item">
          <span>네이티브 브리지</span>
          <StatusPill label={mouse.bridge === "ready" ? "연결됨" : "연결 실패"} tone={mouse.bridge === "ready" ? "green" : "orange"} />
        </div>
      </div>
    </Panel>
  );
}
