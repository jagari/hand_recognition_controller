import { Panel } from "../../components/Panel";
import type { ActivityEvent } from "../../lib/controlCenterTypes";

type Props = {
  events: ActivityEvent[];
};

export function ActivityLog({ events }: Props) {
  return (
    <Panel title="활동 로그" eyebrow="디버그" className="panel--wide">
      <ol className="activity-list">
        {events.map((event) => (
          <li key={event.id}>
            <span className={`activity-dot activity-dot--${event.tone}`} />
            <time>{event.time}</time>
            <p>{event.message}</p>
          </li>
        ))}
      </ol>
    </Panel>
  );
}
