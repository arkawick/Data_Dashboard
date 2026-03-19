from django.shortcuts import render
from .mongo_utils import get_mongo_collection
from datetime import datetime


# ── Data classes ──────────────────────────────────────────────────────────────

class Requirement:
    def __init__(self, d):
        self.requirement_id              = d.get('requirement_id')
        self.requirement_name            = d.get('requirement_name')
        self.description                 = d.get('description')
        self.domain                      = d.get('domain')
        self.category                    = d.get('category')
        self.priority                    = d.get('priority')
        self.status                      = d.get('status')
        self.project_id                  = d.get('project_id')
        self.project_name                = d.get('project_name')
        self.verification_responsibility = d.get('verification_responsibility')
        self.verifier_employee_id        = d.get('verifier_employee_id')
        self.covered_by_test_case_id     = d.get('covered_by_test_case_id')
        self.covered_by_test_case_name   = d.get('covered_by_test_case_name')
        self.team                        = d.get('team')
        self.date                        = d.get('date')
        self.db_status                   = d.get('db_status')


class Employee:
    def __init__(self, d):
        self.employee_id = d.get('employee_id')
        self.name        = d.get('name')
        self.email       = d.get('email')
        self.department  = d.get('department')
        self.role        = d.get('role')
        self.team        = d.get('team')
        self.location    = d.get('location')
        self.seniority   = d.get('seniority')
        self.skills      = ', '.join(d.get('skills') or [])
        self.date        = d.get('date')
        self.db_status   = d.get('db_status')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _date_filter(query, field, start_str, end_str):
    if start_str and end_str:
        try:
            s = datetime.strptime(start_str, '%Y-%m-%d')
            e = datetime.strptime(end_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query[field] = {'$gte': s, '$lte': e}
        except ValueError:
            pass


# ── View ──────────────────────────────────────────────────────────────────────

def index2(request):
    req_col = get_mongo_collection('requirements')
    emp_col = get_mongo_collection('employees')

    # ── dropdown options ──────────────────────────────────────────────────────
    domain_options   = sorted(x for x in req_col.distinct('domain')    if x)
    team_options     = sorted(x for x in req_col.distinct('team')      if x)
    category_options = sorted(x for x in req_col.distinct('category')  if x)
    priority_options = sorted(x for x in req_col.distinct('priority')  if x)
    status_options   = sorted(x for x in req_col.distinct('status')    if x)
    dept_options     = sorted(x for x in emp_col.distinct('department') if x)
    seniority_options = sorted(x for x in emp_col.distinct('seniority') if x)

    # ── build filters ─────────────────────────────────────────────────────────
    req_q = {}
    emp_q = {}

    g = request.GET
    if g.get('domain'):
        req_q['domain'] = g['domain']
    if g.get('team'):
        req_q['team'] = emp_q['team'] = g['team']
    if g.get('category'):
        req_q['category'] = g['category']
    if g.get('priority'):
        req_q['priority'] = g['priority']
    if g.get('status'):
        req_q['status'] = g['status']
    if g.get('department'):
        emp_q['department'] = g['department']
    if g.get('seniority'):
        emp_q['seniority'] = g['seniority']

    _date_filter(req_q, 'date', g.get('start_date'), g.get('end_date'))
    _date_filter(emp_q, 'date', g.get('start_date'), g.get('end_date'))

    # ── fetch data ────────────────────────────────────────────────────────────
    requirements = [Requirement(d) for d in req_col.find(req_q).sort('date', -1)]
    employees    = [Employee(d)    for d in emp_col.find(emp_q).sort('date', -1)]

    # ── join: requirements ↔ employees (via verifier_employee_id) ─────────────
    emp_map = {e.employee_id: e for e in employees}
    req_emp_matched = []
    for req in requirements:
        if req.verifier_employee_id and req.verifier_employee_id in emp_map:
            emp = emp_map[req.verifier_employee_id]
            req_emp_matched.append({
                'requirement_id':   req.requirement_id,
                'requirement_name': req.requirement_name,
                'req_status':       req.status,
                'category':         req.category,
                'priority':         req.priority,
                'project_name':     req.project_name,
                'domain':           req.domain,
                'team':             req.team,
                'covered_by':       req.covered_by_test_case_name,
                'employee_id':      emp.employee_id,
                'employee_name':    emp.name,
                'role':             emp.role,
                'department':       emp.department,
                'seniority':        emp.seniority,
                'date':             req.date,
            })

    # ── db_status breakdown ───────────────────────────────────────────────────
    db_status_counts = {}
    for r in requirements:
        if r.db_status:
            db_status_counts[r.db_status] = db_status_counts.get(r.db_status, 0) + 1

    req_status_counts = {}
    for r in requirements:
        if r.status:
            req_status_counts[r.status] = req_status_counts.get(r.status, 0) + 1

    emp_dept_counts = {}
    for e in employees:
        if e.department:
            emp_dept_counts[e.department] = emp_dept_counts.get(e.department, 0) + 1

    return render(request, 'index2.html', {
        'requirements':    requirements,
        'employees':       employees,
        'req_emp_matched': req_emp_matched,

        'db_status_counts':  db_status_counts,
        'req_status_counts': req_status_counts,
        'emp_dept_counts':   emp_dept_counts,

        'domain_options':    domain_options,
        'team_options':      team_options,
        'category_options':  category_options,
        'priority_options':  priority_options,
        'status_options':    status_options,
        'dept_options':      dept_options,
        'seniority_options': seniority_options,
        'filter_criteria':   g,
    })
