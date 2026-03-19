import type { ExecutionSession, TreeDraft } from "../types";

interface RunControlsProps {
  tree: TreeDraft;
  session: ExecutionSession | null;
  busy: boolean;
  onRun: () => void;
  onTick: () => void;
  onReset: () => void;
}

export function RunControls({ tree, session, busy, onRun, onTick, onReset }: RunControlsProps) {
  return (
    <section className="panel">
      <div className="panel__header">
        <h3>Execution</h3>
        <span>{session?.status ?? "idle"}</span>
      </div>

      <div className="stats-grid">
        <div>
          <strong>Tree status</strong>
          <span>{tree.is_valid ? "ready" : "draft / invalid"}</span>
        </div>
        <div>
          <strong>Ticks</strong>
          <span>{session?.tick_count ?? 0}</span>
        </div>
      </div>

      <div className="button-row">
        <button disabled={busy || !tree.id} onClick={onRun} type="button">
          Run
        </button>
        <button disabled={busy || !session} onClick={onTick} type="button">
          Tick
        </button>
        <button disabled={busy || !session} onClick={onReset} type="button">
          Reset
        </button>
      </div>
    </section>
  );
}

