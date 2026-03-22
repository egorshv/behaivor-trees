import type { NodeProps } from "reactflow";
import { Handle, Position } from "reactflow";

type FlowNodeData = {
  label: string;
  nodeType: string;
  status: string;
  canHaveChildren: boolean;
  isActive: boolean;
  onActivate?: () => void;
  onOpenMenu?: (element: HTMLDivElement) => void;
};

export function FlowNode({ data }: NodeProps<FlowNodeData>) {
  function activateAndOpenMenu(element: HTMLDivElement) {
    data.onActivate?.();
    data.onOpenMenu?.(element);
  }

  return (
    <div
      className={`flow-node flow-node--${data.status} ${data.isActive ? "flow-node--active" : ""}`}
      onClick={(event) => {
        event.preventDefault();
        activateAndOpenMenu(event.currentTarget);
      }}
      onPointerDownCapture={(event) => {
        activateAndOpenMenu(event.currentTarget);
      }}
      onContextMenuCapture={(event) => {
        event.preventDefault();
        event.stopPropagation();
        activateAndOpenMenu(event.currentTarget);
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div className="flow-node__header flow-node__drag-handle">
        <div className="flow-node__type">{data.nodeType}</div>
        <div className="flow-node__label">{data.label}</div>
      </div>
      <div className="flow-node__status">{data.status}</div>
      {data.canHaveChildren ? <Handle type="source" position={Position.Bottom} /> : null}
    </div>
  );
}
