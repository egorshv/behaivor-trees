import type { NodeProps } from "reactflow";
import { Handle, Position } from "reactflow";

type FlowNodeData = {
  label: string;
  nodeType: string;
  status: string;
};

export function FlowNode({ data }: NodeProps<FlowNodeData>) {
  return (
    <div className={`flow-node flow-node--${data.status}`}>
      <Handle type="target" position={Position.Top} />
      <div className="flow-node__type">{data.nodeType}</div>
      <div className="flow-node__label">{data.label}</div>
      <div className="flow-node__status">{data.status}</div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

