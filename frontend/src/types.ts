export type NodeType =
  | "sequence"
  | "selector"
  | "parallel"
  | "inverter"
  | "decorator"
  | "action"
  | "condition"
  | "success"
  | "failure"
  | "running";

export type ExecutionStatus = "idle" | "running" | "success" | "failure" | "invalid";

export interface Position {
  x: number;
  y: number;
}

export interface EdgeDTO {
  id: string;
  source: string;
  target: string;
}

export interface NodeDTO {
  id: string;
  type: NodeType;
  label: string;
  parent_id: string | null;
  position: Position;
  config: Record<string, unknown>;
  order_index: number;
}

export interface ValidationIssue {
  node_id?: string | null;
  message: string;
}

export interface TreeSummary {
  id: string;
  name: string;
  description: string;
  root_node_id: string | null;
  is_valid: boolean;
  validation_errors: ValidationIssue[];
  created_at: string;
  updated_at: string;
  node_count: number;
}

export interface TreeDocument extends TreeSummary {
  nodes: NodeDTO[];
  edges: EdgeDTO[];
}

export interface TreeDraft {
  id?: string;
  name: string;
  description: string;
  root_node_id: string | null;
  is_valid: boolean;
  validation_errors: ValidationIssue[];
  created_at?: string;
  updated_at?: string;
  node_count: number;
  nodes: NodeDTO[];
  edges: EdgeDTO[];
}

export interface TreeUpsertRequest {
  name: string;
  description: string;
  root_node_id: string | null;
  nodes: NodeDTO[];
  edges: EdgeDTO[];
}

export interface NodeExecutionState {
  status: ExecutionStatus;
  feedback: string;
}

export interface SessionSnapshot {
  root_status: ExecutionStatus;
  root_node_id: string | null;
  active_node_ids: string[];
}

export interface ExecutionSession {
  id: string;
  tree_id: string;
  status: ExecutionStatus;
  tick_count: number;
  last_tick_at: string | null;
  node_statuses: Record<string, NodeExecutionState>;
  snapshot: SessionSnapshot;
  created_at: string;
  updated_at: string;
}

export interface SessionStateResponse {
  session: ExecutionSession;
  tree: TreeDocument;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationIssue[];
  root_node_id: string | null;
}

