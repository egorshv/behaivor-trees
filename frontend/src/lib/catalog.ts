import type { NodeType } from "../types";

export interface NodeCatalogItem {
  type: NodeType;
  label: string;
  description: string;
  maxChildren: number | null;
}

export const NODE_CATALOG: NodeCatalogItem[] = [
  { type: "sequence", label: "Sequence", description: "Run children in order.", maxChildren: null },
  { type: "selector", label: "Selector", description: "Pick the first succeeding branch.", maxChildren: null },
  { type: "parallel", label: "Parallel", description: "Tick children together.", maxChildren: null },
  { type: "inverter", label: "Inverter", description: "Flip success and failure.", maxChildren: 1 },
  { type: "decorator", label: "Decorator", description: "Remap child statuses.", maxChildren: 1 },
  { type: "action", label: "Action", description: "Stub action leaf.", maxChildren: 0 },
  { type: "condition", label: "Condition", description: "Stub condition leaf.", maxChildren: 0 },
  { type: "success", label: "Success", description: "Always succeed.", maxChildren: 0 },
  { type: "failure", label: "Failure", description: "Always fail.", maxChildren: 0 },
  { type: "running", label: "Running", description: "Stay running forever.", maxChildren: 0 },
];

export function getNodeCatalogItem(nodeType: NodeType): NodeCatalogItem {
  return NODE_CATALOG.find((item) => item.type === nodeType) ?? NODE_CATALOG[0];
}

export function supportsChildren(nodeType: NodeType): boolean {
  return getNodeCatalogItem(nodeType).maxChildren !== 0;
}

export function defaultNodeConfig(nodeType: NodeType): Record<string, unknown> {
  if (nodeType === "sequence") {
    return { memory: true };
  }
  if (nodeType === "selector") {
    return { memory: false };
  }
  if (nodeType === "parallel") {
    return { policy: "success_on_all", synchronise: false };
  }
  if (nodeType === "decorator") {
    return { success_to: "SUCCESS", failure_to: "FAILURE", running_to: "RUNNING" };
  }
  if (nodeType === "action" || nodeType === "condition") {
    return { result: "SUCCESS", delay_ticks: 0 };
  }
  return {};
}

