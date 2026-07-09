import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Mail, Calendar, GitCommit, FileText, Loader2, ArrowRight, X } from "lucide-react";
import { fetchTimeline } from "../api";
import type { TimelineEvent } from "../api";

interface TimelineViewProps {
  filterTopic: string;
  onClearFilter: () => void;
}

export const TimelineView: React.FC<TimelineViewProps> = ({ filterTopic, onClearFilter }) => {
  const [topicInput, setTopicInput] = useState(filterTopic);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(false);

  // Sync state when filterTopic changes from parent selection
  useEffect(() => {
    setTopicInput(filterTopic);
    loadTimeline(filterTopic);
  }, [filterTopic]);

  const loadTimeline = async (topic?: string) => {
    setLoading(true);
    try {
      const data = await fetchTimeline(topic);
      setEvents(data.events);
    } catch (err) {
      console.error("Failed to load timeline:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadTimeline(topicInput);
  };

  const handleClear = () => {
    setTopicInput("");
    onClearFilter();
    loadTimeline("");
  };

  const getSourceIcon = (source: string) => {
    switch (source.toLowerCase()) {
      case "gmail":
        return <Mail className="w-3.5 h-3.5 text-red-400 stroke-[1.8]" />;
      case "calendar":
        return <Calendar className="w-3.5 h-3.5 text-blue-400 stroke-[1.8]" />;
      case "github":
        return <GitCommit className="w-3.5 h-3.5 text-emerald-400 stroke-[1.8]" />;
      default:
        return <FileText className="w-3.5 h-3.5 text-zinc-400 stroke-[1.8]" />;
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Search Bar */}
      <div className="px-6 py-4 border-b border-zinc-800/40">
        <form onSubmit={handleSearchSubmit} className="relative">
          <input
            type="text"
            value={topicInput}
            onChange={(e) => setTopicInput(e.target.value)}
            placeholder="Filter timeline by topic, technology, or author..."
            className="w-full bg-zinc-900/50 text-zinc-100 placeholder-zinc-500 pl-4 pr-12 py-2 rounded border border-zinc-800 focus:outline-none focus:border-zinc-700 transition text-xs"
          />
          {topicInput ? (
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
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>

      {/* Timeline Events List */}
      <div className="flex-1 overflow-y-auto px-6 py-6 relative">
        {loading ? (
          <div className="flex items-center justify-center h-48 text-zinc-500 space-y-2">
            <Loader2 className="w-5 h-5 animate-spin text-zinc-400" />
            <span className="text-xs ml-2">Loading chronological timeline...</span>
          </div>
        ) : events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-zinc-600 text-center">
            <Calendar className="w-6 h-6 text-zinc-800 stroke-[1.2] mb-2" />
            <p className="text-xs font-medium">No timeline events found</p>
            <p className="text-[10px] text-zinc-600 mt-0.5">Try widening your query or clearing the filters.</p>
          </div>
        ) : (
          <div className="relative border-l border-zinc-800 pl-6 ml-3 space-y-6">
            {events.map((event, idx) => (
              <motion.div
                key={event.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="relative"
              >
                {/* Timeline node dot indicator */}
                <div className="absolute -left-[37px] top-1.5 w-6 h-6 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center">
                  {getSourceIcon(event.source)}
                </div>

                {/* Event Card */}
                <div className="bg-zinc-900/30 border border-zinc-800/60 rounded-lg p-4 space-y-2 hover:border-zinc-800 transition">
                  <div className="flex items-center justify-between text-[10px] text-zinc-500 font-medium">
                    <span className="uppercase tracking-wider font-mono bg-zinc-900 px-1.5 py-0.5 rounded">
                      {event.source}
                    </span>
                    <span>
                      {event.timestamp ? new Date(event.timestamp).toLocaleString() : ""}
                    </span>
                  </div>

                  <h3 className="text-xs font-semibold text-zinc-200">{event.title}</h3>
                  <p className="text-[11px] text-zinc-400 font-light">Author: {event.author}</p>
                  
                  {event.snippet && (
                    <p className="text-[11px] text-zinc-500 leading-relaxed font-light line-clamp-3 bg-zinc-950/40 p-2 rounded border border-zinc-800/30 mt-1.5">
                      {event.snippet}
                    </p>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
