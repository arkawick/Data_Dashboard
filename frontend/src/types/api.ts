// ---- Auth ----
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  username: string;
  role: string;
}

export interface RefreshResponse {
  access_token: string;
}

// ---- FastAPI Health ----
export interface HealthResponse {
  status: string;
  chunks_loaded: number;
  retriever_type: string;
  neo4j_available: boolean;
}

// ---- Graph Stats ----
export interface GraphStatsResponse {
  nodes: number;
  edges: number;
  node_types: Record<string, number>;
  edge_types: Record<string, number>;
}

// ---- Django Stats ----
export interface StatsResponse {
  counts: {
    employees: number;
    projects: number;
    test_cases: number;
    bugs: number;
    requirements: number;
  };
  bug_by_severity: Record<string, number>;
  tc_by_status: Record<string, number>;
}

// ---- Pagination ----
export interface PaginatedResponse<T> {
  count: number;
  page: number;
  pages: number;
  results: T[];
}

// ---- Bug ----
export interface Bug {
  _id: string;
  bug_id: string;
  title: string;
  severity: "Critical" | "Major" | "Minor" | "Trivial";
  priority: string;
  status: "Open" | "In Progress" | "Resolved" | "Closed" | "Reopened";
  bug_type: string;
  project: string;
  reporter: string;
  assignee: string;
  domain: string;
  created_at: string;
}

// ---- Test Case ----
export interface TestCase {
  _id: string;
  tc_id: string;
  name: string;
  status: "Passed" | "Failed" | "Skipped" | "Pending" | "Blocked";
  test_type: string;
  automation_status: string;
  project: string;
  assigned_to: string;
  domain: string;
  team: string;
  created_at: string;
}

// ---- Project ----
export interface Project {
  _id: string;
  project_id: string;
  name: string;
  domain: string;
  status: "Active" | "Completed" | "On Hold" | "Planning" | "Cancelled";
  priority: string;
  lead_name: string;
  tech_stack: string[];
  description: string;
  start_date: string;
  end_date: string;
  budget: number;
  team: string;
}

// ---- Requirement ----
export interface Requirement {
  _id: string;
  req_id: string;
  name: string;
  category: string;
  priority: string;
  status: string;
  project: string;
  verifier: string;
  covered_by: string;
  created_at: string;
}

// ---- Employee ----
export interface Employee {
  _id: string;
  emp_id: string;
  name: string;
  role: string;
  department: string;
  team: string;
  seniority: "Junior" | "Mid" | "Senior" | "Principal" | "Staff";
  skills: string[];
  email: string;
  joined_at: string;
}

// ---- Query ----
export interface QueryRequest {
  question: string;
  top_k: number;
  backend: string;
}

export interface Chunk {
  id: string;
  type: string;
  text: string;
  score?: number;
}

export interface QueryResponse {
  question: string;
  backend: string;
  chunks_retrieved: number;
  chunks: Chunk[];
  answer: string;
  graph_paths?: string[][];
}

// ---- Pipeline ----
export interface PipelineRebuildResponse {
  task_id: string;
  status: string;
}

export interface PipelineStatusResponse {
  task_id: string;
  status: string;
  result: unknown;
}

// ---- Chunk Search ----
export interface ChunkSearchResponse {
  chunks: Chunk[];
}
