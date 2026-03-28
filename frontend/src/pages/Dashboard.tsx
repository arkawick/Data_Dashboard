import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  Users,
  FolderKanban,
  FlaskConical,
  Bug,
  FileText,
  Brain,
  Network,
  RefreshCw,
  Loader2,
  CheckCircle,
  Activity,
} from "lucide-react";
import { fetchStats, fetchHealth, fetchGraphStats, rebuildPipeline } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { BugSeverityChart } from "@/components/charts/BugSeverityChart";
import { TestCaseStatusChart } from "@/components/charts/TestCaseStatusChart";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ElementType;
  color: string;
  loading?: boolean;
}

function StatCard({ label, value, icon: Icon, color, loading }: StatCardProps) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
            {loading ? (
              <Skeleton className="h-7 w-20 mt-2" />
            ) : (
              <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
            )}
          </div>
          <div className={cn("w-11 h-11 rounded-xl flex items-center justify-center", color)}>
            <Icon className="h-5 w-5 text-white" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function Dashboard() {
  const { toast } = useToast();
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<string | null>(null);

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: fetchStats,
    refetchInterval: 30000,
  });

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 15000,
  });

  const { data: graphStats, isLoading: graphLoading } = useQuery({
    queryKey: ["graphStats"],
    queryFn: fetchGraphStats,
    refetchInterval: 60000,
  });

  const rebuildMutation = useMutation({
    mutationFn: rebuildPipeline,
    onSuccess: (data) => {
      setTaskId(data.task_id);
      setTaskStatus(data.status);
      toast("Pipeline rebuild triggered successfully", "success");
    },
    onError: () => {
      toast("Failed to trigger pipeline rebuild", "error");
    },
  });

  const statCards = [
    { label: "Employees", value: stats?.counts.employees ?? 0, icon: Users, color: "bg-blue-500" },
    { label: "Projects", value: stats?.counts.projects ?? 0, icon: FolderKanban, color: "bg-purple-500" },
    { label: "Test Cases", value: stats?.counts.test_cases ?? 0, icon: FlaskConical, color: "bg-teal-500" },
    { label: "Bugs", value: stats?.counts.bugs ?? 0, icon: Bug, color: "bg-red-500" },
    { label: "Requirements", value: stats?.counts.requirements ?? 0, icon: FileText, color: "bg-orange-500" },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Overview</h2>
        <p className="text-sm text-gray-500 mt-0.5">System metrics and GraphRAG status</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {statCards.map((card) => (
          <StatCard
            key={card.label}
            {...card}
            loading={statsLoading}
          />
        ))}
      </div>

      {/* GraphRAG status card */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-4 w-4 text-blue-500" />
              GraphRAG Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            {healthLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-5 w-full" />
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-5 w-1/2" />
              </div>
            ) : health ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Status</span>
                  <span className={cn(
                    "inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full",
                    health.status === "ok"
                      ? "bg-green-100 text-green-800"
                      : "bg-red-100 text-red-800"
                  )}>
                    <span className={cn(
                      "w-1.5 h-1.5 rounded-full",
                      health.status === "ok" ? "bg-green-500" : "bg-red-500"
                    )} />
                    {health.status === "ok" ? "Online" : health.status}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Chunks Loaded</span>
                  <span className="text-sm font-semibold text-gray-900">{health.chunks_loaded.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Retriever</span>
                  <span className="text-sm font-semibold text-gray-900 capitalize">{health.retriever_type}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Neo4j</span>
                  <span className={cn(
                    "text-xs font-medium px-2 py-0.5 rounded-full",
                    health.neo4j_available
                      ? "bg-green-100 text-green-800"
                      : "bg-gray-100 text-gray-600"
                  )}>
                    {health.neo4j_available ? "Connected" : "Offline"}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-400">FastAPI unreachable</p>
            )}
          </CardContent>
        </Card>

        {/* Pipeline rebuild */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-orange-500" />
              Pipeline Control
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-500 mb-4">
              Trigger a full rebuild of the GraphRAG pipeline. This re-builds the graph, re-chunks, and reloads retrieval indices.
            </p>
            <Button
              onClick={() => rebuildMutation.mutate()}
              disabled={rebuildMutation.isPending}
              variant="outline"
              className="gap-2"
            >
              {rebuildMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              {rebuildMutation.isPending ? "Rebuilding..." : "Rebuild Pipeline"}
            </Button>
            {taskId && (
              <div className="mt-3 p-3 bg-green-50 rounded-lg border border-green-200 flex items-start gap-2">
                <CheckCircle className="h-4 w-4 text-green-600 mt-0.5 shrink-0" />
                <div>
                  <p className="text-xs font-medium text-green-800">Task queued</p>
                  <p className="text-xs text-green-700 mt-0.5 font-mono">{taskId}</p>
                  {taskStatus && (
                    <p className="text-xs text-green-600 mt-0.5">Status: {taskStatus}</p>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bug className="h-4 w-4 text-red-500" />
              Bug Severity Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-52 w-full" />
            ) : stats?.bug_by_severity ? (
              <BugSeverityChart data={stats.bug_by_severity} />
            ) : (
              <p className="text-sm text-gray-400 h-52 flex items-center justify-center">No data</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-teal-500" />
              Test Case Status Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <Skeleton className="h-52 w-full" />
            ) : stats?.tc_by_status ? (
              <TestCaseStatusChart data={stats.tc_by_status} />
            ) : (
              <p className="text-sm text-gray-400 h-52 flex items-center justify-center">No data</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Graph stats */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="h-4 w-4 text-purple-500" />
            Knowledge Graph Statistics
          </CardTitle>
        </CardHeader>
        <CardContent>
          {graphLoading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : graphStats ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-purple-50 rounded-xl p-4 border border-purple-100">
                  <p className="text-xs text-purple-600 font-medium uppercase tracking-wide">Nodes</p>
                  <p className="text-2xl font-bold text-purple-900 mt-1">{graphStats.nodes.toLocaleString()}</p>
                </div>
                <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                  <p className="text-xs text-blue-600 font-medium uppercase tracking-wide">Edges</p>
                  <p className="text-2xl font-bold text-blue-900 mt-1">{graphStats.edges.toLocaleString()}</p>
                </div>
                <div className="bg-teal-50 rounded-xl p-4 border border-teal-100">
                  <p className="text-xs text-teal-600 font-medium uppercase tracking-wide">Node Types</p>
                  <p className="text-2xl font-bold text-teal-900 mt-1">{Object.keys(graphStats.node_types).length}</p>
                </div>
                <div className="bg-orange-50 rounded-xl p-4 border border-orange-100">
                  <p className="text-xs text-orange-600 font-medium uppercase tracking-wide">Edge Types</p>
                  <p className="text-2xl font-bold text-orange-900 mt-1">{Object.keys(graphStats.edge_types).length}</p>
                </div>
              </div>

              {Object.keys(graphStats.node_types).length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Node Type Breakdown</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(graphStats.node_types)
                      .sort(([, a], [, b]) => b - a)
                      .map(([type, count]) => (
                        <span
                          key={type}
                          className="inline-flex items-center gap-1.5 bg-gray-100 text-gray-700 text-xs px-2.5 py-1 rounded-full border border-gray-200"
                        >
                          <span className="font-medium">{type}</span>
                          <span className="text-gray-400">{count}</span>
                        </span>
                      ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-400">FastAPI unreachable</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
