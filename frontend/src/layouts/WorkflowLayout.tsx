import type { ReactNode } from "react";

export type WorkflowStep = {
  index: number;
  label: string;
  available: boolean;
};

export type WorkflowContext = {
  input: string;
  schemaPack: string;
  configuration: string;
};

type WorkflowLayoutProps = {
  children: ReactNode;
  currentStep: number;
  steps: WorkflowStep[];
  context: WorkflowContext;
  onStepChange: (step: number) => void;
};

export function WorkflowLayout({
  children,
  currentStep,
  steps,
  context,
  onStepChange
}: WorkflowLayoutProps) {
  return (
    <section className="conversion-workflow" aria-label="转换工作流">
      <nav className="conversion-stepper" aria-label="转换步骤">
        <ol>
          {steps.map((step) => {
            const active = currentStep === step.index;
            return (
              <li key={step.index} className={active ? "conversion-step conversion-step-active" : "conversion-step"}>
                <button
                  type="button"
                  aria-current={active ? "step" : undefined}
                  aria-disabled={!step.available}
                  disabled={!step.available}
                  onClick={() => onStepChange(step.index)}
                >
                  <span aria-hidden="true">{step.index}</span>
                  {step.label}
                </button>
              </li>
            );
          })}
        </ol>
      </nav>

      <div className="conversion-workflow-content">{children}</div>

      <aside
        className="conversion-context-summary"
        aria-label="转换上下文摘要"
      >
        <h2>当前上下文</h2>
        <dl>
          <div>
            <dt>输入</dt>
            <dd>{context.input}</dd>
          </div>
          <div>
            <dt>SchemaPack</dt>
            <dd>{context.schemaPack}</dd>
          </div>
          <div>
            <dt>转换配置</dt>
            <dd>{context.configuration}</dd>
          </div>
        </dl>
        <p>浏览器本地恢复（browser-local）</p>
      </aside>
    </section>
  );
}
