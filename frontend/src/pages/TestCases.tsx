import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { fetchTestCases } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { Skeleton } from "@/components/ui/Skeleton";
import { Pagination } from "@/components/ui/Pagination";
import { formatDate, tcStatusClass, cn } from "@/lib/utils";

const STATUSES = ["Passed", "Failed", "Skipped", "Pending", "Blocked"];
const TEAMS = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"];
const DOMAINS = ["Automotive", "Finance", "Healthcare", "Retail", "Industrial", "Aerospace", "Telecom"];
const AUTO_STATUSES = ["Automated", "Manual", "Semi-Automated"];

export function TestCases() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [team, setTeam] = useState("");
  const [domain, setDomain] = useState("");
  const [autoStatus, setAutoStatus] = useState("");
  const [search, setSearch] = useState("");

  const params: Record<string, string> = { page: String(page) };
  if (status) params.status = status;
  if (team) params.team = team;
  if (domain) params.domain = domain;
  if (autoStatus) params.automation_status = autoStatus;
  if (search) params.search = search;

  const { data, isLoading } = useQuery({
    queryKey: ["test-cases", page, status, team, domain, autoStatus, search],
    queryFn: () => fetchTestCases(params),
  });

  const handleFilter = () => setPage(1);

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Test Cases</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          {data ? `${data.count.toLocaleString()} total test cases` : "Loading..."}
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-48">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search test cases..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); handleFilter(); }}
                className="pl-9"
              />
            </div>
            <Select
              value={status}
              onChange={(e) => { setStatus(e.target.value); handleFilter(); }}
              placeholder="All Statuses"
              options={STATUSES.map((s) => ({ value: s, label: s }))}
              className="w-36"
            />
            <Select
              value={team}
              onChange={(e) => { setTeam(e.target.value); handleFilter(); }}
              placeholder="All Teams"
              options={TEAMS.map((t) => ({ value: t, label: `Team ${t}` }))}
              className="w-36"
            />
            <Select
              value={domain}
              onChange={(e) => { setDomain(e.target.value); handleFilter(); }}
              placeholder="All Domains"
              options={DOMAINS.map((d) => ({ value: d, label: d }))}
              className="w-44"
            />
            <Select
              value={autoStatus}
              onChange={(e) => { setAutoStatus(e.target.value); handleFilter(); }}
              placeholder="Automation"
              options={AUTO_STATUSES.map((s) => ({ value: s, label: s }))}
              className="w-40"
            />
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow className="bg-gray-50">
              <TableHead>TC ID</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Test Type</TableHead>
              <TableHead>Automation</TableHead>
              <TableHead>Project</TableHead>
              <TableHead>Assigned To</TableHead>
              <TableHead>Team</TableHead>
              <TableHead>Domain</TableHead>
              <TableHead>Date</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading
              ? Array.from({ length: 10 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 10 }).map((__, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                    ))}
                  </TableRow>
                ))
              : data?.results.map((tc) => (
                  <TableRow key={tc._id ?? tc.tc_id}>
                    <TableCell className="font-mono text-xs text-gray-500">{tc.tc_id}</TableCell>
                    <TableCell className="max-w-xs">
                      <p className="truncate font-medium text-gray-900" title={tc.name}>{tc.name}</p>
                    </TableCell>
                    <TableCell>
                      <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", tcStatusClass(tc.status))}>
                        {tc.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-gray-600">{tc.test_type}</TableCell>
                    <TableCell className="text-xs text-gray-600">{tc.automation_status}</TableCell>
                    <TableCell className="text-xs text-gray-600 max-w-24 truncate" title={tc.project}>{tc.project}</TableCell>
                    <TableCell className="text-xs text-gray-600">{tc.assigned_to}</TableCell>
                    <TableCell className="text-xs text-gray-600">{tc.team}</TableCell>
                    <TableCell className="text-xs text-gray-600">{tc.domain}</TableCell>
                    <TableCell className="text-xs text-gray-500 whitespace-nowrap">{formatDate(tc.created_at)}</TableCell>
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
