import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { fetchBugs } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { Skeleton } from "@/components/ui/Skeleton";
import { Pagination } from "@/components/ui/Pagination";
import { formatDate, severityClass, bugStatusClass, cn } from "@/lib/utils";

const SEVERITIES = ["Critical", "Major", "Minor", "Trivial"];
const STATUSES = ["Open", "In Progress", "Resolved", "Closed", "Reopened"];
const DOMAINS = ["Automotive", "Finance", "Healthcare", "Retail", "Industrial", "Aerospace", "Telecom"];

export function Bugs() {
  const [page, setPage] = useState(1);
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [domain, setDomain] = useState("");
  const [search, setSearch] = useState("");

  const params: Record<string, string> = { page: String(page) };
  if (severity) params.severity = severity;
  if (status) params.status = status;
  if (domain) params.domain = domain;
  if (search) params.search = search;

  const { data, isLoading } = useQuery({
    queryKey: ["bugs", page, severity, status, domain, search],
    queryFn: () => fetchBugs(params),
  });

  const handleFilter = () => setPage(1);

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Bugs</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          {data ? `${data.count.toLocaleString()} total bugs` : "Loading..."}
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-48">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search bugs..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); handleFilter(); }}
                className="pl-9"
              />
            </div>
            <Select
              value={severity}
              onChange={(e) => { setSeverity(e.target.value); handleFilter(); }}
              placeholder="All Severities"
              options={SEVERITIES.map((s) => ({ value: s, label: s }))}
              className="w-40"
            />
            <Select
              value={status}
              onChange={(e) => { setStatus(e.target.value); handleFilter(); }}
              placeholder="All Statuses"
              options={STATUSES.map((s) => ({ value: s, label: s }))}
              className="w-40"
            />
            <Select
              value={domain}
              onChange={(e) => { setDomain(e.target.value); handleFilter(); }}
              placeholder="All Domains"
              options={DOMAINS.map((d) => ({ value: d, label: d }))}
              className="w-44"
            />
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow className="bg-gray-50">
              <TableHead>Bug ID</TableHead>
              <TableHead>Title</TableHead>
              <TableHead>Severity</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Project</TableHead>
              <TableHead>Reporter</TableHead>
              <TableHead>Assignee</TableHead>
              <TableHead>Domain</TableHead>
              <TableHead>Date</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? Array.from({ length: 10 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 11 }).map((__, j) => (
                      <TableCell key={j}>
                        <Skeleton className="h-4 w-full" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              : data?.results.map((bug) => (
                  <TableRow key={bug._id ?? bug.bug_id}>
                    <TableCell className="font-mono text-xs text-gray-500">{bug.bug_id}</TableCell>
                    <TableCell className="max-w-xs">
                      <p className="truncate font-medium text-gray-900" title={bug.title}>{bug.title}</p>
                    </TableCell>
                    <TableCell>
                      <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", severityClass(bug.severity))}>
                        {bug.severity}
                      </span>
                    </TableCell>
                    <TableCell className="text-gray-600 text-xs">{bug.priority}</TableCell>
                    <TableCell>
                      <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", bugStatusClass(bug.status))}>
                        {bug.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-gray-600">{bug.bug_type}</TableCell>
                    <TableCell className="text-xs text-gray-600 max-w-24 truncate" title={bug.project}>{bug.project}</TableCell>
                    <TableCell className="text-xs text-gray-600">{bug.reporter}</TableCell>
                    <TableCell className="text-xs text-gray-600">{bug.assignee}</TableCell>
                    <TableCell className="text-xs text-gray-600">{bug.domain}</TableCell>
                    <TableCell className="text-xs text-gray-500 whitespace-nowrap">{formatDate(bug.created_at)}</TableCell>
                  </TableRow>
                ))}
          </TableBody>
        </Table>
        {data && (
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.count}
            onPageChange={setPage}
          />
        )}
      </Card>
    </div>
  );
}
