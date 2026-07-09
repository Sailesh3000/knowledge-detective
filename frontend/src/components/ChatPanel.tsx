import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Loader2, BookOpen, AlertCircle, Cpu, Network, FileText } from "lucide-react";
import { askQuestion } from "../api";
import type { QueryResponse } from "../api";

interface ChatPanelProps {
  onSelectEntity: (name: string) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ onSelectEntity }) => {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<QueryResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await askQuestion(question);
      setResponse(data);
    } catch (err: any) {
      setError(err.message || "An error occurred while fetching the answer.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 border-r border-zinc-800/80">
      {/* Header */}
      <div className="px-6 py-4 border-b border-zinc-800/60 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-medium text-zinc-100 tracking-tight flex items-center gap-2">
            <Network className="w-5 h-5 text-zinc-400 stroke-[1.5]" />
            Knowledge Detective
          </h1>
          <p className="text-xs text-zinc-500 font-normal">Hybrid semantic Q&A reasoning engine</p>
        </div>
      </div>

      {/* Query input */}
      <div className="p-6 border-b border-zinc-800/40">
        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
            placeholder="Ask a question about the project (e.g. why did we choose Neo4j?)..."
            className="w-full bg-zinc-900/60 text-zinc-100 placeholder-zinc-500 pl-11 pr-24 py-3 rounded-lg border border-zinc-800 focus:outline-none focus:border-zinc-700 transition text-sm disabled:opacity-50"
          />
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500">
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin text-zinc-400" />
            ) : (
              <Search className="w-4 h-4" />
            )}
          </div>
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-zinc-100 hover:bg-zinc-200 text-zinc-950 px-3 py-1 rounded text-xs font-medium transition disabled:opacity-40 disabled:hover:bg-zinc-100"
          >
            Run Query
          </button>
        </form>
      </div>

      {/* Results Workspace */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <AnimatePresence mode="wait">
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="p-4 bg-red-950/20 border border-red-900/40 rounded-lg flex gap-3 text-red-400 text-sm"
            >
              <AlertCircle className="w-5 h-5 shrink-0" />
              <div>
                <p className="font-medium">Query Execution Failed</p>
                <p className="text-xs text-red-500 mt-1">{error}</p>
              </div>
            </motion.div>
          )}

          {loading && (
            <div className="flex flex-col items-center justify-center h-64 text-zinc-500 space-y-3">
              <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
              <p className="text-xs font-normal">Analyzing question & traversing graph databases...</p>
            </div>
          )}

          {!loading && !response && !error && (
            <div className="flex flex-col items-center justify-center h-64 text-zinc-600 text-center px-6">
              <Network className="w-8 h-8 text-zinc-800 stroke-[1.2] mb-3" />
              <p className="text-sm font-medium">Enter a question above to get started</p>
              <p className="text-xs text-zinc-600 mt-1 max-w-xs leading-relaxed">
                The agent will decompose the query, extract entities, search vectors, and traverse structural relationships to synthesize an answer.
              </p>
            </div>
          )}

          {response && !loading && (
            <motion.div
              key={response.question}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
              className="space-y-6"
            >
              {/* Query Plan */}
              <div className="bg-zinc-900/30 border border-zinc-800/50 rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-zinc-400 flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-zinc-500" />
                    Query Execution Plan
                  </span>
                  <span className="text-[10px] bg-zinc-800/80 text-zinc-400 font-mono px-2 py-0.5 rounded">
                    Strategy: {response.plan.search_type.toUpperCase()}
                  </span>
                </div>
                
                {/* Deconstructed Subqueries */}
                <div className="space-y-1.5">
                  <p className="text-[10px] uppercase text-zinc-500 font-medium tracking-wider">Sub-queries</p>
                  <div className="flex flex-wrap gap-1.5">
                    {response.plan.sub_queries.map((q, idx) => (
                      <span key={idx} className="text-xs bg-zinc-900 text-zinc-400 border border-zinc-800/60 px-2 py-1 rounded">
                        {q}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Extracted Entities */}
                {(response.plan.entities.length > 0 || response.plan.topics.length > 0) && (
                  <div className="grid grid-cols-2 gap-4 pt-1.5 border-t border-zinc-800/40">
                    {response.plan.entities.length > 0 && (
                      <div>
                        <p className="text-[10px] uppercase text-zinc-500 font-medium tracking-wider mb-1">Entities</p>
                        <div className="flex flex-wrap gap-1">
                          {response.plan.entities.map((ent, idx) => (
                            <button
                              key={idx}
                              type="button"
                              onClick={() => onSelectEntity(ent)}
                              className="text-xs bg-zinc-900/80 text-zinc-300 hover:bg-zinc-800 px-1.5 py-0.5 rounded transition cursor-pointer text-left"
                            >
                              {ent}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    {response.plan.topics.length > 0 && (
                      <div>
                        <p className="text-[10px] uppercase text-zinc-500 font-medium tracking-wider mb-1">Topics</p>
                        <div className="flex flex-wrap gap-1">
                          {response.plan.topics.map((top, idx) => (
                            <button
                              key={idx}
                              type="button"
                              onClick={() => onSelectEntity(top)}
                              className="text-xs bg-zinc-900/80 text-zinc-300 hover:bg-zinc-800 px-1.5 py-0.5 rounded transition cursor-pointer text-left"
                            >
                              {top}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Synthesized Answer */}
              <div className="space-y-2">
                <p className="text-xs font-medium text-zinc-400">Synthesized Answer</p>
                <div className="text-zinc-100 text-sm leading-relaxed whitespace-pre-line bg-zinc-900/10 border border-zinc-800/20 p-5 rounded-lg font-light">
                  {response.answer}
                </div>
              </div>

              {/* Citations */}
              <div className="space-y-3">
                <p className="text-xs font-medium text-zinc-400 flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-zinc-500" />
                  Citations ({response.citations.length})
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {response.citations.map((cite, idx) => (
                    <div
                      key={idx}
                      className="bg-zinc-900/40 border border-zinc-800/60 p-3.5 rounded-lg flex flex-col justify-between hover:border-zinc-700 transition"
                    >
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-mono uppercase bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-400">
                            {cite.source}
                          </span>
                          <span className="text-[10px] text-zinc-500">
                            {cite.timestamp ? new Date(cite.timestamp).toLocaleDateString() : ""}
                          </span>
                        </div>
                        <h4 className="text-xs font-medium text-zinc-200 line-clamp-1">{cite.title}</h4>
                        <p className="text-[11px] text-zinc-400 font-light">Author: {cite.author}</p>
                      </div>
                      
                      {cite.url && (
                        <div className="mt-3 pt-2 border-t border-zinc-800/40 flex justify-end">
                          <a
                            href={cite.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[10px] text-zinc-300 hover:text-zinc-100 flex items-center gap-1 transition"
                          >
                            <FileText className="w-3 h-3 text-zinc-500" />
                            View Source
                          </a>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};
