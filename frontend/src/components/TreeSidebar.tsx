import type { ChangeEvent } from "react";

import type { TreeDraft, TreeSummary } from "../types";

interface TreeSidebarProps {
  tree: TreeDraft;
  trees: TreeSummary[];
  busy: boolean;
  onCreate: () => void;
  onReload: () => void;
  onSelect: (treeId: string) => void;
  onSave: () => void;
  onDelete: () => void;
  onTreeChange: (updater: (tree: TreeDraft) => TreeDraft) => void;
}

export function TreeSidebar({
  tree,
  trees,
  busy,
  onCreate,
  onReload,
  onSelect,
  onSave,
  onDelete,
  onTreeChange,
}: TreeSidebarProps) {
  function updateText<K extends "name" | "description">(key: K, event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    const value = event.target.value;
    onTreeChange((current) => ({ ...current, [key]: value }));
  }

  return (
    <aside className="sidebar">
      <section className="panel panel--hero">
        <div className="panel__header">
          <h2>Behavior Trees</h2>
          <span>FastAPI + py_trees</span>
        </div>
        <label className="field">
          <span>Name</span>
          <input value={tree.name} onChange={(event) => updateText("name", event)} />
        </label>
        <label className="field">
          <span>Description</span>
          <textarea rows={3} value={tree.description} onChange={(event) => updateText("description", event)} />
        </label>
        <div className="button-row">
          <button disabled={busy} onClick={onSave} type="button">
            Save
          </button>
          <button disabled={busy} onClick={onCreate} type="button">
            New
          </button>
          <button disabled={busy || !tree.id} onClick={onDelete} type="button">
            Delete
          </button>
        </div>
      </section>

      <section className="panel">
        <div className="panel__header">
          <h3>Stored Trees</h3>
          <button className="ghost-button" onClick={onReload} type="button">
            Refresh
          </button>
        </div>
        <div className="tree-list">
          {trees.map((item) => (
            <button
              className={`tree-list__item ${tree.id === item.id ? "tree-list__item--active" : ""}`}
              key={item.id}
              onClick={() => onSelect(item.id)}
              type="button"
            >
              <strong>{item.name}</strong>
              <span>
                {item.node_count} nodes · {item.is_valid ? "valid" : "draft"}
              </span>
            </button>
          ))}
          {trees.length === 0 && <p className="empty-state">No saved trees yet.</p>}
        </div>
      </section>
    </aside>
  );
}

