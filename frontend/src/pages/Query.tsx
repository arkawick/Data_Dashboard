import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Send,
  Loader2,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
  Brain,
  Network,
  Clock,
  Zap,
} from "lucide-react";
import { queryGraphRAG, queryHybrid } from "@/lib/api";
import type { QueryResponse, Chunk } from "@/types/api";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { cn, truncate } from "@/lib/utils";

type Mode = "standard" | "hybrid";
type Backend = "auto" | "dry_run" | "claude" | "ollama";

interface HistoryItem {
  id: string;
  question: string;
  response: QueryResponse;
  mode: Mode;
  timestamp: Date;
}

function ChunkItem({ chunk }: { chunk: Chunk }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-100 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-gray-50 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-3.5 w-3.5 text-gray-400 shrink-0" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-gray-400 shrink-0" />
        )}
        <span className="text-xs font-medium text-gray-500 shrink-0">{chunk.id}</span>
        <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded shrink-0">{chunk.type}</span>
        <span className="text-xs text-gray-600 truncate">{truncate(chunk.text, 80)}</span>
        {chunk.score !== undefined && (
          <span className="text-xs text-gray-400 ml-auto shrink-0">
            {chunk.score.toFixed(3)}
          </span>
        )}
      </button>
      {expanded && (
        <div className="px-3 pb-3 pt-1 bg-gray-50 border-t border-gray-100">
          <p className="text-xs text-gray-700 leading-relaxed whitespace-pre-wrap">{chunk.text}</p>
        </div>
      )}
    </div>
  );
}

function ResponsePanel({ response, mode }: { response: QueryResponse; mode: Mode }) {
  const [copied, setCopied] = useState(false);
  const [chunksOpen, setChunksOpen] = useState(false);
  const [pathsOpen, setPathsOpen] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(response.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Meta */}
      <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <Zap className="h-3.5 w-3.5 text-blue-500" />
          Backend: <span className="font-medium text-gray-700">{response.backend}</span>
        </span>
        <span className="text-gray-300">·</span>
        <span className="flex items-center gap-1">
          <Brain className="h-3.5 w-3.5 text-purple-500" />
          {response.chunks_retrieved} chunks retrieved
        </span>
        {mode === "hybrid" && response.graph_paths && (
          <>
            <span className="text-gray-300">·</span>
            <span className="flex items-center gap-1">
              <Network className="h-3.5 w-3.5 text-teal-500" />
              {response.graph_paths.length} graph paths
            </span>
          </>
        )}
      </div>

      {/* Answer */}
      <div className="relative">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Answer</span>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-700 transition-colors"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
        <div className="bg-gradient-to-br from-slate-50 to-blue-50/30 rounded-xl border border-gray-200 p-5">
          <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">{response.answer}</p>
        </div>
      </div>

      {/* Chunks */}
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <button
          onClick={() => setChunksOpen(!chunksOpen)}
          className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
        >
          <span className="text-sm font-medium text-gray-700">
            Retrieved Chunks ({response.chunks.length})
          </span>
          {chunksOpen ? (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-400" />
          )}
        </button>
        {chunksOpen && (
          <div className="p-3 space-y-1 max-h-72 overflow-y-auto">
            {response.chunks.map((chunk, i) => (
              <ChunkItem key={`${chunk.id}-${i}`} chunk={chunk} />
            ))}
          </div>
        )}
      </div>

      {/* Graph paths (hybrid only) */}
      {mode === "hybrid" && response.graph_paths && response.graph_paths.length > 0 && (
        <div className="border border-teal-200 rounded-xl overflow-hidden">
          <button
            onClick={() => setPathsOpen(!pathsOpen)}
            className="w-full flex items-center justify-between px-4 py-3 bg-teal-50 hover:bg-teal-100 transition-colors"
          >
            <span className="text-sm font-medium text-teal-800">
              Graph Paths ({response.graph_paths.length})
            </span>
            {pathsOpen ? (
              <ChevronDown className="h-4 w-4 text-teal-500" />
            ) : (
              <ChevronRight className="h-4 w-4 text-teal-500" />
            )}
          </button>
          {pathsOpen && (
            <div className="p-3 space-y-1.5 max-h-48 overflow-y-auto bg-white">
              {response.graph_paths.map((path, i) => (
                <div key={i} className="flex flex-wrap items-center gap-1 text-xs">
                  {path.map((node, j) => (
                    <span key={j} className="flex items-center gap-1">
                      <span className="bg-teal-100 text-teal-800 px-2 py-0.5 rounded font-medium">
                        {node}
                      </span>
                      {j < path.length - 1 && (
                        <ChevronRight className="h-3 w-3 text-gray-400" />
                      )}
                    </span>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function Query() {
  const { toast } = useToast();
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<Mode>("standard");
  const [backend, setBackend] = useState<Backend>("auto");
  const [topK, setTopK] = useState(20);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const activeItem = history.find((h) => h.id === activeId);

  const mutation = useMutation({
    mutationFn: (q: string) => {
      const payload = { question: q, top_k: topK, backend };
      return mode === "hybrid" ? queryHybrid(payload) : queryGraphRAG(payload);
    },
    onSuccess: (data, q) => {
      const item: HistoryItem = {
        id: Date.now().toString(),
        question: q,
        response: data,
        mode,
        timestamp: new Date(),
      };
      setHistory((prev) => [item, ...prev]);
      setActiveId(item.id);
      setQuestion("");
    },
    onError: () => {
      toast("Failed to query GraphRAG. Is the FastAPI server running?", "error");
    },
  });

  const handleSubmit = () => {
    const q = question.trim();
    if (!q || mutation.isPending) return;
    mutation.mutate(q);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      handleSubmit();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`;
  }, [question]);

  return (
    <div className="animate-fade-in h-full">
      <div className="mb-5">
        <h2 className="text-xl font-bold text-gray-900">Query</h2>
        <p className="text-sm text-gray-500 mt-0.5">Ask questions about your data using GraphRAG retrieval</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5" style={{ minHeight: "calc(100vh - 200px)" }}>
        {/* Left: History */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm h-full flex flex-col">
            <div className="px-4 py-3 border-b border-gray-100">
              <h3 className="text-sm font-semibold text-gray-700">Query History</h3>
            </div>
            {history.length === 0 ? (
              <div className="flex-1 flex items-center justify-center p-6">
                <div className="text-center">
                  <Clock className="h-8 w-8 text-gray-200 mx-auto mb-2" />
                  <p className="text-xs text-gray-400">No queries yet</p>
                </div>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto py-2">
                {history.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setActiveId(item.id)}
                    className={cn(
                      "w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-l-2",
                      activeId === item.id
                        ? "border-l-blue-500 bg-blue-50/50"
                        : "border-l-transparent"
                    )}
                  >
                    <p className="text-xs font-medium text-gray-700 line-clamp-2">
                      {item.question}
                    </p>
                    <div className="flex items-center gap-1.5 mt-1">
                      <span className={cn(
                        "text-xs px-1.5 py-0.5 rounded",
                        item.mode === "hybrid"
                          ? "bg-teal-100 text-teal-700"
                          : "bg-gray-100 text-gray-600"
                      )}>
                        {item.mode}
                      </span>
                      <span className="text-xs text-gray-400">
                        {item.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Main panel */}
        <div className="lg:col-span-3 flex flex-col gap-4">
          {/* Input card */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            {/* Controls */}
            <div className="flex flex-wrap gap-3 mb-4">
              {/* Mode toggle */}
              <div className="flex rounded-lg border border-gray-200 overflow-hidden">
                <button
                  onClick={() => setMode("standard")}
                  className={cn(
                    "px-4 py-1.5 text-xs font-medium transition-colors",
                    mode === "standard"
                      ? "bg-blue-600 text-white"
                      : "bg-white text-gray-600 hover:bg-gray-50"
                  )}
                >
                  Standard
                </button>
                <button
                  onClick={() => setMode("hybrid")}
                  className={cn(
                    "px-4 py-1.5 text-xs font-medium transition-colors",
                    mode === "hybrid"
                      ? "bg-teal-600 text-white"
                      : "bg-white text-gray-600 hover:bg-gray-50"
                  )}
                >
                  Hybrid
                </button>
              </div>

              {/* Backend */}
              <div className="relative">
                <select
                  value={backend}
                  onChange={(e) => setBackend(e.target.value as Backend)}
                  className="h-8 rounded-lg border border-gray-200 bg-white px-3 pr-8 text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none"
                >
                  <option value="auto">Backend: Auto</option>
                  <option value="dry_run">Backend: Dry Run</option>
                  <option value="claude">Backend: Claude</option>
                  <option value="ollama">Backend: Ollama</option>
                </select>
                <ChevronDown className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
              </div>

              {/* Top K */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500 shrink-0">Top K:</span>
                <input
                  type="range"
                  min={5}
                  max={30}
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="w-24 h-1.5 bg-gray-200 rounded accent-blue-600"
                />
                <span className="text-xs font-semibold text-gray-700 w-6">{topK}</span>
              </div>
            </div>

            {/* Input */}
            <div className="relative">
              <textarea
                ref={textareaRef}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about your data... (Ctrl+Enter to send)"
                className="w-full min-h-16 max-h-48 resize-none rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-colors pr-12"
                rows={2}
              />
              <Button
                onClick={handleSubmit}
                disabled={!question.trim() || mutation.isPending}
                size="icon"
                className="absolute right-2 bottom-2 h-8 w-8 rounded-lg"
              >
                {mutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="text-xs text-gray-400 mt-1.5">Press Ctrl+Enter to submit</p>
          </div>

          {/* Response */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 flex-1">
            {mutation.isPending ? (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center">
                  <Loader2 className="h-6 w-6 text-blue-500 animate-spin" />
                </div>
                <p className="text-sm text-gray-500">Querying GraphRAG...</p>
                <p className="text-xs text-gray-400">Retrieving {topK} chunks via {mode} search</p>
              </div>
            ) : activeItem ? (
              <div>
                <div className="flex items-start gap-2 mb-4 pb-4 border-b border-gray-100">
                  <div className="w-7 h-7 rounded-lg bg-blue-100 flex items-center justify-center shrink-0 mt-0.5">
                    <Brain className="h-4 w-4 text-blue-600" />
                  </div>
                  <p className="text-sm font-medium text-gray-800 leading-relaxed">{activeItem.question}</p>
                </div>
                <ResponsePanel response={activeItem.response} mode={activeItem.mode} />
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center">
                  <Brain className="h-7 w-7 text-blue-400" />
                </div>
                <h3 className="text-sm font-semibold text-gray-700">Ready to Query</h3>
                <p className="text-xs text-gray-400 max-w-xs">
                  Ask a question about your projects, bugs, test cases, requirements, or employees.
                  The GraphRAG pipeline will retrieve relevant context and generate an answer.
                </p>
                <div className="mt-2 flex flex-wrap justify-center gap-2">
                  {[
                    "What are the critical bugs in Healthcare?",
                    "Show me Active projects in Finance",
                    "Which employees are in QA?",
                    "What requirements are unverified?",
                  ].map((q) => (
                    <button
                      key={q}
                      onClick={() => setQuestion(q)}
                      className="text-xs bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-600 px-3 py-1.5 rounded-lg transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
