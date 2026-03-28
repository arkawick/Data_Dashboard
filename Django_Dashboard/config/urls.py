from django.urls import path
from django.http import HttpResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from dashboard import views, views2, api_views, auth_views

urlpatterns = [
    # ── Dashboard (template views, public) ───────────────────────────────────
    path("",                  views.home,             name="home"),
    path("index/",            views.index,            name="index"),
    path("index2/",           views2.index2,          name="index2"),
    path("filter_by_domain/", views.filter_by_domain, name="filter_by_domain"),

    # ── Auth ──────────────────────────────────────────────────────────────────
    path("api/auth/login/",    auth_views.login_view,    name="auth-login"),
    path("api/auth/refresh/",  auth_views.refresh_view,  name="auth-refresh"),
    path("api/auth/me/",       auth_views.me_view,       name="auth-me"),
    path("api/auth/register/", auth_views.register_view, name="auth-register"),

    # ── REST API (JWT-protected) ───────────────────────────────────────────────
    path("api/stats/",        api_views.stats_api,        name="api-stats"),
    path("api/projects/",     api_views.projects_api,     name="api-projects"),
    path("api/test-cases/",   api_views.test_cases_api,   name="api-test-cases"),
    path("api/bugs/",         api_views.bugs_api,         name="api-bugs"),
    path("api/requirements/", api_views.requirements_api, name="api-requirements"),
    path("api/employees/",    api_views.employees_api,    name="api-employees"),
    path("api/rebuild/",      api_views.trigger_rebuild,  name="api-rebuild"),

    # ── Prometheus metrics ────────────────────────────────────────────────────
    path("metrics", lambda r: HttpResponse(
        generate_latest(), content_type=CONTENT_TYPE_LATEST
    ), name="metrics"),
]
