import React, { useState, useEffect, useRef } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { Loader2, Network, X, RefreshCw } from "lucide-react";
import { fetchGraph } from "../api";
import type { GraphResponse } from "../api";

interface GraphViewProps {
  filterEntity: string;
  onSelectNode: (name: string) => void;
  onClearFilter: () => void;
}

export const GraphView: React.FC<GraphViewProps> = ({ filterEntity, onSelectNode, onClearFilter }) => {
  const [entityInput, setEntityInput] = useState(filterEntity);
  const [graphData, setGraphData] = useState<GraphResponse>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const graphRef = useRef<any>(null);

  // Sync state when filterEntity changes from parent selection
  useEffect(() => {
    setEntityInput(filterEntity);
    loadGraph(filterEntity);
  }, [filterEntity]);

  const loadGraph = async (entityName?: string) => {
    setLoading(true);
    try {
      const data = await fetchGraph(entityName);
      
      // Auto-assign positions for react-force-graph if nodes don't have them
      const formattedNodes = data.nodes.map(n => ({
        ...n,
        x: n.x ?? (Math.random() - 0.5) * 200,
        y: n.y ?? (Math.random() - 0.5) * 200
      }));

      setGraphData({
        nodes: formattedNodes,
        links: data.links
      });
      
      // Center the graph on update
      setTimeout(() => {
        if (graphRef.current) {
          graphRef.current.zoomToFit(400, 50);
        }
      }, 200);

    } catch (err) {
      console.error("Failed to fetch graph data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadGraph(entityInput);
  };

  const handleClear = () => {
    setEntityInput("");
    onClearFilter();
    loadGraph("");
  };

  const handleNodeClick = (node: any) => {
    onSelectNode(node.id);
  };

  // Node coloring strategy mapping standard node types to neutral/cool tailwind-matching hexes
  const getNodeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case "person":
        return "#f4f4f5"; // Zinc 100
      case "technology":
        return "#10b981"; // Emerald 500
      case "topic":
        return "#06b6d4"; // Cyan 500
      case "document":
      case "doc":
      case "email":
      case "meeting":
      case "commit":
      case "issue":
        return "#8b5cf6"; // Violet 500
      default:
        return "#71717a"; // Zinc 500
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 overflow-hidden relative">
      {/* Top Search bar */}
      <div className="px-6 py-4 border-b border-zinc-800/40 flex items-center justify-between z-10 bg-zinc-950">
        <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
          <input
            type="text"
            value={entityInput}
            onChange={(e) => setEntityInput(e.target.value)}
            placeholder="Search graph (e.g. OAuth, Sailesh, Qdrant)..."
            className="w-full bg-zinc-900/50 text-zinc-100 placeholder-zinc-500 pl-4 pr-12 py-2 rounded border border-zinc-800 focus:outline-none focus:border-zinc-700 transition text-xs"
          />
          {entityInput ? (
            <button
              type="button"
              onClick={handleClear}
              className="absolute right-8 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          ) : null}
          <button
            type="submit"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-100 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>

      {/* Interactive Force Graph container */}
      <div className="flex-1 w-full h-full relative">
        {loading && (
          <div className="absolute inset-0 bg-zinc-950/70 flex items-center justify-center z-25">
            <div className="flex items-center gap-2 text-zinc-500">
              <Loader2 className="w-5 h-5 animate-spin text-zinc-400" />
              <span className="text-xs">Traversing 2-hop graph paths...</span>
            </div>
          </div>
        )}

        {graphData.nodes.length === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-zinc-600 text-center">
            <Network className="w-6 h-6 text-zinc-800 stroke-[1.2] mb-2" />
            <p className="text-xs font-medium">No graph data found</p>
            <p className="text-[10px] text-zinc-600">Try checking your Neo4j database or search filters.</p>
          </div>
        ) : (
          <div className="w-full h-full force-graph-container">
            <ForceGraph2D
              ref={graphRef}
              graphData={graphData}
              backgroundColor="#09090b" // zinc-950
              nodeRelSize={6}
              nodeVal={d => (d.type === "Document" || d.type === "Doc" ? 4 : 3)}
              linkColor={() => "#27272a"} // zinc-800
              linkWidth={1.5}
              linkDirectionalParticles={1}
              linkDirectionalParticleSpeed={() => 0.005}
              linkDirectionalParticleColor={() => "#3f3f46"} // zinc-700
              onNodeClick={handleNodeClick}
              nodeCanvasObject={(node: any, ctx, globalScale) => {
                const label = node.label;
                const fontSize = 9 / globalScale;
                ctx.font = `${fontSize}px ui-sans-serif, system-ui, sans-serif`;
                
                // Draw circle
                const color = getNodeColor(node.type);
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(node.x, node.y, 4, 0, 2 * Math.PI, false);
                ctx.fill();

                // Draw label under node on high zoom levels
                if (globalScale > 1.4) {
                  ctx.textAlign = 'center';
                  ctx.textBaseline = 'top';
                  ctx.fillStyle = '#a1a1aa'; // zinc-400
                  ctx.fillText(label, node.x, node.y + 6);
                }
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
};
