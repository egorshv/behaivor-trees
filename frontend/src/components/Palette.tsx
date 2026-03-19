import type { DragEvent } from "react";

import { NODE_CATALOG } from "../lib/catalog";

interface PaletteProps {
  onQuickAdd: (nodeType: (typeof NODE_CATALOG)[number]["type"]) => void;
}

export function Palette({ onQuickAdd }: PaletteProps) {
  function onDragStart(event: DragEvent<HTMLButtonElement>, nodeType: string) {
    event.dataTransfer.setData("application/x-bt-node", nodeType);
    event.dataTransfer.effectAllowed = "move";
  }

  return (
    <section className="panel">
      <div className="panel__header">
        <h3>Node Palette</h3>
        <span>Drag into the canvas</span>
      </div>
      <div className="palette">
        {NODE_CATALOG.map((item) => (
          <button
            key={item.type}
            className="palette__item"
            draggable
            onDragStart={(event) => onDragStart(event, item.type)}
            onClick={() => onQuickAdd(item.type)}
            type="button"
          >
            <strong>{item.label}</strong>
            <span>{item.description}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

