import type { ChangeEvent } from "react";

import { supportsChildren } from "../lib/catalog";
import type { NodeDTO, TreeDraft } from "../types";

interface InspectorProps {
  node: NodeDTO | null;
  tree: TreeDraft;
  onUpdateNode: (nodeId: string, updater: (node: NodeDTO) => NodeDTO) => void;
  onDeleteNode: (nodeId: string) => void;
  onDisconnectNode: (nodeId: string) => void;
  onReorderChild: (parentId: string, childId: string, direction: -1 | 1) => void;
}

function textValue(event: ChangeEvent<HTMLInputElement | HTMLSelectElement>): string {
  return event.target.value;
}

function numberValue(event: ChangeEvent<HTMLInputElement>): number {
  return Number.parseInt(event.target.value || "0", 10);
}

export function Inspector({
  node,
  tree,
  onUpdateNode,
  onDeleteNode,
  onDisconnectNode,
  onReorderChild,
}: InspectorProps) {
  if (!node) {
    return (
      <section className="panel">
        <div className="panel__header">
          <h3>Inspector</h3>
          <span>Select a node</span>
        </div>
        <p className="empty-state">Use the palette or load the demo tree to begin editing.</p>
      </section>
    );
  }

  const children = tree.nodes
    .filter((candidate) => candidate.parent_id === node.id)
    .sort((left, right) => left.order_index - right.order_index);

  return (
    <section className="panel">
      <div className="panel__header">
        <h3>Inspector</h3>
        <span>{node.type}</span>
      </div>

      <label className="field">
        <span>Label</span>
        <input
          value={node.label}
          onChange={(event) =>
            onUpdateNode(node.id, (current) => ({ ...current, label: textValue(event) }))
          }
        />
      </label>

      {(node.type === "action" || node.type === "condition") && (
        <>
          <label className="field">
            <span>Result</span>
            <select
              value={String(node.config.result ?? "SUCCESS")}
              onChange={(event) =>
                onUpdateNode(node.id, (current) => ({
                  ...current,
                  config: { ...current.config, result: textValue(event) },
                }))
              }
            >
              <option value="SUCCESS">SUCCESS</option>
              <option value="FAILURE">FAILURE</option>
              <option value="RUNNING">RUNNING</option>
            </select>
          </label>
          <label className="field">
            <span>Delay ticks</span>
            <input
              min={0}
              type="number"
              value={String(node.config.delay_ticks ?? 0)}
              onChange={(event) =>
                onUpdateNode(node.id, (current) => ({
                  ...current,
                  config: { ...current.config, delay_ticks: numberValue(event) },
                }))
              }
            />
          </label>
        </>
      )}

      {(node.type === "sequence" || node.type === "selector") && (
        <label className="field field--checkbox">
          <input
            checked={Boolean(node.config.memory)}
            type="checkbox"
            onChange={(event) =>
              onUpdateNode(node.id, (current) => ({
                ...current,
                config: { ...current.config, memory: event.target.checked },
              }))
            }
          />
          <span>Memory</span>
        </label>
      )}

      {node.type === "parallel" && (
        <>
          <label className="field">
            <span>Policy</span>
            <select
              value={String(node.config.policy ?? "success_on_all")}
              onChange={(event) =>
                onUpdateNode(node.id, (current) => ({
                  ...current,
                  config: { ...current.config, policy: textValue(event) },
                }))
              }
            >
              <option value="success_on_all">success_on_all</option>
              <option value="success_on_one">success_on_one</option>
            </select>
          </label>
          <label className="field field--checkbox">
            <input
              checked={Boolean(node.config.synchronise)}
              type="checkbox"
              onChange={(event) =>
                onUpdateNode(node.id, (current) => ({
                  ...current,
                  config: { ...current.config, synchronise: event.target.checked },
                }))
              }
            />
            <span>Synchronise</span>
          </label>
        </>
      )}

      {node.type === "decorator" && (
        <>
          {(["success_to", "failure_to", "running_to"] as const).map((key) => (
            <label className="field" key={key}>
              <span>{key}</span>
              <select
                value={String(node.config[key] ?? key.replace("_to", "").toUpperCase())}
                onChange={(event) =>
                  onUpdateNode(node.id, (current) => ({
                    ...current,
                    config: { ...current.config, [key]: textValue(event) },
                  }))
                }
              >
                <option value="SUCCESS">SUCCESS</option>
                <option value="FAILURE">FAILURE</option>
                <option value="RUNNING">RUNNING</option>
              </select>
            </label>
          ))}
        </>
      )}

      {supportsChildren(node.type) && (
        <div className="children-list">
          <div className="children-list__header">Children</div>
          {children.length === 0 && <p className="empty-state">Connect child nodes by dragging an edge.</p>}
          {children.map((child, index) => (
            <div className="child-row" key={child.id}>
              <span>
                {index + 1}. {child.label}
              </span>
              <div className="child-row__actions">
                <button onClick={() => onDisconnectNode(child.id)} type="button">
                  Unlink
                </button>
                <button
                  disabled={index === 0}
                  onClick={() => onReorderChild(node.id, child.id, -1)}
                  type="button"
                >
                  Up
                </button>
                <button
                  disabled={index === children.length - 1}
                  onClick={() => onReorderChild(node.id, child.id, 1)}
                  type="button"
                >
                  Down
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <button className="danger-button" onClick={() => onDeleteNode(node.id)} type="button">
        Delete subtree
      </button>
    </section>
  );
}
