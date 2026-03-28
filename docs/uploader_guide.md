# Uploader Guide

Three ways to get data into MongoDB. Each suits a different workflow.

---

## Overview

| Method | Script | When to use |
|---|---|---|
| Direct insert | `generate_data.py` | Dev reset, quick re-seed, no Excel needed |
| GUI uploader | `uploader.py` | Manual uploads with visual feedback |
| CLI batch | `Uploader_Scripts/Base_Uploader_Scripts/upload_all.py` | Automation, CI, scripting |
| CLI individual | `Uploader_Scripts/Base_Uploader_Scripts/*_to_db.py` | Upload one collection at a time |
| Comp scripts | `Uploader_Scripts/Comp_Uploader_Scripts/*_comp.py` | Sync changes, preserve history via db_status |

---

## 1. Direct insert — `generate_data.py`

Bypasses Excel entirely. Generates fresh randomized data and inserts straight into MongoDB.

```bash
python generate_data.py
```

**What it does:**
- Drops and re-creates all 5 collections: `employees`, `projects`, `test_cases`, `bugs`, `requirements`
- Inserts fresh randomized records with consistent FK relationships across collections
- Prints a summary of inserted counts and available graph edges

**When to use:**
- Fastest way to reset to a clean state during development
- When you don't need the Excel pipeline
- Before running the GraphRAG pipeline from scratch

---

## 2. Generating Excel files — `generate_excel.py`

```bash
python generate_excel.py
```

Writes 5 styled `.xlsx` files into `input_folder/`:

| File | Sheet | Collection |
|---|---|---|
| `employees_data.xlsx` | `Employees` | `employees` |
| `projects_data.xlsx` | `Projects` | `projects` |
| `test_cases_data.xlsx` | `TestCases` | `test_cases` |
| `bugs_data.xlsx` | `Bugs` | `bugs` |
| `requirements_data.xlsx` | `Requirements` | `requirements` |

**Notes:**
- List fields (`skills`, `tech_stack`) are written as comma-separated strings in Excel
- The `date` upload timestamp is **not** included in Excel — it is appended by the uploader at upload time
- The `requirements` Excel file does **not** include `db_status` — that field is managed by the sync uploader

---

## 3. GUI uploader — `uploader.py`

Tkinter GUI. Reads Excel files and uploads to MongoDB.

```bash
python uploader.py
```

**Steps:**
1. Run `python generate_excel.py` first to populate `input_folder/`
2. Run `python uploader.py`
3. Leave the path field blank (defaults to `input_folder/`) or browse to a specific file or folder
4. Click **Start Upload**
5. Watch the log panel for per-collection results

**How routing works:**
The uploader matches each Excel filename against the patterns in `config.py` to decide which
MongoDB collection and sheet to target, and whether to use insert or sync mode.

---

## 4. CLI batch uploader — `upload_all.py`

Uploads all 5 Excel files from `input_folder/` in one command. No GUI.

```bash
python Uploader_Scripts/Base_Uploader_Scripts/upload_all.py
```

Useful for automation or scripting.

---

## 5. CLI individual uploaders (Base scripts)

Clear the collection and re-insert all rows from Excel. No history preserved.

```bash
python Uploader_Scripts/Base_Uploader_Scripts/employees_to_db.py
python Uploader_Scripts/Base_Uploader_Scripts/projects_to_db.py
python Uploader_Scripts/Base_Uploader_Scripts/test_cases_to_db.py
python Uploader_Scripts/Base_Uploader_Scripts/bugs_to_db.py
python Uploader_Scripts/Base_Uploader_Scripts/requirements_to_db.py
```

Each script:
1. Reads the corresponding Excel file from `input_folder/`
2. Calls `delete_many({})` on the collection
3. Calls `insert_many()` with all rows + current timestamp as `date`

---

## 6. Comp (compare-and-sync) uploaders

Compare incoming Excel rows against existing MongoDB records using the unique ID field.
Tracks record lifecycle via `db_status` without physically deleting rows.

```bash
python Uploader_Scripts/Comp_Uploader_Scripts/employees_comp.py
python Uploader_Scripts/Comp_Uploader_Scripts/projects_comp.py
python Uploader_Scripts/Comp_Uploader_Scripts/test_cases_comp.py
python Uploader_Scripts/Comp_Uploader_Scripts/bugs_comp.py
python Uploader_Scripts/Comp_Uploader_Scripts/requirements_comp.py
```

**How it works:**

| Scenario | Action | `db_status` set to |
|---|---|---|
| Row exists in Excel AND in MongoDB, data changed | Update document | `updated` |
| Row exists in Excel AND in MongoDB, no change | No action | unchanged |
| Row is in Excel but NOT in MongoDB | Insert new document | `added` |
| Row is in MongoDB but NOT in Excel | Mark as soft-deleted | `deleted` |

**Unique field per collection:**

| Collection | Unique field |
|---|---|
| employees | `employee_id` |
| projects | `project_id` |
| test_cases | `test_case_id` |
| bugs | `bug_id` |
| requirements | `requirement_id` |

Rows marked `deleted` are **not** physically removed — they remain in MongoDB with `db_status = "deleted"`.
This makes the comp script the recommended approach when you need to audit changes over time.

---

## Upload modes summary

| Mode | Collection cleared? | db_status managed? | History preserved? |
|---|---|---|---|
| insert (base scripts) | Yes | No | No |
| sync (comp scripts) | No | Yes (added/updated/deleted) | Yes |

The `requirements` collection is the only one configured for sync mode in `config.py`
and the GUI uploader routes it accordingly.

---

## config.py — routing table

`config.py` at the project root controls how filenames map to collections:

```python
FILE_PATTERNS = [
    {
        "pattern":      r"employees_data",   # regex matched against lowercase filename
        "collection":   "employees",         # MongoDB collection name
        "sheet_regex":  r"Employees",        # regex matched against Excel sheet names
        "header_row":   1,                   # row number of the column headers
        "unique_field": "employee_id",       # used by comp scripts for matching
        "sync":         False,               # False = insert mode, True = sync mode
    },
    {
        "pattern":      r"projects_data",
        "collection":   "projects",
        "sheet_regex":  r"Projects",
        "header_row":   1,
        "unique_field": "project_id",
        "sync":         False,
    },
    {
        "pattern":      r"test_cases_data",
        "collection":   "test_cases",
        "sheet_regex":  r"TestCases",
        "header_row":   1,
        "unique_field": "test_case_id",
        "sync":         False,
    },
    {
        "pattern":      r"bugs_data",
        "collection":   "bugs",
        "sheet_regex":  r"Bugs",
        "header_row":   1,
        "unique_field": "bug_id",
        "sync":         False,
    },
    {
        "pattern":      r"requirements_data",
        "collection":   "requirements",
        "sheet_regex":  r"Requirements",
        "header_row":   1,
        "unique_field": "requirement_id",
        "sync":         True,               # sync mode: tracks db_status lifecycle
    },
]
```

To add a new Excel source, add a new entry to `FILE_PATTERNS`.

---

## MongoDB connection

Default: `mongodb://localhost:27017/`, database `test_db`.

All connection strings now read from environment variables:

```bash
# .env (copy from .env.example)
MONGO_URI=mongodb://localhost:27017/
DB_NAME=test_db
```

The following files all respect these env vars automatically:
- `Django_Dashboard/dashboard/mongo_utils.py`
- `graphrag/build_graph.py`
- `graphrag/tasks.py` (Celery tasks)
- `airflow/dags/graphrag_pipeline_dag.py`

The uploader scripts (`generate_data.py`, `uploader.py`, `Uploader_Scripts/`) still use hardcoded defaults.
To change their connection, edit `MONGO_URI` / `DB_NAME` at the top of each script,
or set the environment variables before running them.

When running in Docker Compose, services connect to each other using the service name as hostname:
```bash
MONGO_URI=mongodb://mongo:27017/    # 'mongo' = Docker service name
```

---

## Rebuilding the GraphRAG pipeline after upload

After uploading new data, rebuild the graph so the React frontend and FastAPI query API
reflect the latest records:

```bash
# Option A — manual
python graphrag/build_graph.py
python graphrag/chunk_graph.py
python graphrag/embed_chunks.py   # only if using FAISS
python graphrag/load_neo4j.py     # only if using Neo4j hybrid

# Option B — via API (queues Celery task chain)
curl -X POST http://localhost:8001/pipeline/rebuild

# Option C — via React frontend
# Dashboard -> Rebuild Pipeline button (triggers the same Celery chain)
```
