import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

// Bug severity badge colors
export function severityClass(severity: string): string {
  const map: Record<string, string> = {
    Critical: "bg-red-100 text-red-800 border border-red-200",
    Major: "bg-orange-100 text-orange-800 border border-orange-200",
    Minor: "bg-yellow-100 text-yellow-800 border border-yellow-200",
    Trivial: "bg-gray-100 text-gray-700 border border-gray-200",
  };
  return map[severity] ?? "bg-gray-100 text-gray-700 border border-gray-200";
}

// Bug status badge colors
export function bugStatusClass(status: string): string {
  const map: Record<string, string> = {
    Open: "bg-red-100 text-red-800 border border-red-200",
    "In Progress": "bg-blue-100 text-blue-800 border border-blue-200",
    Resolved: "bg-green-100 text-green-800 border border-green-200",
    Closed: "bg-gray-100 text-gray-700 border border-gray-200",
    Reopened: "bg-orange-100 text-orange-800 border border-orange-200",
  };
  return map[status] ?? "bg-gray-100 text-gray-700 border border-gray-200";
}

// TC status badge colors
export function tcStatusClass(status: string): string {
  const map: Record<string, string> = {
    Passed: "bg-green-100 text-green-800 border border-green-200",
    Failed: "bg-red-100 text-red-800 border border-red-200",
    Skipped: "bg-gray-100 text-gray-700 border border-gray-200",
    Pending: "bg-yellow-100 text-yellow-800 border border-yellow-200",
    Blocked: "bg-purple-100 text-purple-800 border border-purple-200",
  };
  return map[status] ?? "bg-gray-100 text-gray-700 border border-gray-200";
}

// Project status badge colors
export function projectStatusClass(status: string): string {
  const map: Record<string, string> = {
    Active: "bg-green-100 text-green-800 border border-green-200",
    Completed: "bg-blue-100 text-blue-800 border border-blue-200",
    "On Hold": "bg-yellow-100 text-yellow-800 border border-yellow-200",
    Planning: "bg-purple-100 text-purple-800 border border-purple-200",
    Cancelled: "bg-red-100 text-red-800 border border-red-200",
  };
  return map[status] ?? "bg-gray-100 text-gray-700 border border-gray-200";
}

// Seniority badge colors
export function seniorityClass(seniority: string): string {
  const map: Record<string, string> = {
    Junior: "bg-blue-100 text-blue-800 border border-blue-200",
    Mid: "bg-teal-100 text-teal-800 border border-teal-200",
    Senior: "bg-purple-100 text-purple-800 border border-purple-200",
    Principal: "bg-orange-100 text-orange-800 border border-orange-200",
    Staff: "bg-red-100 text-red-800 border border-red-200",
  };
  return map[seniority] ?? "bg-gray-100 text-gray-700 border border-gray-200";
}

// Priority badge colors
export function priorityClass(priority: string): string {
  const map: Record<string, string> = {
    Critical: "bg-red-100 text-red-800 border border-red-200",
    High: "bg-orange-100 text-orange-800 border border-orange-200",
    Medium: "bg-yellow-100 text-yellow-800 border border-yellow-200",
    Low: "bg-gray-100 text-gray-600 border border-gray-200",
  };
  return map[priority] ?? "bg-gray-100 text-gray-700 border border-gray-200";
}

export function truncate(str: string, length = 60): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + "...";
}

export function getInitials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

export function avatarColor(name: string): string {
  const colors = [
    "bg-blue-500",
    "bg-purple-500",
    "bg-green-500",
    "bg-orange-500",
    "bg-pink-500",
    "bg-teal-500",
    "bg-red-500",
    "bg-indigo-500",
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}
