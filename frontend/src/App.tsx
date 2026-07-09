import { useState } from "react";
import { ChatPanel } from "./components/ChatPanel";
import { TimelineView } from "./components/TimelineView";
import { GraphView } from "./components/GraphView";
import { Calendar, Network } from "lucide-react";

type Tab = "timeline" | "graph";

function App() {
  const [activeTab, setActiveTab] = useState<Tab>("graph");
  const [filterText, setFilterText] = useState("");

  const handleSelectEntity = (name: string) => {
    setFilterText(name);
    // Switch to the relevant tab if needed, or keep it open
  };

  const handleClearFilter = () => {
    setFilterText("");
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-950 text-zinc-100 antialiased">
      {/* Left Panel: Reasoning Engine & Q&A Chat */}
      <div className="w-[45%] h-full shrink-0">
        <ChatPanel onSelectEntity={handleSelectEntity} />
      </div>

      {/* Right Panel: Interactive Visualizations (Timeline & Graph) */}
      <div className="flex-1 h-full flex flex-col min-w-0">
        {/* Navigation Tabs Header */}
        <div className="px-6 py-[18px] border-b border-zinc-800/60 bg-zinc-950 flex items-center justify-between shrink-0">
          <div className="flex gap-4">
            <button
              onClick={() => setActiveTab("graph")}
              className={`flex items-center gap-1.5 pb-2 text-xs font-medium tracking-tight border-b-2 transition ${
                activeTab === "graph"
                  ? "text-zinc-100 border-zinc-100"
                  : "text-zinc-500 border-transparent hover:text-zinc-300"
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              Knowledge Graph
            </button>
            <button
              onClick={() => setActiveTab("timeline")}
              className={`flex items-center gap-1.5 pb-2 text-xs font-medium tracking-tight border-b-2 transition ${
                activeTab === "timeline"
                  ? "text-zinc-100 border-zinc-100"
                  : "text-zinc-500 border-transparent hover:text-zinc-300"
              }`}
            >
              <Calendar className="w-3.5 h-3.5" />
              Decision Timeline
            </button>
          </div>

          {filterText && (
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-zinc-500 font-medium">Active Filter:</span>
              <span className="text-[10px] bg-zinc-900 border border-zinc-800 text-zinc-300 font-mono px-2 py-0.5 rounded flex items-center gap-1.5">
                {filterText}
                <button
                  onClick={handleClearFilter}
                  className="text-zinc-500 hover:text-zinc-300 font-sans font-semibold cursor-pointer"
                >
                  ×
                </button>
              </span>
            </div>
          )}
        </div>

        {/* Tab workspace window */}
        <div className="flex-1 min-h-0 min-w-0">
          {activeTab === "graph" ? (
            <GraphView
              filterEntity={filterText}
              onSelectNode={handleSelectEntity}
              onClearFilter={handleClearFilter}
            />
          ) : (
            <TimelineView
              filterTopic={filterText}
              onClearFilter={handleClearFilter}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
