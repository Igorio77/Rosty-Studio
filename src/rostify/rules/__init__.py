"""Rule base, registry, engine, and builtin rules.

No Qt imports allowed in this package — see CLAUDE.md layer boundaries. The
settings UI (rostify.ui) builds its forms from `Rule.param_schema` at
runtime; it must never need a code change here to display a new rule's
parameters.
"""
