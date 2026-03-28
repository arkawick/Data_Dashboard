import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, Calendar, User } from "lucide-react";
import { fetchProjects } from "@/lib/api";
import type { Project } from "@/types/api";
import { Card, CardContent } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { Pagination } from "@/components/ui/Pagination";
import { formatDate, projectStatusClass, priorityClass, cn } from "@/lib/utils";

const DOMAINS = ["Automotive", "Finance", "Healthcare", "Retail", "Industrial", "Aerospace", "Telecom"];
const STATUSES = ["Active", "Completed", "On Hold", "Planning", "Cancelled"];
const PRIORITIES = ["Critical", "High", "Medium", "Low"];

const DOMAIN_COLORS: Record<string, string> = {
  Automotive: "bg-blue-100 text-blue-800",
  Finance: "bg-green-100 text-green-800",
  Healthcare: "bg-red-100 text-red-800",
  Retail: "bg-purple-100 text-purple-800",
  Industrial: "bg-orange-100 text-orange-800",
  Aerospace: "bg-indigo-100 text-indigo-800",
  Telecom: "bg-teal-100 text-teal-800",
};

function ProjectCard({ project }: { project: Project }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
      <div className="p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-900 text-sm truncate" title={project.name}>
              {project.name}
            </h3>
            <p className="text-xs text-gray-400 font-mono mt-0.5">{project.project_id}</p>
          </div>
          <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium shrink-0", projectStatusClass(project.status))}>
            {project.status}
          </span>
        </div>

        <div className="flex flex-wrap gap-1.5 mb-3">
          <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", DOMAIN_COLORS[project.domain] ?? "bg-gray-100 text-gray-700")}>
            {project.domain}
          </span>
          <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", priorityClass(project.priority))}>
            {project.priority} priority
          </span>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-3">
          <User className="h-3.5 w-3.5 text-gray-400" />
          <span>{project.lead_name}</span>
          {project.team && (
            <>
              <span className="text-gray-300">·</span>
              <span>Team {project.team}</span>
            </>
          )}
        </div>

        {project.tech_stack && project.tech_stack.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {project.tech_stack.slice(0, 4).map((tech) => (
              <span key={tech} className="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-medium">
                {tech}
              </span>
            ))}
            {project.tech_stack.length > 4 && (
              <span className="text-xs text-gray-400">+{project.tech_stack.length - 4}</span>
            )}
          </div>
        )}

        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 font-medium"
        >
          {expanded ? "Hide details" : "Show details"}
          {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        </button>

        {expanded && (
          <div className="mt-3 pt-3 border-t border-gray-100 space-y-2 animate-fade-in">
            {project.description && (
              <p className="text-xs text-gray-600 leading-relaxed">{project.description}</p>
            )}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center gap-1.5 text-gray-500">
                <Calendar className="h-3 w-3" />
                <span>Start: {formatDate(project.start_date)}</span>
              </div>
              <div className="flex items-center gap-1.5 text-gray-500">
                <Calendar className="h-3 w-3" />
                <span>End: {formatDate(project.end_date)}</span>
              </div>
            </div>
            {project.budget > 0 && (
              <p className="text-xs text-gray-500">
                Budget: <span className="font-medium text-gray-700">${project.budget.toLocaleString()}</span>
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function Projects() {
  const [page, setPage] = useState(1);
  const [domain, setDomain] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");

  const params: Record<string, string> = { page: String(page) };
  if (domain) params.domain = domain;
  if (status) params.status = status;
  if (priority) params.priority = priority;

  const { data, isLoading } = useQuery({
    queryKey: ["projects", page, domain, status, priority],
    queryFn: () => fetchProjects(params),
  });

  const handleFilter = () => setPage(1);

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Projects</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          {data ? `${data.count.toLocaleString()} total projects` : "Loading..."}
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-wrap gap-3">
            <Select
              value={domain}
              onChange={(e) => { setDomain(e.target.value); handleFilter(); }}
              placeholder="All Domains"
              options={DOMAINS.map((d) => ({ value: d, label: d }))}
              className="w-44"
            />
            <Select
              value={status}
              onChange={(e) => { setStatus(e.target.value); handleFilter(); }}
              placeholder="All Statuses"
              options={STATUSES.map((s) => ({ value: s, label: s }))}
              className="w-40"
            />
            <Select
              value={priority}
              onChange={(e) => { setPriority(e.target.value); handleFilter(); }}
              placeholder="All Priorities"
              options={PRIORITIES.map((p) => ({ value: p, label: p }))}
              className="w-36"
            />
          </div>
        </CardContent>
      </Card>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <Skeleton key={i} className="h-52 w-full rounded-xl" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data?.results.map((project) => (
              <ProjectCard key={project._id ?? project.project_id} project={project} />
            ))}
          </div>
          {data && (
            <Card>
              <Pagination
                page={data.page}
                pages={data.pages}
                total={data.count}
                onPageChange={setPage}
              />
            </Card>
          )}
        </>
      )}
    </div>
  );
}
