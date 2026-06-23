import type { WorkflowStage } from "../appTypes";

interface StageRailProps {
  stages: WorkflowStage[];
}

export function StageRail({ stages }: StageRailProps) {
  return (
    <ol className="stage-rail" aria-label="SchemaFlow pipeline">
      {stages.map((stage, index) => (
        <li className={`stage-rail__item stage-rail__item--${stage.state}`} key={stage.label}>
          <span className="stage-rail__index">{index + 1}</span>
          <span className="stage-rail__copy">
            <strong>{stage.label}</strong>
            <small>{stage.detail}</small>
          </span>
        </li>
      ))}
    </ol>
  );
}
