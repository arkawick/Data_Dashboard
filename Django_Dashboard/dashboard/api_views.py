"""
dashboard/api_views.py
======================
REST API views for the Django dashboard (JSON responses, JWT-protected).

All endpoints require a valid JWT access token in the Authorization header:
    Authorization: Bearer <access_token>

Endpoints (registered in config/urls.py):
    GET  /api/stats/          - summary counts for all collections
    GET  /api/projects/       - paginated projects list
    GET  /api/test-cases/     - paginated test cases with optional filters
    GET  /api/bugs/           - paginated bugs with optional filters
    GET  /api/requirements/   - paginated requirements
    GET  /api/employees/      - paginated employees
    POST /api/rebuild/        - trigger graph pipeline rebuild via FastAPI
"""

import json
import os
import urllib.request

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .mongo_utils import get_mongo_collection
from .auth_views import jwt_required

PAGE_SIZE = 50


# ── Pagination helper ─────────────────────────────────────────────────────────

def _paginate(cursor, page: int, page_size: int = PAGE_SIZE) -> dict:
    total = cursor.count()   # Note: count() on a cursor after find()
    offset = (page - 1) * page_size
    items = list(cursor.skip(offset).limit(page_size))
    return {
        "count":    total,
        "page":     page,
        "pages":    (total + page_size - 1) // page_size,
        "results":  items,
    }


def _clean(docs: list) -> list:
    """Remove MongoDB _id field from documents."""
    return [{k: v for k, v in d.items() if k != "_id"} for d in docs]


def _int_param(request, name: str, default: int) -> int:
    try:
        return max(1, int(request.GET.get(name, default)))
    except (TypeError, ValueError):
        return default


# ── Stats ─────────────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
@jwt_required
def stats_api(request):
    """GET /api/stats/ - document counts and status breakdowns."""
    col_names = ["employees", "projects", "test_cases", "bugs", "requirements"]
    counts = {name: get_mongo_collection(name).count_documents({}) for name in col_names}

    bugs_col = get_mongo_collection("bugs")
    tc_col   = get_mongo_collection("test_cases")

    bug_by_severity = {
        sev: bugs_col.count_documents({"severity": sev})
        for sev in ["Critical", "Major", "Minor", "Trivial"]
    }
    tc_by_status = {
        st: tc_col.count_documents({"status": st})
        for st in ["Passed", "Failed", "Skipped", "Pending", "Blocked"]
    }

    return JsonResponse({
        "counts":         counts,
        "bug_by_severity": bug_by_severity,
        "tc_by_status":   tc_by_status,
    })


# ── Projects ──────────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
@jwt_required
def projects_api(request):
    """GET /api/projects/?domain=&status=&page=1"""
    col = get_mongo_collection("projects")
    query = {}
    if request.GET.get("domain"):
        query["domain"] = request.GET["domain"]
    if request.GET.get("status"):
        query["status"] = request.GET["status"]
    if request.GET.get("priority"):
        query["priority"] = request.GET["priority"]

    page     = _int_param(request, "page", 1)
    page_size = _int_param(request, "page_size", PAGE_SIZE)

    total = col.count_documents(query)
    offset = (page - 1) * page_size
    results = _clean(list(col.find(query, {"_id": 0}).sort("date", -1).skip(offset).limit(page_size)))

    return JsonResponse({
        "count":   total,
        "page":    page,
        "pages":   (total + page_size - 1) // page_size,
        "results": results,
    })


# ── Test Cases ────────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
@jwt_required
def test_cases_api(request):
    """GET /api/test-cases/?domain=&status=&team=&project_name=&page=1"""
    col = get_mongo_collection("test_cases")
    query = {}
    for field in ("domain", "status", "team", "project_name", "test_type", "automation_status"):
        if request.GET.get(field):
            query[field] = request.GET[field]

    page     = _int_param(request, "page", 1)
    page_size = _int_param(request, "page_size", PAGE_SIZE)

    total = col.count_documents(query)
    offset = (page - 1) * page_size
    results = _clean(list(col.find(query, {"_id": 0}).sort("date", -1).skip(offset).limit(page_size)))

    return JsonResponse({
        "count":   total,
        "page":    page,
        "pages":   (total + page_size - 1) // page_size,
        "results": results,
    })


# ── Bugs ──────────────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
@jwt_required
def bugs_api(request):
    """GET /api/bugs/?severity=&status=&priority=&domain=&page=1"""
    col = get_mongo_collection("bugs")
    query = {}
    for field in ("severity", "status", "priority", "domain", "team", "bug_type", "project_name"):
        if request.GET.get(field):
            query[field] = request.GET[field]

    page     = _int_param(request, "page", 1)
    page_size = _int_param(request, "page_size", PAGE_SIZE)

    total = col.count_documents(query)
    offset = (page - 1) * page_size
    results = _clean(list(col.find(query, {"_id": 0}).sort("date", -1).skip(offset).limit(page_size)))

    return JsonResponse({
        "count":   total,
        "page":    page,
        "pages":   (total + page_size - 1) // page_size,
        "results": results,
    })


# ── Requirements ──────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
@jwt_required
def requirements_api(request):
    """GET /api/requirements/?category=&status=&priority=&domain=&page=1"""
    col = get_mongo_collection("requirements")
    query = {}
    for field in ("category", "status", "priority", "domain", "team", "project_name"):
        if request.GET.get(field):
            query[field] = request.GET[field]

    page     = _int_param(request, "page", 1)
    page_size = _int_param(request, "page_size", PAGE_SIZE)

    total = col.count_documents(query)
    offset = (page - 1) * page_size
    results = _clean(list(col.find(query, {"_id": 0}).sort("date", -1).skip(offset).limit(page_size)))

    return JsonResponse({
        "count":   total,
        "page":    page,
        "pages":   (total + page_size - 1) // page_size,
        "results": results,
    })


# ── Employees ─────────────────────────────────────────────────────────────────

@require_http_methods(["GET"])
@jwt_required
def employees_api(request):
    """GET /api/employees/?department=&team=&seniority=&page=1"""
    col = get_mongo_collection("employees")
    query = {}
    for field in ("department", "team", "seniority", "role"):
        if request.GET.get(field):
            query[field] = request.GET[field]

    page     = _int_param(request, "page", 1)
    page_size = _int_param(request, "page_size", PAGE_SIZE)

    total = col.count_documents(query)
    offset = (page - 1) * page_size
    results = _clean(list(col.find(query, {"_id": 0}).skip(offset).limit(page_size)))

    return JsonResponse({
        "count":   total,
        "page":    page,
        "pages":   (total + page_size - 1) // page_size,
        "results": results,
    })


# ── Pipeline rebuild trigger ──────────────────────────────────────────────────

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@require_http_methods(["POST"])
@jwt_required
def trigger_rebuild(request):
    """POST /api/rebuild/ - trigger async graph rebuild via FastAPI/Celery."""
    fastapi_url = os.environ.get("FASTAPI_URL", "http://localhost:8001")
    try:
        req = urllib.request.Request(
            f"{fastapi_url}/pipeline/rebuild",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return JsonResponse(data)
    except Exception as exc:
        return JsonResponse(
            {"error": f"Could not reach FastAPI service: {exc}"},
            status=503,
        )
