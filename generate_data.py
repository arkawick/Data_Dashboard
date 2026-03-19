"""
generate_data.py
Generates randomized, GraphRAG-ready data across 5 MongoDB collections
with shared foreign keys to enable graph relationships.

Collections created:
  employees   (25)  - base entity node
  projects    (10)  - linked to employees via lead_employee_id
  test_cases  (100) - linked to projects (project_id) and employees (assigned_to_employee_id)
  bugs        (150) - linked to test_cases (test_case_id), projects, and employees
  requirements(80)  - linked to projects, test_cases, and employees

Graph edges this enables:
  Employee  --LEADS-->           Project
  Employee  --ASSIGNED_TO-->     TestCase
  Employee  --REPORTED_BY-->     Bug
  Employee  --ASSIGNED_TO-->     Bug
  Employee  --RESPONSIBLE_FOR--> Requirement
  Project   --HAS_TEST_CASE-->   TestCase
  Project   --HAS_BUG-->         Bug
  Project   --HAS_REQUIREMENT--> Requirement
  TestCase  --FOUND_BUG-->       Bug
  TestCase  --COVERS-->          Requirement

Run: python generate_data.py
"""

import random
import string
from datetime import datetime, timedelta
from pymongo import MongoClient

# ── Config ────────────────────────────────────────────────────────────────────
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "test_db"

# ── Lookup tables ─────────────────────────────────────────────────────────────
DOMAINS       = ["Automotive", "Finance", "Healthcare", "Retail", "Industrial", "Aerospace", "Telecom"]
TEAMS         = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]
DEPARTMENTS   = ["Engineering", "QA", "DevOps", "Product", "Security"]
ROLES         = ["Engineer", "Senior Engineer", "Tech Lead", "QA Engineer", "DevOps Engineer", "Architect", "Product Manager"]
SENIORITIES   = ["Junior", "Mid", "Senior", "Principal", "Staff"]
LOCATIONS     = ["New York", "London", "Berlin", "Tokyo", "Sydney", "Bangalore", "Toronto"]
SKILLS_POOL   = ["Python", "Java", "C++", "JavaScript", "MongoDB", "Docker", "Kubernetes",
                 "CI/CD", "Selenium", "pytest", "JUnit", "REST API", "GraphQL", "Spark", "Redis"]
TECH_STACKS   = ["Python/FastAPI", "Java/Spring", "Node.js/Express", "Go/gRPC",
                 "C++/Qt", "React/TypeScript", "Vue.js/Django"]

PROJECT_NAMES = [
    "Platform Modernization", "API Gateway", "Data Pipeline", "Auth Service Overhaul",
    "Mobile SDK", "Analytics Engine", "Security Audit", "Cloud Migration",
    "Real-time Monitoring", "ML Inference Service"
]

PROJECT_STATUSES   = ["Active", "Completed", "On Hold", "Planning", "Cancelled"]
PROJECT_PRIORITIES = ["Critical", "High", "Medium", "Low"]

TC_STATUSES          = ["Passed", "Failed", "Skipped", "Pending", "Blocked"]
TC_TYPES             = ["Functional", "Regression", "Smoke", "Performance", "Security", "Integration"]
AUTOMATION_STATUSES  = ["Automated", "Manual", "In Progress"]
PARENT_FOLDERS       = ["Unit Tests", "Integration Tests", "E2E Tests", "Performance Tests", "Security Tests"]
TC_VERBS             = ["Validate", "Verify", "Test", "Check", "Assert", "Ensure"]
TC_SUBJECTS          = [
    "login_flow", "data_ingestion", "api_response", "ui_rendering", "auth_token",
    "database_query", "cache_invalidation", "error_handling", "retry_logic",
    "rate_limiting", "session_management", "file_upload", "export_function",
    "search_feature", "pagination_logic"
]

BUG_SEVERITIES = ["Critical", "Major", "Minor", "Trivial"]
BUG_PRIORITIES = ["P1", "P2", "P3", "P4"]
BUG_STATUSES   = ["Open", "In Progress", "Resolved", "Closed", "Reopened"]
BUG_TYPES      = ["Functional", "Performance", "Security", "UI", "Data", "Concurrency"]
BUG_PREFIXES   = [
    "Crash in", "Memory leak in", "Incorrect output from", "Timeout in",
    "Race condition in", "Null pointer in", "Missing validation in",
    "Broken redirect in", "Data corruption in", "UI glitch in",
    "Performance degradation in", "Auth bypass in"
]

REQ_CATEGORIES = ["Functional", "Non-Functional", "Security", "Performance", "Compliance", "Usability"]
REQ_PRIORITIES = ["Must Have", "Should Have", "Could Have", "Won't Have"]
REQ_STATUSES   = ["Approved", "Draft", "Under Review", "Rejected", "Implemented"]
REQ_SUBJECTS   = [
    "user authentication", "data encryption", "API response time", "error logging",
    "access control", "audit trail", "data backup", "session timeout",
    "input validation", "rate limiting", "multi-factor authentication",
    "GDPR compliance", "load balancing", "monitoring dashboard", "automated alerts"
]

FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank",
               "Iris", "Jack", "Karen", "Leo", "Mia", "Noah", "Olivia", "Paul",
               "Quinn", "Rachel", "Sam", "Tina", "Uma", "Victor", "Wendy", "Xander", "Yara"]
LAST_NAMES  = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
               "Davis", "Wilson", "Taylor", "Anderson", "Thomas", "Jackson", "White",
               "Harris", "Martin", "Thompson", "Moore", "Young", "Allen"]


# ── Helpers ───────────────────────────────────────────────────────────────────
def rand_date(start_days_ago=365, end_days_ago=0):
    delta = random.randint(end_days_ago, start_days_ago)
    return datetime.now() - timedelta(days=delta)

def rand_git_hash():
    return ''.join(random.choices(string.hexdigits[:16], k=10))

def fmt_id(prefix, n, width=3):
    return f"{prefix}-{str(n).zfill(width)}"


# ── Generators ────────────────────────────────────────────────────────────────
def gen_employees(n=25):
    records, used = [], set()
    for i in range(1, n + 1):
        while True:
            fn, ln = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
            name = f"{fn} {ln}"
            if name not in used:
                used.add(name)
                break
        records.append({
            "employee_id":  fmt_id("EMP", i),
            "name":         name,
            "email":        f"{fn.lower()}.{ln.lower()}@techcorp.io",
            "department":   random.choice(DEPARTMENTS),
            "role":         random.choice(ROLES),
            "team":         random.choice(TEAMS),
            "location":     random.choice(LOCATIONS),
            "seniority":    random.choice(SENIORITIES),
            "skills":       random.sample(SKILLS_POOL, k=random.randint(2, 5)),
            "date":         rand_date(500, 200),
            "db_status":    random.choices(["active", "inactive"], weights=[85, 15])[0],
        })
    return records


def gen_projects(n=10, employees=None):
    records = []
    for i in range(1, n + 1):
        lead  = random.choice(employees) if employees else None
        start = rand_date(400, 100)
        end   = start + timedelta(days=random.randint(90, 365))
        records.append({
            "project_id":       fmt_id("PROJ", i),
            "project_name":     PROJECT_NAMES[i - 1],
            "domain":           random.choice(DOMAINS),
            "status":           random.choice(PROJECT_STATUSES),
            "priority":         random.choice(PROJECT_PRIORITIES),
            "tech_stack":       random.sample(TECH_STACKS, k=random.randint(1, 3)),
            "lead_employee_id": lead["employee_id"] if lead else None,
            "lead_name":        lead["name"]        if lead else None,
            "team":             lead["team"]         if lead else random.choice(TEAMS),
            "start_date":       start,
            "end_date":         end,
            "git_hash":         rand_git_hash(),
            "date":             rand_date(100, 0),
            "db_status":        random.choices(["active", "inactive"], weights=[85, 15])[0],
        })
    return records


def gen_test_cases(n=100, projects=None, employees=None):
    records = []
    for i in range(1, n + 1):
        proj     = random.choice(projects)  if projects  else None
        assignee = random.choice(employees) if employees else None
        name     = f"{random.choice(TC_VERBS)}_{random.choice(TC_SUBJECTS)}_{fmt_id('', i, 3).strip('-')}"
        records.append({
            "test_case_id":            fmt_id("TC", i),
            "test_case_name":          name,
            "domain":                  proj["domain"]      if proj else random.choice(DOMAINS),
            "project_id":              proj["project_id"]  if proj else None,
            "project_name":            proj["project_name"] if proj else None,
            "assigned_to_employee_id": assignee["employee_id"] if assignee else None,
            "assigned_to_name":        assignee["name"]        if assignee else None,
            "parent_folder":           random.choice(PARENT_FOLDERS),
            "path_folder":             f"/{random.choice(PARENT_FOLDERS).replace(' ', '_')}/{random.choice(TC_SUBJECTS)}",
            "status":                  random.choice(TC_STATUSES),
            "test_type":               random.choice(TC_TYPES),
            "automation_status":       random.choice(AUTOMATION_STATUSES),
            "team":                    proj["team"]      if proj else random.choice(TEAMS),
            "git_hash":                proj["git_hash"]  if proj else rand_git_hash(),
            "date":                    rand_date(90, 0),
            "db_status":               random.choices(["active", "inactive"], weights=[90, 10])[0],
        })
    return records


def gen_bugs(n=150, projects=None, test_cases=None, employees=None):
    records = []
    for i in range(1, n + 1):
        proj     = random.choice(projects)   if projects   else None
        tc       = random.choice(test_cases) if test_cases else None
        reporter = random.choice(employees)  if employees  else None
        assignee = random.choice(employees)  if employees  else None
        component = random.choice(TC_SUBJECTS).replace("_", " ")
        records.append({
            "bug_id":                  fmt_id("BUG", i),
            "title":                   f"{random.choice(BUG_PREFIXES)} {component}",
            "description":             f"Found during {tc['test_case_name'] if tc else 'manual testing'}",
            "severity":                random.choice(BUG_SEVERITIES),
            "priority":                random.choice(BUG_PRIORITIES),
            "status":                  random.choice(BUG_STATUSES),
            "bug_type":                random.choice(BUG_TYPES),
            "project_id":              proj["project_id"]  if proj else None,
            "project_name":            proj["project_name"] if proj else None,
            "test_case_id":            tc["test_case_id"]   if tc else None,
            "test_case_name":          tc["test_case_name"] if tc else None,
            "reporter_employee_id":    reporter["employee_id"] if reporter else None,
            "reporter_name":           reporter["name"]        if reporter else None,
            "assignee_employee_id":    assignee["employee_id"] if assignee else None,
            "assignee_name":           assignee["name"]        if assignee else None,
            "domain":                  proj["domain"] if proj else random.choice(DOMAINS),
            "team":                    proj["team"]   if proj else random.choice(TEAMS),
            "git_hash":                tc["git_hash"] if tc else rand_git_hash(),
            "date":                    rand_date(60, 0),
            "db_status":               random.choices(["active", "inactive"], weights=[80, 20])[0],
        })
    return records


def gen_requirements(n=80, projects=None, test_cases=None, employees=None):
    records = []
    for i in range(1, n + 1):
        proj  = random.choice(projects)   if projects   else None
        tc    = random.choice(test_cases) if test_cases else None
        owner = random.choice(employees)  if employees  else None
        subj  = random.choice(REQ_SUBJECTS)
        records.append({
            "requirement_id":              fmt_id("REQ", i),
            "requirement_name":            f"The system shall support {subj}",
            "description":                 f"Requirement for {proj['project_name'] if proj else 'the system'} to implement {subj}",
            "domain":                      proj["domain"]       if proj else random.choice(DOMAINS),
            "category":                    random.choice(REQ_CATEGORIES),
            "priority":                    random.choice(REQ_PRIORITIES),
            "status":                      random.choice(REQ_STATUSES),
            "project_id":                  proj["project_id"]   if proj else None,
            "project_name":                proj["project_name"] if proj else None,
            "verification_responsibility": owner["name"]        if owner else None,
            "verifier_employee_id":        owner["employee_id"] if owner else None,
            "covered_by_test_case_id":     tc["test_case_id"]   if tc else None,
            "covered_by_test_case_name":   tc["test_case_name"] if tc else None,
            "team":                        proj["team"] if proj else random.choice(TEAMS),
            "date":                        rand_date(120, 0),
            "db_status":                   random.choices(["active", "inactive", "deleted"], weights=[70, 20, 10])[0],
        })
    return records


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    old_cols = ["employees", "projects", "test_cases", "bugs", "requirements",
                "metadata", "powerbi", "powerbi_prio2"]
    print("Dropping old collections...")
    for col in old_cols:
        db[col].drop()

    print("Generating employees  (25)...")
    employees = gen_employees(25)
    db["employees"].insert_many(employees)

    print("Generating projects   (10)...")
    projects = gen_projects(10, employees)
    db["projects"].insert_many(projects)

    print("Generating test_cases (100)...")
    test_cases = gen_test_cases(100, projects, employees)
    db["test_cases"].insert_many(test_cases)

    print("Generating bugs       (150)...")
    bugs = gen_bugs(150, projects, test_cases, employees)
    db["bugs"].insert_many(bugs)

    print("Generating requirements (80)...")
    requirements = gen_requirements(80, projects, test_cases, employees)
    db["requirements"].insert_many(requirements)

    print("\n-- Collections in test_db --")
    for col in ["employees", "projects", "test_cases", "bugs", "requirements"]:
        print(f"  {col:<15} {db[col].count_documents({})} records")

    print("\n-- Graph edges available --")
    edges = [
        ("Employee",  "LEADS",            "Project",     "lead_employee_id -> employee_id"),
        ("Employee",  "ASSIGNED_TO",      "TestCase",    "assigned_to_employee_id -> employee_id"),
        ("Employee",  "REPORTED_BUG",     "Bug",         "reporter_employee_id -> employee_id"),
        ("Employee",  "ASSIGNED_BUG",     "Bug",         "assignee_employee_id -> employee_id"),
        ("Employee",  "RESPONSIBLE_FOR",  "Requirement", "verifier_employee_id -> employee_id"),
        ("Project",   "HAS_TEST_CASE",    "TestCase",    "project_id -> project_id"),
        ("Project",   "HAS_BUG",          "Bug",         "project_id -> project_id"),
        ("Project",   "HAS_REQUIREMENT",  "Requirement", "project_id -> project_id"),
        ("TestCase",  "FOUND_BUG",        "Bug",         "test_case_id -> test_case_id"),
        ("TestCase",  "COVERS",           "Requirement", "test_case_id -> covered_by_test_case_id"),
    ]
    for src, rel, dst, keys in edges:
        print(f"  ({src})-[:{rel}]->({dst})  via {keys}")

    print("\nDone.")


if __name__ == "__main__":
    main()
