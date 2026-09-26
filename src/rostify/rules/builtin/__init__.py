"""Builtin rules, discovered automatically by rostify.rules.registry.

Every rule here traces to docs/01-analysis.md §4.1 ("directly portable" —
real, currently-enforced rules found in the production workbook's export
logic), ported as behavior, not as VBA-translated code. §4.3 of that same
document lists the rules that do NOT exist yet anywhere (double-booking
beyond exact overlap, rest periods, max hours, qualification matching) —
those still need to be defined with the domain expert before they can be
added here.
"""
