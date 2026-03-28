# Data Schema

All collections live in MongoDB database **`test_db`** at `localhost:27017`
(configurable via `MONGO_URI` and `DB_NAME` environment variables).

Every record has a `date` field (Python `datetime`) appended automatically by the uploader.
The `_id` field is MongoDB's auto-generated ObjectId and is never included in Excel files.

---

## Collections

### `employees` — 25 records

Base entity node. Every other collection links back to this via `*_employee_id` foreign-key fields.

| Field | Type | Values / Notes |
|---|---|---|
| `employee_id` | string | `EMP-001` ... `EMP-025` — unique primary key |
| `name` | string | Full name, e.g. `Alice Smith` |
| `email` | string | `firstname.lastname@techcorp.io` |
| `department` | string | `Engineering`, `QA`, `DevOps`, `Product`, `Security` |
| `role` | string | `Senior Engineer`, `Tech Lead`, `QA Engineer`, `Architect`, `DevOps Engineer`, `Product Manager`, `Security Analyst` |
| `team` | string | `Alpha`, `Beta`, `Gamma`, `Delta`, `Epsilon` |
| `location` | string | `London`, `New York`, `Berlin`, `Tokyo`, `Sydney`, `Toronto`, `Singapore` |
| `seniority` | string | `Junior`, `Mid`, `Senior`, `Principal`, `Staff` |
| `skills` | list (DB) / comma-string (Excel) | e.g. `["Python", "Docker", "pytest"]` |
| `db_status` | string | `active`, `inactive` |
| `date` | datetime | Appended by uploader at upload time |

**Graph role:** Source node for LEADS, ASSIGNED_TO, REPORTED, ASSIGNED_BUG, RESPONSIBLE_FOR edges.

---

### `projects` — 10 records

| Field | Type | Values / Notes |
|---|---|---|
| `project_id` | string | `PROJ-001` ... `PROJ-010` |
| `project_name` | string | e.g. `API Gateway`, `ML Inference Service`, `Cloud Migration` |
| `domain` | string | `Automotive`, `Finance`, `Healthcare`, `Retail`, `Industrial`, `Aerospace`, `Telecom` |
| `status` | string | `Active`, `Completed`, `On Hold`, `Planning`, `Cancelled` |
| `priority` | string | `Critical`, `High`, `Medium`, `Low` |
| `tech_stack` | list (DB) / comma-string (Excel) | e.g. `["Python", "FastAPI", "Docker"]` |
| `lead_employee_id` | string | FK -> `employees.employee_id` |
| `lead_name` | string | Denormalised name of lead employee |
| `team` | string | Inherited from lead employee |
| `start_date` | string | ISO date string |
| `end_date` | string | ISO date string |
| `git_hash` | string | Simulated 10-char hex commit hash |
| `db_status` | string | `active`, `inactive` |
| `date` | datetime | Appended by uploader |

**Graph role:** Target of LEADS edge; source of HAS_TEST_CASE, HAS_BUG, HAS_REQUIREMENT edges.

---

### `test_cases` — 100 records

| Field | Type | Values / Notes |
|---|---|---|
| `test_case_id` | string | `TC-001` ... `TC-100` |
| `test_case_name` | string | Auto-generated, e.g. `Validate_login_flow_042` |
| `domain` | string | Inherited from linked project |
| `project_id` | string | FK -> `projects.project_id` |
| `project_name` | string | Denormalised project name |
| `assigned_to_employee_id` | string | FK -> `employees.employee_id` |
| `assigned_to_name` | string | Denormalised assignee name |
| `parent_folder` | string | `Unit Tests`, `Integration Tests`, `E2E Tests`, `Performance Tests`, `Security Tests` |
| `path_folder` | string | Hierarchical path, e.g. `/Unit_Tests/login_flow` |
| `status` | string | `Passed`, `Failed`, `Skipped`, `Pending`, `Blocked` |
| `test_type` | string | `Functional`, `Regression`, `Smoke`, `Performance`, `Security`, `Integration` |
| `automation_status` | string | `Automated`, `Manual`, `In Progress` |
| `team` | string | Inherited from linked project |
| `git_hash` | string | Inherited from linked project |
| `db_status` | string | `active`, `inactive` |
| `date` | datetime | Appended by uploader |

**Graph role:** Target of HAS_TEST_CASE and ASSIGNED_TO edges; source of FOUND_BUG and COVERS edges.

---

### `bugs` — 150 records

| Field | Type | Values / Notes |
|---|---|---|
| `bug_id` | string | `BUG-001` ... `BUG-150` |
| `title` | string | Auto-generated, e.g. `Crash in login flow` |
| `description` | string | Short description referencing source test case |
| `severity` | string | `Critical`, `Major`, `Minor`, `Trivial` |
| `priority` | string | `P1`, `P2`, `P3`, `P4` |
| `status` | string | `Open`, `In Progress`, `Resolved`, `Closed`, `Reopened` |
| `bug_type` | string | `Functional`, `Performance`, `Security`, `UI`, `Data`, `Concurrency` |
| `project_id` | string | FK -> `projects.project_id` |
| `project_name` | string | Denormalised project name |
| `test_case_id` | string | FK -> `test_cases.test_case_id` (test that found this bug) |
| `test_case_name` | string | Denormalised test case name |
| `reporter_employee_id` | string | FK -> `employees.employee_id` |
| `reporter_name` | string | Denormalised reporter name |
| `assignee_employee_id` | string | FK -> `employees.employee_id` |
| `assignee_name` | string | Denormalised assignee name |
| `domain` | string | Inherited from linked project |
| `team` | string | Inherited from linked project |
| `git_hash` | string | Inherited from linked test case |
| `db_status` | string | `active`, `inactive` |
| `date` | datetime | Appended by uploader |

**Graph role:** Target of HAS_BUG, FOUND_BUG, REPORTED, ASSIGNED_BUG edges.

---

### `requirements` — 80 records

The only collection that uses **sync mode** upload. `db_status` is managed automatically
by the sync uploader to track record lifecycle across data refreshes.

| Field | Type | Values / Notes |
|---|---|---|
| `requirement_id` | string | `REQ-001` ... `REQ-080` |
| `requirement_name` | string | Auto-generated, e.g. `The system shall support user authentication` |
| `description` | string | Short description |
| `domain` | string | Inherited from linked project |
| `category` | string | `Functional`, `Non-Functional`, `Security`, `Performance`, `Compliance`, `Usability` |
| `priority` | string | `Must Have`, `Should Have`, `Could Have`, `Won't Have` |
| `status` | string | `Approved`, `Draft`, `Under Review`, `Rejected`, `Implemented` |
| `project_id` | string | FK -> `projects.project_id` |
| `project_name` | string | Denormalised project name |
| `verification_responsibility` | string | Denormalised name of verifier employee |
| `verifier_employee_id` | string | FK -> `employees.employee_id` |
| `covered_by_test_case_id` | string | FK -> `test_cases.test_case_id` |
| `covered_by_test_case_name` | string | Denormalised test case name |
| `team` | string | Inherited from linked project |
| `db_status` | string | **Managed by sync uploader** -- `added`, `updated`, `deleted` |
| `date` | datetime | Appended by uploader |

**Graph role:** Target of HAS_REQUIREMENT, COVERS, RESPONSIBLE_FOR edges.

---

## Graph Edges

10 directed relationship types. All edges derived from explicit FK fields in MongoDB documents.

| Relationship | Source | Target | FK Field |
|---|---|---|---|
| `(Employee)-[:LEADS]->(Project)` | `employee_id` | `project_id` | `projects.lead_employee_id` |
| `(Employee)-[:ASSIGNED_TO]->(TestCase)` | `employee_id` | `test_case_id` | `test_cases.assigned_to_employee_id` |
| `(Employee)-[:REPORTED]->(Bug)` | `employee_id` | `bug_id` | `bugs.reporter_employee_id` |
| `(Employee)-[:ASSIGNED_BUG]->(Bug)` | `employee_id` | `bug_id` | `bugs.assignee_employee_id` |
| `(Employee)-[:RESPONSIBLE_FOR]->(Requirement)` | `employee_id` | `requirement_id` | `requirements.verifier_employee_id` |
| `(Project)-[:HAS_TEST_CASE]->(TestCase)` | `project_id` | `test_case_id` | `test_cases.project_id` |
| `(Project)-[:HAS_BUG]->(Bug)` | `project_id` | `bug_id` | `bugs.project_id` |
| `(Project)-[:HAS_REQUIREMENT]->(Requirement)` | `project_id` | `requirement_id` | `requirements.project_id` |
| `(TestCase)-[:FOUND_BUG]->(Bug)` | `test_case_id` | `bug_id` | `bugs.test_case_id` |
| `(TestCase)-[:COVERS]->(Requirement)` | `test_case_id` | `requirement_id` | `requirements.covered_by_test_case_id` |

**Actual edge counts (from build_graph.py run):**

| Relationship | Count |
|---|---|
| LEADS | 10 |
| ASSIGNED_TO | 100 |
| REPORTED | 145 |
| ASSIGNED_BUG | 150 |
| RESPONSIBLE_FOR | 80 |
| HAS_TEST_CASE | 100 |
| HAS_BUG | 150 |
| HAS_REQUIREMENT | 80 |
| FOUND_BUG | 150 |
| COVERS | 80 |
| **Total** | **1045** |

---

## Cross-Collection Join Fields

Fields shared across multiple collections that enable joins in the Django dashboard and graph edges in GraphRAG.

| Field | Collections | Purpose |
|---|---|---|
| `domain` | all 5 | Group / filter by business domain |
| `team` | all 5 | Group / filter by team |
| `db_status` | all 5 | Record lifecycle tracking |
| `date` | all 5 | Temporal ordering |
| `project_id` | projects, test_cases, bugs, requirements | Core structural join |
| `employee_id` (via aliases) | employees + all 4 others | Employee linkage |
| `test_case_id` | test_cases, bugs, requirements | Test linkage |
| `git_hash` | projects, test_cases, bugs | Code version linkage |

---

## Denormalised Fields

To avoid runtime joins in MongoDB (which has no native join), several name fields are
duplicated denormalised across collections:

| Denormalised field | Source field | Where stored |
|---|---|---|
| `lead_name` | `employees.name` | `projects` |
| `assigned_to_name` | `employees.name` | `test_cases` |
| `reporter_name` | `employees.name` | `bugs` |
| `assignee_name` | `employees.name` | `bugs` |
| `verification_responsibility` | `employees.name` | `requirements` |
| `project_name` | `projects.project_name` | `test_cases`, `bugs`, `requirements` |
| `test_case_name` | `test_cases.test_case_name` | `bugs`, `requirements` |

---

---

### `users` — auth collection (no fixed count)

Managed by `dashboard/auth_views.py`. Used for JWT authentication on the Django REST API.

| Field | Type | Notes |
|---|---|---|
| `username` | string | Unique login name |
| `password_hash` | string | bcrypt hash — never stored in plain text |
| `role` | string | `admin` or `viewer` |
| `created_at` | string | ISO datetime |

Create users via Django shell:
```python
from dashboard.auth_views import create_user
create_user("admin", "changeme", role="admin")
create_user("readonly", "pass", role="viewer")
```

Or via the REST API (admin token required):
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"username": "newuser", "password": "secret", "role": "viewer"}'
```

The React frontend login page authenticates against this collection via `/api/auth/login/`.

---

## Enumerations

```
DOMAINS            : Automotive, Finance, Healthcare, Retail, Industrial, Aerospace, Telecom
TEAMS              : Alpha, Beta, Gamma, Delta, Epsilon
DEPARTMENTS        : Engineering, QA, DevOps, Product, Security
SENIORITIES        : Junior, Mid, Senior, Principal, Staff
LOCATIONS          : London, New York, Berlin, Tokyo, Sydney, Toronto, Singapore

PROJECT_STATUSES   : Active, Completed, On Hold, Planning, Cancelled
PROJECT_PRIORITIES : Critical, High, Medium, Low

TC_STATUSES        : Passed, Failed, Skipped, Pending, Blocked
TC_TYPES           : Functional, Regression, Smoke, Performance, Security, Integration
AUTOMATION         : Automated, Manual, In Progress

BUG_SEVERITIES     : Critical, Major, Minor, Trivial
BUG_PRIORITIES     : P1, P2, P3, P4
BUG_STATUSES       : Open, In Progress, Resolved, Closed, Reopened
BUG_TYPES          : Functional, Performance, Security, UI, Data, Concurrency

REQ_CATEGORIES     : Functional, Non-Functional, Security, Performance, Compliance, Usability
REQ_PRIORITIES     : Must Have, Should Have, Could Have, Won't Have
REQ_STATUSES       : Approved, Draft, Under Review, Rejected, Implemented
```
