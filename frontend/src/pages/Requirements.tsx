import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchRequirements } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { Skeleton } from "@/components/ui/Skeleton";
import { Pagination } from "@/components/ui/Pagination";
import { priorityClass, cn } from "@/lib/utils";

const CATEGORIES = ["Functional", "Non-Functional", "Performance", "Security", "Usability", "Reliability"];
const STATUSES = ["Draft", "Review", "Approved", "Implemented", "Verified", "Rejected"];
const PRIORITIES = ["Critical", "High", "Medium", "Low"];

function reqStatusClass(status: string): string {
  const map: Record<string, string> = {
    Draft: "bg-gray-100 text-gray-600 border border-gray-200",
    Review: "bg-yellow-100 text-yellow-800 border border-yellow-200",
    Approved: "bg-green-100 text-green-800 border border-green-200",
    Implemented: "bg-blue-100 text-blue-800 border border-blue-200",
    Verified: "bg-teal-100 text-teal-800 border border-teal-200",
    Rejected: "bg-red-100 text-red-800 border border-red-200",
  };
  return map[status] ?? "bg-gray-100 text-gray-600 border border-gray-200";
}

export function Requirements() {
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");

  const params: Record<string, string> = { page: String(page) };
  if (category) params.category = category;
  if (status) params.status = status;
  if (priority) params.priority = priority;

  const { data, isLoading } = useQuery({
    queryKey: ["requirements", page, category, status, priority],
    queryFn: () => fetchRequirements(params),
  });

  const handleFilter = () => setPage(1);

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Requirements</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          {data ? `${data.count.toLocaleString()} total requirements` : "Loading..."}
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-wrap gap-3">
            <Select
              value={category}
              onChange={(e) => { setCategory(e.target.value); handleFilter(); }}
              placeholder="All Categories"
              options={CATEGORIES.map((c) => ({ value: c, label: c }))}
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

      {/* Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow className="bg-gray-50">
              <TableHead>Req ID</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Project</TableHead>
              <TableHead>Verifier</TableHead>
              <TableHead>Covered By</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? Array.from({ length: 10 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 8 }).map((__, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                    ))}
                  </TableRow>
                ))
              : data?.results.map((req) => (
                  <TableRow key={req._id ?? req.req_id}>
                    <TableCell className="font-mono text-xs text-gray-500">{req.req_id}</TableCell>
                    <TableCell className="max-w-xs">
                      <p className="truncate font-medium text-gray-900" title={req.name}>{req.name}</p>
                    </TableCell>
                    <TableCell className="text-xs text-gray-600">{req.category}</TableCell>
                    <TableCell>
                      <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", priorityClass(req.priority))}>
                        {req.priority}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", reqStatusClass(req.status))}>
                        {req.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-gray-600 max-w-32 truncate" title={req.project}>{req.project}</TableCell>
                    <TableCell className="text-xs text-gray-600">{req.verifier}</TableCell>
                    <TableCell className="text-xs text-gray-600">{req.covered_by}</TableCell>
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
