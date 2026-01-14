# agents/policy_agent.py
"""
Policy & Core Rules Agent
Handles questions about AUC core curriculum rules, academic policies,
registration holds, probation/dismissal, Arabic requirement, leaves, etc.
"""

from langchain_openai import ChatOpenAI
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import KWAIPILOT_API_KEY, LLM_MODEL, LLM_TEMPERATURE, MAX_ITERATIONS  # type: ignore
from support.context_manager import ContextManager
from support.knowledge_base import KnowledgeBase
from tools.policy_tools import POLICY_TOOLS, POLICY_TOOL_DESCRIPTIONS


class PolicyAgent:
    """
    Specialized agent for university policies and core rules.
    Uses MongoDB-backed rules from data/policies/core_rules.json.
    """

    def __init__(self, context_manager: ContextManager, knowledge_base: KnowledgeBase) -> None:
        """
        Initialize Policy Agent.
        """
        self.llm = ChatOpenAI(
            model=LLM_MODEL,
            api_key=KWAIPILOT_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=LLM_TEMPERATURE,
        )

        self.context_manager = context_manager
        self.knowledge_base = knowledge_base
        self.max_iterations = MAX_ITERATIONS

        # Map tool names to tool functions
        self.available_tools = {tool.name: tool for tool in POLICY_TOOLS}

        # Agent name for tracking
        self.name = "Policy & Core Rules Agent"

    def process(self, question: str) -> str:
        """
        Process a policy-related question.
        """
        # Track that this agent was used
        self.context_manager.add_agent_used(self.name)

        # Get student context if available
        student_context = self.context_manager.get_context_summary()

        # Use iterative agent loop
        return self._iterative_process(question, student_context)

    def _iterative_process(self, question: str, student_context: str) -> str:
        """
        Iterative processing loop - agent can use multiple tools.
        """
        tool_results = []

        for _ in range(self.max_iterations):
            context = f"Original Question: {question}\n\n"

            if student_context:
                context += f"Student Context:\n{student_context}\n\n"

            if tool_results:
                context += "Information gathered so far:\n"
                for i, result in enumerate(tool_results, 1):
                    context += f"{i}. {result}\n\n"

            decision = self._make_decision(context)

            # Final answer
            if decision.get("action") == "answer":
                return decision.get("response", "No response provided.")

            # Tool calls
            if decision.get("action") == "tool_call":
                for call in decision.get("tools", []):
                    tool_name = call.get("tool")
                    tool_args = call.get("args", {})

                    if tool_name in self.available_tools:
                        try:
                            result = self.available_tools[tool_name].invoke(tool_args)
                            tool_results.append(f"[{tool_name}] {result}")
                        except Exception as e:  # pragma: no cover - defensive
                            tool_results.append(f"Error calling {tool_name}: {e}")

        # If max iterations reached
        if tool_results:
            return "Based on the policies I found:\n\n" + "\n\n".join(tool_results)
        return "I couldn't find enough policy information to answer your question."

    def _make_decision(self, context: str) -> dict:
        """
        Let LLM decide what to do next.
        """
        system_prompt = (
            "You are an academic policy specialist for AUC advising.\n\n"
            + POLICY_TOOL_DESCRIPTIONS
            + """

Your task:
1. Analyze the question and information gathered so far.
2. Decide if you need more information or if you can answer.
3. Choose appropriate tools - you can use multiple tools in one iteration.

Respond with JSON in ONE of these formats:

Format 1 - To call tools:
{"action": "tool_call", "tools": [{"tool": "tool_name", "args": {}}]}

Format 2 - To provide final answer:
{"action": "answer", "response": "your final answer"}

CRITICAL RULES:
- For questions about Core Curriculum rules, freshman/secondary/capstone requirements,
  double counting, declaration rules, Arabic requirement, registration holds, probation,
  leaves of absence, withdrawal, transcripts, etc., use the policy tools.
- Prefer get_policy_rule when the question is clearly about a specific section you recognize.
- Use search_policies_by_tag and search_policies_by_keyword to discover relevant sections.
- Keep answers concise but precise, and quote key policy sentences when relevant.
- Respond ONLY with valid JSON, no markdown code fences.

Context:
"""
            + context
        )

        decision_str = self.llm.invoke(system_prompt).content

        decision_clean = decision_str.strip()
        if decision_clean.startswith("```json"):
            decision_clean = decision_clean[7:]
        if decision_clean.startswith("```"):
            decision_clean = decision_clean[3:]
        if decision_clean.endswith("```"):
            decision_clean = decision_clean[:-3]
        decision_clean = decision_clean.strip()

        try:
            return json.loads(decision_clean)
        except json.JSONDecodeError:
            return {
                "action": "answer",
                "response": "I encountered an error processing your policy question. Please try rephrasing.",
            }


