# tools/policy_tools.py
"""
Policy / Core Rules Tools
LangChain tools for querying AUC core academic rules and policies.
"""

from langchain_core.tools import tool
import sys
import os
from typing import List, Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from support.knowledge_base import get_knowledge_base


kb = get_knowledge_base()


def _format_rule(rule: Dict[str, Any]) -> str:
    """Format a single rule document into human-readable text."""
    lines: List[str] = []
    rule_id = rule.get("_id", "")
    section = rule.get("section", "")
    applies_to = ", ".join(rule.get("applies_to", [])) or "unspecified"
    tags = ", ".join(rule.get("tags", [])) or "none"

    lines.append(f"Section: {section} (ID: {rule_id})")
    lines.append(f"Applies to: {applies_to}")
    lines.append(f"Tags: {tags}")
    lines.append("")
    lines.append("Rules:")
    for i, r in enumerate(rule.get("rules", []), 1):
        lines.append(f"{i}. {r}")

    return "\n".join(lines)


@tool
def get_policy_rule(rule_id: str) -> str:
    """
    Get a specific core policy/rule by its ID.

    Args:
        rule_id: Rule identifier (e.g., "freshman_level_requirements",
                 "major_declaration_progression", "arabic_language_requirement")

    Returns:
        Formatted rule text, or a not-found message.
    """
    rule = kb.get_rule_by_id(rule_id.strip())
    if not rule:
        return f"No rule found with ID '{rule_id}'."
    return _format_rule(rule)


@tool
def search_policies_by_tag(tag: str) -> str:
    """
    Search core rules/policies by tag.

    Args:
        tag: Tag keyword (e.g., "freshman", "declaration", "registration_hold",
             "double_counting", "capstone")

    Returns:
        A formatted list of matching rule sections and brief summaries.
    """
    rules = kb.search_rules_by_tag(tag)
    if not rules:
        return f"No policies found for tag '{tag}'."

    lines: List[str] = [f"Policies with tag '{tag}':", ""]
    for rule in rules:
        lines.append(f"- {rule.get('section', '')} (ID: {rule.get('_id', '')})")
    lines.append("")
    lines.append("Use get_policy_rule(rule_id) to see full details of a specific rule.")
    return "\n".join(lines)


@tool
def search_policies_by_keyword(keyword: str) -> str:
    """
    Search core rules/policies by keyword in section title or rule text.

    Args:
        keyword: Text to search for (e.g., "Arabic", "probation", "leave", "transcript")

    Returns:
        A formatted list of matching rules with highlights.
    """
    rules = kb.search_rules_by_keyword(keyword)
    if not rules:
        return f"No policies found containing '{keyword}'."

    lines: List[str] = [f"Policies mentioning '{keyword}':", ""]
    for rule in rules:
        lines.append(f"- {rule.get('section', '')} (ID: {rule.get('_id', '')})")
    lines.append("")
    lines.append("Use get_policy_rule(rule_id) to see full details of a specific rule.")
    return "\n".join(lines)


@tool
def list_policy_sections() -> str:
    """
    List all available policy sections and their IDs.

    Returns:
        A list of all rule sections with IDs, suitable for browsing.
    """
    sections = kb.list_rule_sections()
    if not sections:
        return "No policy sections found in the database."

    lines: List[str] = ["Available policy sections:", ""]
    for s in sections:
        lines.append(f"- {s['section']} (ID: {s['id']})")
    return "\n".join(lines)


POLICY_TOOLS = [
    get_policy_rule,
    search_policies_by_tag,
    search_policies_by_keyword,
    list_policy_sections,
]


POLICY_TOOL_DESCRIPTIONS = """
Available Tools for Policies & Core Rules:

1. get_policy_rule(rule_id: str)
   - Get the full text of a specific policy/rule by its ID.
   - Example: get_policy_rule("freshman_level_requirements")

2. search_policies_by_tag(tag: str)
   - Search policies by tag (e.g., "freshman", "declaration", "registration_hold",
     "double_counting", "capstone").
   - Example: search_policies_by_tag("declaration")

3. search_policies_by_keyword(keyword: str)
   - Search policies by keyword in section title or rule text.
   - Example: search_policies_by_keyword("Arabic")

4. list_policy_sections()
   - List all available policy sections with their IDs.
"""


