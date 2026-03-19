import type { EdgeDTO, NodeDTO, NodeType, Position, TreeDraft, TreeUpsertRequest } from "../types";
import { defaultNodeConfig } from "./catalog";

function createId(prefix: string): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

export function buildEdges(nodes: NodeDTO[]): EdgeDTO[] {
  return nodes
    .filter((node) => node.parent_id)
    .sort((left, right) => left.order_index - right.order_index)
    .map((node) => ({
      id: `${node.parent_id}-${node.id}`,
      source: node.parent_id as string,
      target: node.id,
    }));
}

export function deriveRootNodeId(nodes: NodeDTO[]): string | null {
  const roots = nodes.filter((node) => node.parent_id === null);
  return roots.length === 1 ? roots[0].id : null;
}

export function normalizeTree(tree: TreeDraft): TreeDraft {
  const nextNodes = tree.nodes.map((node) => ({ ...node }));
  const childrenByParent = new Map<string | null, NodeDTO[]>();

  for (const node of nextNodes) {
    const siblings = childrenByParent.get(node.parent_id) ?? [];
    siblings.push(node);
    childrenByParent.set(node.parent_id, siblings);
  }

  for (const siblings of childrenByParent.values()) {
    siblings
      .sort((left, right) => left.order_index - right.order_index)
      .forEach((node, index) => {
        node.order_index = index;
      });
  }

  return {
    ...tree,
    nodes: nextNodes,
    edges: buildEdges(nextNodes),
    node_count: nextNodes.length,
    root_node_id: deriveRootNodeId(nextNodes),
  };
}

export function createEmptyTree(name = "Untitled Tree"): TreeDraft {
  return {
    name,
    description: "",
    root_node_id: null,
    is_valid: false,
    validation_errors: [],
    node_count: 0,
    nodes: [],
    edges: [],
  };
}

export function createNode(nodeType: NodeType, position: Position): NodeDTO {
  return {
    id: createId(nodeType),
    type: nodeType,
    label: nodeType[0].toUpperCase() + nodeType.slice(1),
    parent_id: null,
    position,
    config: defaultNodeConfig(nodeType),
    order_index: 0,
  };
}

export function addNode(tree: TreeDraft, nodeType: NodeType, position: Position): TreeDraft {
  return normalizeTree({
    ...tree,
    nodes: [...tree.nodes, createNode(nodeType, position)],
  });
}

export function updateNode(tree: TreeDraft, nodeId: string, updater: (node: NodeDTO) => NodeDTO): TreeDraft {
  return normalizeTree({
    ...tree,
    nodes: tree.nodes.map((node) => (node.id === nodeId ? updater({ ...node }) : node)),
  });
}

export function connectNodes(tree: TreeDraft, sourceId: string, targetId: string): TreeDraft {
  if (sourceId === targetId) {
    return tree;
  }
  const siblings = tree.nodes.filter((node) => node.parent_id === sourceId && node.id !== targetId);
  return normalizeTree({
    ...tree,
    nodes: tree.nodes.map((node) => {
      if (node.id !== targetId) {
        return node;
      }
      return {
        ...node,
        parent_id: sourceId,
        order_index: siblings.length,
      };
    }),
  });
}

export function disconnectNode(tree: TreeDraft, targetId: string): TreeDraft {
  return normalizeTree({
    ...tree,
    nodes: tree.nodes.map((node) =>
      node.id === targetId ? { ...node, parent_id: null, order_index: 0 } : node
    ),
  });
}

export function deleteNodeCascade(tree: TreeDraft, nodeId: string): TreeDraft {
  const toDelete = new Set<string>([nodeId]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const node of tree.nodes) {
      if (node.parent_id && toDelete.has(node.parent_id) && !toDelete.has(node.id)) {
        toDelete.add(node.id);
        changed = true;
      }
    }
  }
  return normalizeTree({
    ...tree,
    nodes: tree.nodes.filter((node) => !toDelete.has(node.id)),
  });
}

export function reorderChild(tree: TreeDraft, parentId: string, childId: string, direction: -1 | 1): TreeDraft {
  const siblings = tree.nodes
    .filter((node) => node.parent_id === parentId)
    .sort((left, right) => left.order_index - right.order_index);
  const currentIndex = siblings.findIndex((node) => node.id === childId);
  const targetIndex = currentIndex + direction;
  if (currentIndex === -1 || targetIndex < 0 || targetIndex >= siblings.length) {
    return tree;
  }
  const reordered = [...siblings];
  const [item] = reordered.splice(currentIndex, 1);
  reordered.splice(targetIndex, 0, item);
  return normalizeTree({
    ...tree,
    nodes: tree.nodes.map((node) => {
      const siblingIndex = reordered.findIndex((candidate) => candidate.id === node.id);
      if (siblingIndex === -1) {
        return node;
      }
      return { ...node, order_index: siblingIndex };
    }),
  });
}

export function preparePayload(tree: TreeDraft): TreeUpsertRequest {
  const normalized = normalizeTree(tree);
  return {
    name: normalized.name,
    description: normalized.description,
    root_node_id: normalized.root_node_id,
    nodes: normalized.nodes,
    edges: normalized.edges,
  };
}

