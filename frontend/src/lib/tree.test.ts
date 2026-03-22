import { describe, expect, it } from "vitest";

import {
  addNode,
  canConnectNodes,
  connectNodes,
  createEmptyTree,
  deleteNodeCascade,
  preparePayload,
  reorderChild,
  updateNode,
} from "./tree";

describe("tree helpers", () => {
  it("creates and connects nodes", () => {
    let tree = createEmptyTree();
    tree = addNode(tree, "sequence", { x: 0, y: 0 });
    tree = addNode(tree, "action", { x: 100, y: 100 });

    const root = tree.nodes.find((node) => node.type === "sequence");
    const child = tree.nodes.find((node) => node.type === "action");

    tree = connectNodes(tree, root!.id, child!.id);

    expect(tree.root_node_id).toBe(root!.id);
    expect(tree.edges).toHaveLength(1);
    expect(tree.nodes.find((node) => node.id === child!.id)?.parent_id).toBe(root!.id);
  });

  it("reorders siblings and prepares payload", () => {
    let tree = createEmptyTree();
    tree = addNode(tree, "sequence", { x: 0, y: 0 });
    tree = addNode(tree, "action", { x: 100, y: 100 });
    tree = addNode(tree, "condition", { x: 200, y: 100 });

    const root = tree.nodes.find((node) => node.type === "sequence")!;
    const action = tree.nodes.find((node) => node.type === "action")!;
    const condition = tree.nodes.find((node) => node.type === "condition")!;

    tree = connectNodes(tree, root.id, action.id);
    tree = connectNodes(tree, root.id, condition.id);
    tree = reorderChild(tree, root.id, condition.id, -1);
    tree = updateNode(tree, root.id, (node) => ({ ...node, label: "Root" }));

    const payload = preparePayload(tree);

    expect(payload.nodes.find((node) => node.id === condition.id)?.order_index).toBe(0);
    expect(payload.nodes.find((node) => node.id === action.id)?.order_index).toBe(1);
    expect(payload.nodes.find((node) => node.id === root.id)?.label).toBe("Root");
  });

  it("deletes a subtree", () => {
    let tree = createEmptyTree();
    tree = addNode(tree, "sequence", { x: 0, y: 0 });
    tree = addNode(tree, "selector", { x: 100, y: 100 });
    tree = addNode(tree, "action", { x: 200, y: 200 });

    const root = tree.nodes.find((node) => node.type === "sequence")!;
    const child = tree.nodes.find((node) => node.type === "selector")!;
    const grandChild = tree.nodes.find((node) => node.type === "action")!;

    tree = connectNodes(tree, root.id, child.id);
    tree = connectNodes(tree, child.id, grandChild.id);
    tree = deleteNodeCascade(tree, child.id);

    expect(tree.nodes).toHaveLength(1);
    expect(tree.nodes[0].id).toBe(root.id);
  });

  it("prevents cycle creation when reconnecting nodes", () => {
    let tree = createEmptyTree();
    tree = addNode(tree, "sequence", { x: 0, y: 0 });
    tree = addNode(tree, "selector", { x: 100, y: 100 });
    tree = addNode(tree, "action", { x: 200, y: 200 });

    const root = tree.nodes.find((node) => node.type === "sequence")!;
    const branch = tree.nodes.find((node) => node.type === "selector")!;
    const leaf = tree.nodes.find((node) => node.type === "action")!;

    tree = connectNodes(tree, root.id, branch.id);
    tree = connectNodes(tree, branch.id, leaf.id);

    expect(canConnectNodes(tree, leaf.id, root.id)).toBe(false);
    expect(canConnectNodes(tree, root.id, leaf.id)).toBe(true);
  });
});
