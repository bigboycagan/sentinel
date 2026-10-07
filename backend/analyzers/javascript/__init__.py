"""JavaScript / TypeScript analyzer: tree-sitter AST based. Parses only, never executes.

tree-sitter is a pure parsing library: it builds a syntax tree from bytes and
has no evaluation facility, so analyzed code can never run. The same
Rule/RuleHit contract as the Python analyzer applies, so scoring, the rules
catalog and the API are shared unchanged.
"""
