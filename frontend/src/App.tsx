import { useEffect, useMemo, useState } from "react";
import type { Connection, Edge, Node, NodeChange, EdgeChange, ReactFlowInstance } from "reactflow";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";

import { FlowNode } from "./components/FlowNode";
import { Inspector } from "./components/Inspector";
import { Palette } from "./components/Palette";
import { RunControls } from "./components/RunControls";
import { TreeSidebar } from "./components/TreeSidebar";
import { api } from "./lib/api";
import { supportsChildren } from "./lib/catalog";
import {
  addNode,
  connectNodes,
  createEmptyTree,
  deleteNodeCascade,
  disconnectNode,
  normalizeTree,
  preparePayload,
  reorderChild,
  updateNode,
} from "./lib/tree";
import type { EdgeDTO, ExecutionSession, TreeDraft, TreeSummary } from "./types";
import "./styles/app.css";

const nodeTypes = {
  behavior: FlowNode,
};

function AppShell() {
  const [tree, setTree] = useState<TreeDraft>(() => createEmptyTree());
  const [trees, setTrees] = useState<TreeSummary[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [session, setSession] = useState<ExecutionSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Loading tree catalog...");
  const [instance, setInstance] = useState<ReactFlowInstance | null>(null);

  useEffect(() => {
    void refreshTrees();
  }, []);

  async function refreshTrees() {
    setBusy(true);
    try {
      const items = await api.listTrees();
      setTrees(items);
      if (items.length > 0 && !tree.id) {
        await loadTree(items[0].id);
      } else if (items.length === 0) {
        setTree(createEmptyTree());
        setMessage("Create a tree or load the seeded demo after the backend starts.");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to load trees.");
    } finally {
      setBusy(false);
    }
  }

  async function loadTree(treeId: string) {
    setBusy(true);
    try {
      const document = await api.getTree(treeId);
      setTree(normalizeTree(document));
      setSelectedNodeId(null);
      setSession(null);
      setMessage(`Loaded "${document.name}".`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to load tree.");
    } finally {
      setBusy(false);
    }
  }

  async function saveTree() {
    setBusy(true);
    try {
      const payload = preparePayload(tree);
      const document = tree.id
        ? await api.updateTree(tree.id, payload)
        : await api.createTree(payload);
      setTree(normalizeTree(document));
      setSession(null);
      setMessage(document.is_valid ? "Tree saved." : "Tree saved as draft with validation issues.");
      const items = await api.listTrees();
      setTrees(items);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to save tree.");
    } finally {
      setBusy(false);
    }
  }

  async function deleteCurrentTree() {
    if (!tree.id) {
      setTree(createEmptyTree());
      return;
    }
    setBusy(true);
    try {
      await api.deleteTree(tree.id);
      setTree(createEmptyTree());
      setSession(null);
      setSelectedNodeId(null);
      setMessage("Tree deleted.");
      const items = await api.listTrees();
      setTrees(items);
      if (items[0]) {
        await loadTree(items[0].id);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to delete tree.");
    } finally {
      setBusy(false);
    }
  }

  async function runTree() {
    if (!tree.id) {
      setMessage("Save the tree before starting an execution session.");
      return;
    }
    setBusy(true);
    try {
      const started = await api.runTree(tree.id);
      setSession(started);
      setMessage("Execution session started.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to start execution.");
    } finally {
      setBusy(false);
    }
  }

  async function tickSession() {
    if (!session) {
      return;
    }
    setBusy(true);
    try {
      const next = await api.tickSession(session.id);
      setSession(next);
      setMessage(`Tick ${next.tick_count} completed.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to tick session.");
    } finally {
      setBusy(false);
    }
  }

  async function resetSession() {
    if (!session) {
      return;
    }
    setBusy(true);
    try {
      const reset = await api.resetSession(session.id);
      setSession(reset);
      setMessage("Execution session reset.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to reset session.");
    } finally {
      setBusy(false);
    }
  }

  const flowNodes = useMemo<Node[]>(
    () =>
      tree.nodes.map((node) => ({
        id: node.id,
        type: "behavior",
        position: node.position,
        data: {
          label: node.label,
          nodeType: node.type,
          status: session?.node_statuses[node.id]?.status ?? "idle",
        },
        selected: node.id === selectedNodeId,
      })),
    [selectedNodeId, session, tree.nodes]
  );

  const flowEdges = useMemo<Edge[]>(
    () =>
      tree.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        animated: session?.snapshot.active_node_ids.includes(edge.target) ?? false,
      })),
    [session, tree.edges]
  );

  function changeTree(updater: (current: TreeDraft) => TreeDraft) {
    setTree((current) => normalizeTree(updater(current)));
  }

  function handleQuickAdd(type: Parameters<typeof addNode>[1]) {
    changeTree((current) =>
      addNode(current, type, { x: 160 + current.nodes.length * 32, y: 160 + current.nodes.length * 24 })
    );
    setMessage(`Added ${type} node.`);
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const nodeType = event.dataTransfer.getData("application/x-bt-node");
    if (!nodeType || !instance) {
      return;
    }
    const position = instance.screenToFlowPosition({ x: event.clientX, y: event.clientY });
    changeTree((current) => addNode(current, nodeType as Parameters<typeof addNode>[1], position));
  }

  function handleConnect(connection: Connection) {
    if (!connection.source || !connection.target) {
      return;
    }
    const sourceNode = tree.nodes.find((node) => node.id === connection.source);
    if (!sourceNode || !supportsChildren(sourceNode.type)) {
      setMessage("Only composite and decorator nodes can accept children.");
      return;
    }
    changeTree((current) => connectNodes(current, connection.source!, connection.target!));
  }

  function handleNodesChange(changes: NodeChange[]) {
    changeTree((current) => {
      let next = current;
      for (const change of changes) {
        if (change.type === "remove") {
          next = deleteNodeCascade(next, change.id);
        }
        if (change.type === "position" && change.position) {
          next = updateNode(next, change.id, (node) => ({ ...node, position: change.position }));
        }
      }
      return next;
    });
  }

  function handleEdgesChange(changes: EdgeChange[]) {
    const removals = changes.filter((change) => change.type === "remove");
    if (removals.length === 0) {
      return;
    }
    changeTree((current) => {
      let next = current;
      for (const removal of removals) {
        const edge = current.edges.find((candidate) => candidate.id === removal.id);
        if (edge) {
          next = disconnectNode(next, edge.target);
        }
      }
      return next;
    });
  }

  const selectedNode = tree.nodes.find((node) => node.id === selectedNodeId) ?? null;

  return (
    <div className="app-shell">
      <TreeSidebar
        tree={tree}
        trees={trees}
        busy={busy}
        onCreate={() => {
          setTree(createEmptyTree());
          setSession(null);
          setSelectedNodeId(null);
          setMessage("Started a new local draft.");
        }}
        onReload={() => void refreshTrees()}
        onSelect={(treeId) => void loadTree(treeId)}
        onSave={() => void saveTree()}
        onDelete={() => void deleteCurrentTree()}
        onTreeChange={changeTree}
      />

      <main className="workspace">
        <header className="workspace__header">
          <div>
            <h1>{tree.name}</h1>
            <p>{message}</p>
          </div>
          <div className={`status-pill status-pill--${tree.is_valid ? "success" : "invalid"}`}>
            {tree.is_valid ? "Valid tree" : "Draft / invalid"}
          </div>
        </header>

        <div
          className="canvas-shell"
          onDragOver={(event) => {
            event.preventDefault();
            event.dataTransfer.dropEffect = "move";
          }}
          onDrop={handleDrop}
        >
          <ReactFlow
            fitView
            edges={flowEdges}
            nodes={flowNodes}
            nodeTypes={nodeTypes}
            onConnect={handleConnect}
            onEdgesChange={handleEdgesChange}
            onInit={setInstance}
            onNodeClick={(_, node) => setSelectedNodeId(node.id)}
            onNodesChange={handleNodesChange}
            onPaneClick={() => setSelectedNodeId(null)}
          >
            <MiniMap />
            <Controls />
            <Background color="#d0c4b2" gap={24} />
          </ReactFlow>
        </div>

        {tree.validation_errors.length > 0 && (
          <section className="validation-box">
            <h3>Validation issues</h3>
            <ul>
              {tree.validation_errors.map((issue, index) => (
                <li key={`${issue.node_id ?? "tree"}-${index}`}>{issue.message}</li>
              ))}
            </ul>
          </section>
        )}
      </main>

      <aside className="sidebar sidebar--right">
        <Palette onQuickAdd={handleQuickAdd} />
        <Inspector
          node={selectedNode}
          tree={tree}
          onDeleteNode={(nodeId) => {
            changeTree((current) => deleteNodeCascade(current, nodeId));
            setSelectedNodeId(null);
          }}
          onReorderChild={(parentId, childId, direction) =>
            changeTree((current) => reorderChild(current, parentId, childId, direction))
          }
          onUpdateNode={(nodeId, updater) => changeTree((current) => updateNode(current, nodeId, updater))}
        />
        <RunControls
          busy={busy}
          session={session}
          tree={tree}
          onReset={() => void resetSession()}
          onRun={() => void runTree()}
          onTick={() => void tickSession()}
        />
      </aside>
    </div>
  );
}

export default function App() {
  return (
    <ReactFlowProvider>
      <AppShell />
    </ReactFlowProvider>
  );
}

