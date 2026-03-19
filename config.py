# config.py
# Maps Excel filename patterns to MongoDB collections and sheet names.
# Used by uploader.py and Uploader_Scripts.
#
# Schema:
#   pattern     - regex matched against the lowercase filename
#   collection  - MongoDB collection name in test_db
#   sheet_regex - regex matched against Excel sheet names
#   header_row  - row number containing column headers (1-indexed)
#   unique_field - field used for compare-and-sync (comp uploaders only)
#   sync        - if True, use sync (update/added/deleted) instead of insert_many

FILE_PATTERNS = [
    {
        "pattern":      r"employees_data",
        "collection":   "employees",
        "sheet_regex":  r"Employees",
        "header_row":   1,
        "unique_field": "employee_id",
        "sync":         False,
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
        "sync":         True,   # sync tracks added/updated/deleted via db_status
    },
]
