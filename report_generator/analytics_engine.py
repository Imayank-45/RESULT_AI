"""
analytics_engine.py
-------------------
Pure computation layer — performs all statistical analysis on the ReportDataset.
No PDF/chart logic here; returns structured dicts consumed by chart renderers and sections.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from report_generator.config import GRADE_POINTS
from report_generator.data_loader import ReportDataset, StudentRecord


# ═══════════════════════════════════════════════════════════════════════
#  ANALYTICS RESULT MODELS
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class OverallStats:
    total_students: int = 0
    passed: int = 0
    failed: int = 0
    not_found: int = 0
    unknown: int = 0
    pass_percentage: float = 0.0
    fail_percentage: float = 0.0
    highest_sgpa: float = 0.0
    lowest_sgpa: float = 0.0
    average_sgpa: float = 0.0
    median_sgpa: float = 0.0
    std_dev_sgpa: float = 0.0
    average_cgpa: float = 0.0
    highest_cgpa: float = 0.0
    lowest_cgpa: float = 0.0
    median_cgpa: float = 0.0
    topper_name: str = ""
    topper_enrollment: str = ""
    topper_sgpa: float = 0.0


@dataclass
class BranchStats:
    branch_code: str = ""
    branch_name: str = ""
    total: int = 0
    passed: int = 0
    failed: int = 0
    pass_percentage: float = 0.0
    fail_percentage: float = 0.0
    average_sgpa: float = 0.0
    average_cgpa: float = 0.0
    highest_sgpa: float = 0.0
    topper_name: str = ""
    topper_enrollment: str = ""
    backlog_count: int = 0


@dataclass
class SubjectStats:
    code: str = ""
    total_students: int = 0
    passed: int = 0
    failed: int = 0
    pass_percentage: float = 0.0
    fail_percentage: float = 0.0
    average_grade_point: float = 0.0
    difficulty_index: float = 0.0       # 0-1, higher = harder
    highest_grade: str = ""
    lowest_grade: str = ""
    grade_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class RiskStudent:
    enrollment: str = ""
    name: str = ""
    branch: str = ""
    sgpa: float = 0.0
    cgpa: float = 0.0
    backlog_count: int = 0
    risk_type: str = ""     # "at_risk" / "near_distinction" / "multi_backlog"


@dataclass
class AnalyticsResult:
    """Container for all computed analytics."""
    overall: OverallStats = field(default_factory=OverallStats)
    branch_stats: List[BranchStats] = field(default_factory=list)
    subject_stats: List[SubjectStats] = field(default_factory=list)
    toppers: List[StudentRecord] = field(default_factory=list)
    grade_distribution: Dict[str, int] = field(default_factory=dict)
    sgpa_distribution: Dict[str, int] = field(default_factory=dict)
    backlog_by_dept: Dict[str, int] = field(default_factory=dict)
    backlog_by_subject: Dict[str, int] = field(default_factory=dict)
    students_at_risk: List[RiskStudent] = field(default_factory=list)
    students_near_distinction: List[RiskStudent] = field(default_factory=list)
    students_multi_backlog: List[RiskStudent] = field(default_factory=list)
    heatmap_data: Dict[str, Dict[str, float]] = field(default_factory=dict)
    comparison: Optional[Dict[str, Any]] = None
    best_branch: str = ""
    weakest_branch: str = ""
    most_failed_subject: str = ""
    most_improved_subject: str = ""


# ═══════════════════════════════════════════════════════════════════════
#  MAIN ANALYTICS COMPUTATION
# ═══════════════════════════════════════════════════════════════════════

def compute_analytics(dataset: ReportDataset) -> AnalyticsResult:
    """Run full analytics pipeline on the dataset."""
    result = AnalyticsResult()
    valid = [r for r in dataset.records if not r.not_found]

    if not valid:
        return result

    # ── Overall Statistics ──
    result.overall = _compute_overall(valid)

    # ── Branch Analysis ──
    result.branch_stats = _compute_branch_stats(valid)

    # Best/Weakest branch
    if result.branch_stats:
        sorted_branches = sorted(result.branch_stats, key=lambda b: b.average_sgpa, reverse=True)
        result.best_branch = sorted_branches[0].branch_name if sorted_branches[0].average_sgpa > 0 else ""
        result.weakest_branch = sorted_branches[-1].branch_name if sorted_branches[-1].average_sgpa > 0 else ""

    # ── Subject Analysis ──
    result.subject_stats = _compute_subject_stats(valid)

    if result.subject_stats:
        sorted_subj = sorted(result.subject_stats, key=lambda s: s.fail_percentage, reverse=True)
        result.most_failed_subject = sorted_subj[0].code if sorted_subj[0].fail_percentage > 0 else ""

    # ── Toppers ──
    result.toppers = _compute_toppers(valid, n=20)

    # ── Grade Distribution ──
    result.grade_distribution = _compute_grade_distribution(valid)

    # ── SGPA Distribution ──
    result.sgpa_distribution = _compute_sgpa_distribution(valid)

    # ── Backlog Analysis ──
    result.backlog_by_dept, result.backlog_by_subject = _compute_backlog_analysis(valid)

    # ── Risk Analysis ──
    result.students_at_risk = _compute_at_risk(valid)
    result.students_near_distinction = _compute_near_distinction(valid)
    result.students_multi_backlog = _compute_multi_backlog(valid)

    # ── Heatmap Data ──
    result.heatmap_data = _compute_heatmap(valid)

    # ── Comparison (if available) ──
    if dataset.comparison_records:
        comp_valid = [r for r in dataset.comparison_records if not r.not_found]
        if comp_valid:
            result.comparison = _compute_comparison(valid, comp_valid)

    return result


# ═══════════════════════════════════════════════════════════════════════
#  INDIVIDUAL COMPUTATIONS
# ═══════════════════════════════════════════════════════════════════════

def _compute_overall(records: List[StudentRecord]) -> OverallStats:
    stats = OverallStats()
    stats.total_students = len(records)

    for r in records:
        if r.result == "PASS":
            stats.passed += 1
        elif r.result == "FAIL":
            stats.failed += 1
        else:
            stats.unknown += 1

    graded = stats.passed + stats.failed
    stats.pass_percentage = round((stats.passed / graded * 100), 2) if graded > 0 else 0.0
    stats.fail_percentage = round((stats.failed / graded * 100), 2) if graded > 0 else 0.0

    sgpas = [r.sgpa for r in records if r.sgpa is not None and r.sgpa > 0]
    cgpas = [r.cgpa for r in records if r.cgpa is not None and r.cgpa > 0]

    if sgpas:
        stats.highest_sgpa = round(max(sgpas), 2)
        stats.lowest_sgpa = round(min(sgpas), 2)
        stats.average_sgpa = round(statistics.mean(sgpas), 2)
        stats.median_sgpa = round(statistics.median(sgpas), 2)
        if len(sgpas) > 1:
            stats.std_dev_sgpa = round(statistics.stdev(sgpas), 2)

        # Topper
        topper = max(records, key=lambda r: r.sgpa if r.sgpa else 0)
        stats.topper_name = topper.name
        stats.topper_enrollment = topper.enrollment
        stats.topper_sgpa = topper.sgpa or 0.0

    if cgpas:
        stats.average_cgpa = round(statistics.mean(cgpas), 2)
        stats.highest_cgpa = round(max(cgpas), 2)
        stats.lowest_cgpa = round(min(cgpas), 2)
        stats.median_cgpa = round(statistics.median(cgpas), 2)

    return stats


def _compute_branch_stats(records: List[StudentRecord]) -> List[BranchStats]:
    branches: Dict[str, List[StudentRecord]] = defaultdict(list)
    for r in records:
        branches[r.branch].append(r)

    result = []
    for code, students in sorted(branches.items()):
        bs = BranchStats()
        bs.branch_code = code
        bs.branch_name = students[0].branch_full if students else code
        bs.total = len(students)
        bs.passed = sum(1 for s in students if s.result == "PASS")
        bs.failed = sum(1 for s in students if s.result == "FAIL")
        graded = bs.passed + bs.failed
        bs.pass_percentage = round((bs.passed / graded * 100), 2) if graded > 0 else 0.0
        bs.fail_percentage = round((bs.failed / graded * 100), 2) if graded > 0 else 0.0

        sgpas = [s.sgpa for s in students if s.sgpa is not None and s.sgpa > 0]
        cgpas = [s.cgpa for s in students if s.cgpa is not None and s.cgpa > 0]
        bs.average_sgpa = round(statistics.mean(sgpas), 2) if sgpas else 0.0
        bs.average_cgpa = round(statistics.mean(cgpas), 2) if cgpas else 0.0
        bs.highest_sgpa = round(max(sgpas), 2) if sgpas else 0.0

        # Topper
        if students:
            topper = max(students, key=lambda s: s.sgpa if s.sgpa else 0)
            bs.topper_name = topper.name
            bs.topper_enrollment = topper.enrollment

        # Backlog count
        bs.backlog_count = sum(len(s.fail_subjects) for s in students)

        result.append(bs)

    return result


def _compute_subject_stats(records: List[StudentRecord]) -> List[SubjectStats]:
    subjects: Dict[str, List[str]] = defaultdict(list)

    for r in records:
        for code, grade in r.subjects.items():
            subjects[code].append(grade.strip().upper())

    result = []
    for code, grades in sorted(subjects.items()):
        ss = SubjectStats()
        ss.code = code
        ss.total_students = len(grades)

        fail_grades = {"F", "FAIL", "AB", "ABSENT", "RL"}
        ss.failed = sum(1 for g in grades if g in fail_grades)
        ss.passed = ss.total_students - ss.failed
        ss.pass_percentage = round((ss.passed / ss.total_students * 100), 2) if ss.total_students > 0 else 0.0
        ss.fail_percentage = round((ss.failed / ss.total_students * 100), 2) if ss.total_students > 0 else 0.0

        # Grade points
        gps = [GRADE_POINTS.get(g, 5.0) for g in grades if g not in fail_grades]
        all_gps = [GRADE_POINTS.get(g, 0.0) for g in grades]
        ss.average_grade_point = round(statistics.mean(all_gps), 2) if all_gps else 0.0

        # Difficulty index (higher = harder, based on fail% and avg grade)
        ss.difficulty_index = round(1.0 - (ss.average_grade_point / 10.0), 2)

        # Highest/Lowest grade
        grade_order = ['O', 'A+', 'A', 'B+', 'B', 'C', 'P', 'F']
        present_grades = [g for g in grades if g in grade_order]
        if present_grades:
            ss.highest_grade = min(present_grades, key=lambda g: grade_order.index(g))
            ss.lowest_grade = max(present_grades, key=lambda g: grade_order.index(g))

        # Grade distribution
        ss.grade_distribution = dict(Counter(grades))

        result.append(ss)

    return result


def _compute_toppers(records: List[StudentRecord], n: int = 20) -> List[StudentRecord]:
    with_sgpa = [r for r in records if r.sgpa is not None and r.sgpa > 0]
    return sorted(with_sgpa, key=lambda r: (r.sgpa or 0, r.cgpa or 0), reverse=True)[:n]


def _compute_grade_distribution(records: List[StudentRecord]) -> Dict[str, int]:
    all_grades = []
    for r in records:
        for grade in r.subjects.values():
            all_grades.append(grade.strip().upper())
    return dict(Counter(all_grades))


def _compute_sgpa_distribution(records: List[StudentRecord]) -> Dict[str, int]:
    ranges = {
        '< 4.0': 0, '4.0–5.0': 0, '5.0–6.0': 0,
        '6.0–7.0': 0, '7.0–8.0': 0, '8.0–9.0': 0, '9.0–10.0': 0
    }
    for r in records:
        if r.sgpa is None:
            continue
        s = r.sgpa
        if s < 4.0:
            ranges['< 4.0'] += 1
        elif s < 5.0:
            ranges['4.0–5.0'] += 1
        elif s < 6.0:
            ranges['5.0–6.0'] += 1
        elif s < 7.0:
            ranges['6.0–7.0'] += 1
        elif s < 8.0:
            ranges['7.0–8.0'] += 1
        elif s < 9.0:
            ranges['8.0–9.0'] += 1
        else:
            ranges['9.0–10.0'] += 1
    return ranges


def _compute_backlog_analysis(records: List[StudentRecord]):
    by_dept: Dict[str, int] = defaultdict(int)
    by_subject: Dict[str, int] = defaultdict(int)

    for r in records:
        if r.fail_subjects:
            by_dept[r.branch_full or r.branch] += len(r.fail_subjects)
            for subj in r.fail_subjects:
                # Clean subject code
                clean = subj.split("-")[0].strip() if "-" in subj else subj.strip()
                by_subject[clean] += 1

    return dict(by_dept), dict(by_subject)


def _compute_at_risk(records: List[StudentRecord]) -> List[RiskStudent]:
    """Students with SGPA < 5.0 or FAIL result."""
    result = []
    for r in records:
        if r.result == "FAIL" or (r.sgpa is not None and r.sgpa < 5.0):
            result.append(RiskStudent(
                enrollment=r.enrollment, name=r.name, branch=r.branch_full or r.branch,
                sgpa=r.sgpa or 0.0, cgpa=r.cgpa or 0.0,
                backlog_count=len(r.fail_subjects), risk_type="at_risk"
            ))
    return sorted(result, key=lambda x: x.sgpa)


def _compute_near_distinction(records: List[StudentRecord]) -> List[RiskStudent]:
    """Students with SGPA between 7.5 and 8.5 — near distinction."""
    result = []
    for r in records:
        if r.sgpa is not None and 7.5 <= r.sgpa <= 8.5 and r.result == "PASS":
            result.append(RiskStudent(
                enrollment=r.enrollment, name=r.name, branch=r.branch_full or r.branch,
                sgpa=r.sgpa, cgpa=r.cgpa or 0.0,
                backlog_count=0, risk_type="near_distinction"
            ))
    return sorted(result, key=lambda x: x.sgpa, reverse=True)


def _compute_multi_backlog(records: List[StudentRecord]) -> List[RiskStudent]:
    """Students with 2+ backlogs."""
    result = []
    for r in records:
        if len(r.fail_subjects) >= 2:
            result.append(RiskStudent(
                enrollment=r.enrollment, name=r.name, branch=r.branch_full or r.branch,
                sgpa=r.sgpa or 0.0, cgpa=r.cgpa or 0.0,
                backlog_count=len(r.fail_subjects), risk_type="multi_backlog"
            ))
    return sorted(result, key=lambda x: x.backlog_count, reverse=True)


def _compute_heatmap(records: List[StudentRecord]) -> Dict[str, Dict[str, float]]:
    """Branch × Subject average grade point matrix for heatmap rendering."""
    matrix: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

    for r in records:
        branch = r.branch or "XX"
        for code, grade in r.subjects.items():
            gp = GRADE_POINTS.get(grade.strip().upper(), 5.0)
            matrix[branch][code].append(gp)

    # Average out
    result = {}
    for branch, subjects in matrix.items():
        result[branch] = {}
        for subj, gps in subjects.items():
            result[branch][subj] = round(statistics.mean(gps), 2) if gps else 0.0

    return result


def _compute_comparison(current: List[StudentRecord], previous: List[StudentRecord]) -> Dict[str, Any]:
    """Compare current vs previous job results."""
    curr_overall = _compute_overall(current)
    prev_overall = _compute_overall(previous)

    curr_branches = {b.branch_code: b for b in _compute_branch_stats(current)}
    prev_branches = {b.branch_code: b for b in _compute_branch_stats(previous)}

    branch_deltas = {}
    for code in set(list(curr_branches.keys()) + list(prev_branches.keys())):
        curr_b = curr_branches.get(code)
        prev_b = prev_branches.get(code)
        if curr_b and prev_b:
            branch_deltas[code] = {
                "name": curr_b.branch_name,
                "sgpa_delta": round(curr_b.average_sgpa - prev_b.average_sgpa, 2),
                "pass_pct_delta": round(curr_b.pass_percentage - prev_b.pass_percentage, 2),
            }

    return {
        "sgpa_delta": round(curr_overall.average_sgpa - prev_overall.average_sgpa, 2),
        "cgpa_delta": round(curr_overall.average_cgpa - prev_overall.average_cgpa, 2),
        "pass_pct_delta": round(curr_overall.pass_percentage - prev_overall.pass_percentage, 2),
        "prev_pass_pct": prev_overall.pass_percentage,
        "curr_pass_pct": curr_overall.pass_percentage,
        "prev_avg_sgpa": prev_overall.average_sgpa,
        "curr_avg_sgpa": curr_overall.average_sgpa,
        "prev_total": prev_overall.total_students,
        "curr_total": curr_overall.total_students,
        "branch_deltas": branch_deltas,
    }
