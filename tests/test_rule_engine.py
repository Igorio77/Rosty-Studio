from datetime import datetime

from rostify.core.models import Assignment, Layer
from rostify.core.schedule import Schedule
from rostify.rules.base import Severity
from rostify.rules.builtin.crew_id_format import CrewIdFormatRule
from rostify.rules.builtin.duplicate_assignment import DuplicateAssignmentRule
from rostify.rules.builtin.max_length import MaxLengthRule
from rostify.rules.engine import RuleEngine
from rostify.rules.registry import RuleRegistry


def make_assignment(employee_id="E1", start_hour=8, end_hour=16, resource="S1", comment=""):
    return Assignment(
        employee_id=employee_id,
        start=datetime(2026, 1, 1, start_hour),
        end=datetime(2026, 1, 1, end_hour),
        resource=resource,
        layer=Layer.SHIFT,
        comment=comment,
    )


def test_registry_discovers_all_builtin_rules():
    registry = RuleRegistry()
    classes = registry.all_rule_classes()
    assert "max_length" in classes
    assert "crew_id_format" in classes
    assert "duplicate_assignment" in classes


def test_max_length_rule_flags_long_resource():
    rule = MaxLengthRule(params={"resource_max_len": 5, "comment_max_len": 100})
    schedule = Schedule()
    assignment = make_assignment(resource="THIS-IS-WAY-TOO-LONG")
    violations = rule.evaluate(assignment, schedule)
    assert len(violations) == 1
    assert violations[0].rule_id == "max_length"
    assert violations[0].severity == Severity.HARD


def test_max_length_rule_passes_short_values():
    rule = MaxLengthRule()
    schedule = Schedule()
    assignment = make_assignment(resource="B1")
    assert rule.evaluate(assignment, schedule) == []


def test_crew_id_format_rule_flags_non_numeric_id():
    rule = CrewIdFormatRule()
    schedule = Schedule()
    assignment = make_assignment(employee_id="not-a-number")
    violations = rule.evaluate(assignment, schedule)
    assert len(violations) == 1


def test_crew_id_format_rule_accepts_numeric_id():
    rule = CrewIdFormatRule()
    schedule = Schedule()
    assignment = make_assignment(employee_id="18293")
    assert rule.evaluate(assignment, schedule) == []


def test_duplicate_assignment_rule_flags_overlap():
    rule = DuplicateAssignmentRule()
    schedule = Schedule()
    existing = make_assignment(start_hour=8, end_hour=16)
    schedule.add_assignment(existing)

    candidate = make_assignment(start_hour=10, end_hour=12)
    violations = rule.evaluate(candidate, schedule)
    assert len(violations) == 1
    assert violations[0].severity == Severity.HARD


def test_rule_engine_blocks_on_hard_violation():
    registry = RuleRegistry()
    crew_id_rule_cls = registry.get("crew_id_format")
    engine = RuleEngine([crew_id_rule_cls()])

    schedule = Schedule()
    bad_assignment = make_assignment(employee_id="oops")
    violations = engine.evaluate(bad_assignment, schedule)

    assert engine.has_hard_violation(violations)


def test_rule_engine_skips_disabled_rules():
    rule = MaxLengthRule(params={"resource_max_len": 1, "comment_max_len": 1})
    rule.enabled = False
    engine = RuleEngine([rule])

    schedule = Schedule()
    assignment = make_assignment(resource="way too long for a max of one char")
    assert engine.evaluate(assignment, schedule) == []
