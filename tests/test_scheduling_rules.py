from datetime import datetime

from rostify.core.models import Assignment, Employee, Layer
from rostify.core.schedule import Schedule
from rostify.rules.base import Severity
from rostify.rules.builtin.position_rotation_eligibility import PositionRotationEligibilityRule
from rostify.rules.builtin.position_time_step import PositionTimeStepRule
from rostify.rules.builtin.rest_period import RestPeriodRule
from rostify.rules.builtin.weekly_hours_threshold import WeeklyHoursThresholdRule
from rostify.rules.registry import RuleRegistry


def make_assignment(
    employee_id="E1",
    day=1,
    start_hour=8,
    start_minute=0,
    end_hour=16,
    end_minute=0,
    layer=Layer.SHIFT,
    resource="S1",
):
    return Assignment(
        employee_id=employee_id,
        start=datetime(2026, 1, day, start_hour, start_minute),
        end=datetime(2026, 1, day, end_hour, end_minute),
        resource=resource,
        layer=layer,
    )


def test_registry_discovers_all_new_rules():
    classes = RuleRegistry().all_rule_classes()
    for rule_id in (
        "rest_period",
        "position_rotation_eligibility",
        "position_time_step",
        "weekly_hours_threshold",
    ):
        assert rule_id in classes


# --- rest_period -----------------------------------------------------


def test_rest_period_flags_short_gap_between_shifts():
    rule = RestPeriodRule(params={"min_rest_hours": 10.0})
    schedule = Schedule()
    schedule.add_assignment(make_assignment(day=1, start_hour=8, end_hour=16))

    candidate = make_assignment(day=1, start_hour=18, end_hour=23)  # 2h gap
    violations = rule.evaluate(candidate, schedule)
    assert len(violations) == 1
    assert violations[0].rule_id == "rest_period"


def test_rest_period_passes_sufficient_gap():
    rule = RestPeriodRule(params={"min_rest_hours": 10.0})
    schedule = Schedule()
    schedule.add_assignment(make_assignment(day=1, start_hour=8, end_hour=16))

    candidate = make_assignment(day=2, start_hour=6, end_hour=14)  # 14h gap
    assert rule.evaluate(candidate, schedule) == []


def test_rest_period_ignores_overlaps_and_position_layer():
    rule = RestPeriodRule()
    schedule = Schedule()
    schedule.add_assignment(make_assignment(day=1, start_hour=8, end_hour=16))

    overlapping = make_assignment(day=1, start_hour=10, end_hour=12)
    assert rule.evaluate(overlapping, schedule) == []  # duplicate_assignment's job

    position = make_assignment(day=1, start_hour=17, end_hour=18, layer=Layer.POSITION)
    assert rule.evaluate(position, schedule) == []


# --- position_rotation_eligibility ------------------------------------


def test_eligibility_flags_non_dealer_position_assignment():
    rule = PositionRotationEligibilityRule()
    schedule = Schedule()
    schedule.add_employee(Employee(id="E1", first_name="Sam", last_name="Cashier", subdepartment="Cashiers"))

    assignment = make_assignment(layer=Layer.POSITION)
    violations = rule.evaluate(assignment, schedule)
    assert len(violations) == 1
    assert violations[0].severity == Severity.HARD


def test_eligibility_passes_dealer_position_assignment():
    rule = PositionRotationEligibilityRule()
    schedule = Schedule()
    schedule.add_employee(Employee(id="E1", first_name="Alex", last_name="Rivera", subdepartment="Dealers"))

    assignment = make_assignment(layer=Layer.POSITION)
    assert rule.evaluate(assignment, schedule) == []


def test_eligibility_ignores_shift_layer():
    rule = PositionRotationEligibilityRule()
    schedule = Schedule()
    schedule.add_employee(Employee(id="E1", first_name="Sam", last_name="Cashier", subdepartment="Cashiers"))

    assignment = make_assignment(layer=Layer.SHIFT)
    assert rule.evaluate(assignment, schedule) == []


# --- position_time_step -----------------------------------------------


def test_time_step_flags_misaligned_start_and_duration():
    rule = PositionTimeStepRule(params={"time_step_minutes": 15})
    schedule = Schedule()
    assignment = make_assignment(
        start_hour=10, start_minute=7, end_hour=10, end_minute=40, layer=Layer.POSITION
    )
    violations = rule.evaluate(assignment, schedule)
    assert len(violations) == 2
    assert all(v.severity == Severity.SOFT for v in violations)


def test_time_step_passes_aligned_assignment():
    rule = PositionTimeStepRule(params={"time_step_minutes": 15})
    schedule = Schedule()
    assignment = make_assignment(
        start_hour=10, start_minute=0, end_hour=10, end_minute=45, layer=Layer.POSITION
    )
    assert rule.evaluate(assignment, schedule) == []


def test_time_step_ignores_shift_layer():
    rule = PositionTimeStepRule(params={"time_step_minutes": 15})
    schedule = Schedule()
    assignment = make_assignment(start_hour=10, start_minute=7, end_hour=18, end_minute=13, layer=Layer.SHIFT)
    assert rule.evaluate(assignment, schedule) == []


# --- weekly_hours_threshold --------------------------------------------


def test_weekly_hours_threshold_flags_when_reached():
    rule = WeeklyHoursThresholdRule(params={"max_weekly_hours": 20.0})
    schedule = Schedule()
    # Monday 2026-01-05, 8h shift already on the books.
    schedule.add_assignment(make_assignment(day=5, start_hour=0, end_hour=8))

    candidate = make_assignment(day=6, start_hour=0, end_hour=13)  # +13h = 21h total
    violations = rule.evaluate(candidate, schedule)
    assert len(violations) == 1
    assert violations[0].severity == Severity.SOFT


def test_weekly_hours_threshold_passes_under_limit():
    rule = WeeklyHoursThresholdRule(params={"max_weekly_hours": 40.0})
    schedule = Schedule()
    candidate = make_assignment(day=5, start_hour=0, end_hour=8)
    assert rule.evaluate(candidate, schedule) == []


def test_weekly_hours_threshold_resets_across_iso_weeks():
    rule = WeeklyHoursThresholdRule(params={"max_weekly_hours": 20.0})
    schedule = Schedule()
    # Sunday 2026-01-04 (end of the previous ISO week) — shouldn't count
    # toward the Monday-starting week the candidate falls in.
    schedule.add_assignment(make_assignment(day=4, start_hour=0, end_hour=20))

    candidate = make_assignment(day=5, start_hour=0, end_hour=8)  # Monday, 8h
    assert rule.evaluate(candidate, schedule) == []
