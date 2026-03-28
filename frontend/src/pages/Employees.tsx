import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Mail } from "lucide-react";
import { fetchEmployees } from "@/lib/api";
import type { Employee } from "@/types/api";
import { Card, CardContent } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { Pagination } from "@/components/ui/Pagination";
import { seniorityClass, getInitials, avatarColor, cn } from "@/lib/utils";

const DEPARTMENTS = ["Engineering", "QA", "DevOps", "Product", "Security"];
const TEAMS = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"];
const SENIORITIES = ["Junior", "Mid", "Senior", "Principal", "Staff"];

function EmployeeCard({ emp }: { emp: Employee }) {
  const initials = getInitials(emp.name);
  const bgColor = avatarColor(emp.name);

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow p-5">
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center text-white font-semibold text-sm shrink-0", bgColor)}>
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="font-semibold text-gray-900 text-sm truncate">{emp.name}</h3>
              <p className="text-xs text-gray-500 truncate">{emp.role}</p>
            </div>
            <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium shrink-0", seniorityClass(emp.seniority))}>
              {emp.seniority}
            </span>
          </div>

          <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-gray-500">
            <span className="bg-gray-100 px-2 py-0.5 rounded">{emp.department}</span>
            <span className="bg-gray-100 px-2 py-0.5 rounded">Team {emp.team}</span>
          </div>

          {emp.email && (
            <div className="flex items-center gap-1.5 mt-2 text-xs text-gray-400">
              <Mail className="h-3 w-3" />
              <span className="truncate">{emp.email}</span>
            </div>
          )}

          {emp.skills && emp.skills.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {emp.skills.slice(0, 5).map((skill) => (
                <span key={skill} className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded border border-blue-100">
                  {skill}
                </span>
              ))}
              {emp.skills.length > 5 && (
                <span className="text-xs text-gray-400">+{emp.skills.length - 5}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function Employees() {
  const [page, setPage] = useState(1);
  const [department, setDepartment] = useState("");
  const [team, setTeam] = useState("");
  const [seniority, setSeniority] = useState("");

  const params: Record<string, string> = { page: String(page) };
  if (department) params.department = department;
  if (team) params.team = team;
  if (seniority) params.seniority = seniority;

  const { data, isLoading } = useQuery({
    queryKey: ["employees", page, department, team, seniority],
    queryFn: () => fetchEmployees(params),
  });

  const handleFilter = () => setPage(1);

  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Employees</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          {data ? `${data.count.toLocaleString()} total employees` : "Loading..."}
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="flex flex-wrap gap-3">
            <Select
              value={department}
              onChange={(e) => { setDepartment(e.target.value); handleFilter(); }}
              placeholder="All Departments"
              options={DEPARTMENTS.map((d) => ({ value: d, label: d }))}
              className="w-44"
            />
            <Select
              value={team}
              onChange={(e) => { setTeam(e.target.value); handleFilter(); }}
              placeholder="All Teams"
              options={TEAMS.map((t) => ({ value: t, label: `Team ${t}` }))}
              className="w-36"
            />
            <Select
              value={seniority}
              onChange={(e) => { setSeniority(e.target.value); handleFilter(); }}
              placeholder="All Seniorities"
              options={SENIORITIES.map((s) => ({ value: s, label: s }))}
              className="w-40"
            />
          </div>
        </CardContent>
      </Card>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full rounded-xl" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data?.results.map((emp) => (
              <EmployeeCard key={emp._id ?? emp.emp_id} emp={emp} />
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
