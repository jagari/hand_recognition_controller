import { Metric } from "../../components/Metric";
import { Panel } from "../../components/Panel";
import { StatusPill } from "../../components/StatusPill";
import type { CalibrationRuntimeState } from "../../lib/controlCenterTypes";

type Props = {
  calibration: CalibrationRuntimeState;
  isCameraActive: boolean;
  onStart: () => void;
  onReset: () => void;
};

export function CalibrationPanel({ calibration, isCameraActive, onStart, onReset }: Props) {
  return (
    <Panel
      title="캘리브레이션"
      eyebrow="설정"
      action={<StatusPill label={calibration.active ? "수집 중" : calibration.bounds ? "적용됨" : "미설정"} tone={calibration.bounds ? "green" : "neutral"} />}
    >
      <div className="control-row">
        <span>진행률</span>
        <progress value={calibration.progress} max="100" />
        <strong>{calibration.progress}%</strong>
      </div>
      <div className="metric-grid metric-grid--two">
        <Metric label="샘플" value={`${calibration.samples}개`} />
        <Metric label="범위" value={calibration.bounds ? "수집됨" : "-"} tone={calibration.bounds ? "green" : "neutral"} />
      </div>
      <div className="button-row">
        <button className="panel-button" onClick={onStart} disabled={!isCameraActive}>
          보정 시작
        </button>
        <button className="panel-button panel-button--ghost" onClick={onReset}>
          초기화
        </button>
      </div>
    </Panel>
  );
}
