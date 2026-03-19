from django.shortcuts import render
from django.http import JsonResponse
from .mongo_utils import get_mongo_collection
from datetime import datetime


def home(request):
    return render(request, 'home.html')


# ── Data classes ──────────────────────────────────────────────────────────────

class Project:
    def __init__(self, d):
        self.project_id   = d.get('project_id')
        self.project_name = d.get('project_name')
        self.domain       = d.get('domain')
        self.status       = d.get('status')
        self.priority     = d.get('priority')
        self.tech_stack   = ', '.join(d.get('tech_stack') or [])
        self.lead_name    = d.get('lead_name')
        self.team         = d.get('team')
        self.git_hash     = d.get('git_hash')
        self.date         = d.get('date')
        self.db_status    = d.get('db_status')


class TestCase:
    def __init__(self, d):
        self.test_case_id            = d.get('test_case_id')
        self.test_case_name          = d.get('test_case_name')
        self.domain                  = d.get('domain')
        self.project_id              = d.get('project_id')
        self.project_name            = d.get('project_name')
        self.assigned_to_name        = d.get('assigned_to_name')
        self.assigned_to_employee_id = d.get('assigned_to_employee_id')
        self.parent_folder           = d.get('parent_folder')
        self.path_folder             = d.get('path_folder')
        self.status                  = d.get('status')
        self.test_type               = d.get('test_type')
        self.automation_status       = d.get('automation_status')
        self.team                    = d.get('team')
        self.git_hash                = d.get('git_hash')
        self.date                    = d.get('date')
        self.db_status               = d.get('db_status')


class Bug:
    def __init__(self, d):
        self.bug_id               = d.get('bug_id')
        self.title                = d.get('title')
        self.description          = d.get('description')
        self.severity             = d.get('severity')
        self.priority             = d.get('priority')
        self.status               = d.get('status')
        self.bug_type             = d.get('bug_type')
        self.project_id           = d.get('project_id')
        self.project_name         = d.get('project_name')
        self.test_case_id         = d.get('test_case_id')
        self.test_case_name       = d.get('test_case_name')
        self.reporter_name        = d.get('reporter_name')
        self.assignee_name        = d.get('assignee_name')
        self.domain               = d.get('domain')
        self.team                 = d.get('team')
        self.git_hash             = d.get('git_hash')
        self.date                 = d.get('date')
        self.db_status            = d.get('db_status')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _date_filter(query, field, start_date_str, end_date_str):
    if start_date_str and end_date_str:
        try:
            s = datetime.strptime(start_date_str, '%Y-%m-%d')
            e = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query[field] = {'$gte': s, '$lte': e}
        except ValueError:
            pass


# ── Views ─────────────────────────────────────────────────────────────────────

def index(request):
    proj_col = get_mongo_collection('projects')
    tc_col   = get_mongo_collection('test_cases')
    bug_col  = get_mongo_collection('bugs')

    # ── dropdown options ──────────────────────────────────────────────────────
    domain_options   = sorted(x for x in tc_col.distinct('domain')        if x)
    team_options     = sorted(x for x in tc_col.distinct('team')          if x)
    status_options   = sorted(x for x in tc_col.distinct('status')        if x)
    priority_options = sorted(x for x in bug_col.distinct('priority')     if x)
    project_options  = sorted(x for x in tc_col.distinct('project_name')  if x)

    # ── build filters ─────────────────────────────────────────────────────────
    proj_q = {}
    tc_q   = {}
    bug_q  = {}

    g = request.GET
    if g.get('domain'):
        proj_q['domain'] = tc_q['domain'] = bug_q['domain'] = g['domain']
    if g.get('team'):
        proj_q['team']   = tc_q['team']   = bug_q['team']   = g['team']
    if g.get('status'):
        tc_q['status']   = g['status']
    if g.get('priority'):
        bug_q['priority'] = g['priority']
    if g.get('project_name'):
        tc_q['project_name']  = g['project_name']
        bug_q['project_name'] = g['project_name']
        proj_q['project_name'] = g['project_name']

    _date_filter(tc_q,   'date', g.get('start_date'), g.get('end_date'))
    _date_filter(bug_q,  'date', g.get('start_date'), g.get('end_date'))
    _date_filter(proj_q, 'date', g.get('start_date'), g.get('end_date'))

    # ── fetch data ────────────────────────────────────────────────────────────
    projects   = [Project(d)  for d in proj_col.find(proj_q).sort('date', -1)]
    test_cases = [TestCase(d) for d in tc_col.find(tc_q).sort('date', -1)]
    bugs       = [Bug(d)      for d in bug_col.find(bug_q).sort('date', -1)]

    # ── join: projects ↔ test_cases (via project_id) ─────────────────────────
    proj_map = {p.project_id: p for p in projects}
    proj_tc_matched = []
    for tc in test_cases:
        if tc.project_id and tc.project_id in proj_map:
            p = proj_map[tc.project_id]
            proj_tc_matched.append({
                'test_case_id':      tc.test_case_id,
                'test_case_name':    tc.test_case_name,
                'tc_status':         tc.status,
                'test_type':         tc.test_type,
                'automation_status': tc.automation_status,
                'assigned_to_name':  tc.assigned_to_name,
                'project_id':        p.project_id,
                'project_name':      p.project_name,
                'proj_status':       p.status,
                'proj_priority':     p.priority,
                'domain':            tc.domain,
                'team':              tc.team,
                'git_hash':          tc.git_hash,
                'date':              tc.date,
            })

    # ── join: test_cases ↔ bugs (via test_case_id) ───────────────────────────
    tc_map = {tc.test_case_id: tc for tc in test_cases}
    tc_bug_matched = []
    for bug in bugs:
        if bug.test_case_id and bug.test_case_id in tc_map:
            tc = tc_map[bug.test_case_id]
            tc_bug_matched.append({
                'bug_id':          bug.bug_id,
                'title':           bug.title,
                'severity':        bug.severity,
                'bug_priority':    bug.priority,
                'bug_status':      bug.status,
                'bug_type':        bug.bug_type,
                'assignee_name':   bug.assignee_name,
                'reporter_name':   bug.reporter_name,
                'test_case_id':    tc.test_case_id,
                'test_case_name':  tc.test_case_name,
                'tc_status':       tc.status,
                'project_name':    bug.project_name,
                'domain':          bug.domain,
                'team':            bug.team,
                'git_hash':        bug.git_hash,
                'date':            bug.date,
            })

    # ── statistics ────────────────────────────────────────────────────────────
    def count_by(items, attr, values):
        return {v: sum(1 for x in items if getattr(x, attr, None) == v) for v in values}

    tc_status_counts  = count_by(test_cases, 'status',   ['Passed', 'Failed', 'Skipped', 'Pending', 'Blocked'])
    bug_sev_counts    = count_by(bugs,       'severity', ['Critical', 'Major', 'Minor', 'Trivial'])
    bug_status_counts = count_by(bugs,       'status',   ['Open', 'In Progress', 'Resolved', 'Closed', 'Reopened'])
    proj_status_counts = count_by(projects,  'status',   ['Active', 'Completed', 'On Hold', 'Planning', 'Cancelled'])

    return render(request, 'index.html', {
        'projects':         projects,
        'test_cases':       test_cases,
        'bugs':             bugs,
        'proj_tc_matched':  proj_tc_matched,
        'tc_bug_matched':   tc_bug_matched,

        'tc_status_counts':   tc_status_counts,
        'bug_sev_counts':     bug_sev_counts,
        'bug_status_counts':  bug_status_counts,
        'proj_status_counts': proj_status_counts,

        'domain_options':   domain_options,
        'team_options':     team_options,
        'status_options':   status_options,
        'priority_options': priority_options,
        'project_options':  project_options,
        'filter_criteria':  g,
    })


def filter_by_domain(request):
    domain = request.GET.get('domain')
    if not domain:
        return JsonResponse({'proj_tc_matched': [], 'tc_bug_matched': []})

    tc_col  = get_mongo_collection('test_cases')
    bug_col = get_mongo_collection('bugs')
    proj_col = get_mongo_collection('projects')

    projects   = {d['project_id']: d for d in proj_col.find({'domain': domain})}
    test_cases = {d['test_case_id']: d for d in tc_col.find({'domain': domain})}
    bugs       = list(bug_col.find({'domain': domain}))

    proj_tc_matched = [
        {
            'test_case_id':   tc['test_case_id'],
            'test_case_name': tc['test_case_name'],
            'tc_status':      tc.get('status'),
            'project_name':   tc.get('project_name'),
            'domain':         tc.get('domain'),
            'team':           tc.get('team'),
        }
        for tc in test_cases.values()
        if tc.get('project_id') in projects
    ]

    tc_bug_matched = [
        {
            'bug_id':        b['bug_id'],
            'title':         b['title'],
            'severity':      b.get('severity'),
            'test_case_name': test_cases[b['test_case_id']]['test_case_name'] if b.get('test_case_id') in test_cases else None,
            'domain':        b.get('domain'),
        }
        for b in bugs
        if b.get('test_case_id') in test_cases
    ]

    return JsonResponse({'proj_tc_matched': proj_tc_matched, 'tc_bug_matched': tc_bug_matched})
