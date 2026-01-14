# agents/academic_planning_agent.py
"""
Academic Planning Agent
Handles degree planning, catalog requirements, specializations, and progress tracking
"""

from langchain_openai import ChatOpenAI
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import KWAIPILOT_API_KEY, LLM_MODEL, LLM_TEMPERATURE, MAX_ITERATIONS
from support.context_manager import ContextManager
from support.knowledge_base import KnowledgeBase
from tools.catalog_tools import (
    get_program_info,
    get_core_requirements,
    get_concentration_requirements,
    get_specialization_requirements,
    get_available_electives,
    calculate_degree_progress,
    list_available_catalogs,
    compare_catalog_changes,
)


# Catalog tools available to this agent
CATALOG_TOOLS = [
    get_program_info,
    get_core_requirements,
    get_concentration_requirements,
    get_specialization_requirements,
    get_available_electives,
    calculate_degree_progress,
    list_available_catalogs,
    compare_catalog_changes,
]

CATALOG_TOOL_DESCRIPTIONS = """
Available Tools for Academic Planning:

1. get_program_info(program_id: str, catalog_year: str = "2024-2025")
   - Get basic information about a program (CE, CS, etc.)
   - Returns: title, degree type, total credits, description, specializations

2. get_core_requirements(program_id: str, catalog_year: str = "2024-2025")
   - Get core curriculum requirements
   - Returns: freshman requirements, cultural foundations, secondary level

3. get_concentration_requirements(program_id: str, catalog_year: str = "2024-2025")
   - Get major-specific required courses
   - Returns: all required courses for the concentration

4. get_specialization_requirements(program_id: str, specialization_name: str, catalog_year: str = "2024-2025")
   - Get requirements for a specific specialization (Embedded Systems, AI, Cybersecurity)
   - Returns: specialization requirements and elective groups

5. get_available_electives(program_id: str, catalog_year: str = "2024-2025")
   - Get list of available elective courses
   - Returns: all elective options for the program

6. calculate_degree_progress(program_id: str, completed_courses: list, catalog_year: str = "2024-2025")
   - Calculate degree completion progress
   - Returns: credits completed, remaining, percentage, requirements status

7. list_available_catalogs()
   - List all available catalog years
   - Returns: all catalogs in the database

8. compare_catalog_changes(program_id: str, old_catalog: str, new_catalog: str)
   - Compare requirements between two catalog years
   - Returns: differences in requirements, credits, specializations

Common program_id values:
- "PROGRAM:CE_BS" - Computer Engineering
- "PROGRAM:CS_BS" - Computer Science (if available)
"""


class AcademicPlanningAgent:
    """
    Specialized agent for academic planning queries.
    Handles catalog requirements, degree progress, specializations.
    """
    
    def __init__(self, context_manager: ContextManager, knowledge_base: KnowledgeBase):
        """
        Initialize Academic Planning Agent
        
        Args:
            context_manager: Context manager instance
            knowledge_base: Knowledge base instance
        """
        self.llm = ChatOpenAI(
            model=LLM_MODEL,
            api_key=KWAIPILOT_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=LLM_TEMPERATURE
        )
        
        self.context_manager = context_manager
        self.knowledge_base = knowledge_base
        self.max_iterations = MAX_ITERATIONS
        
        # Map tool names to tool functions
        self.available_tools = {tool.name: tool for tool in CATALOG_TOOLS}
        
        # Agent name for tracking
        self.name = "Academic Planning Agent"
    
    def process(self, question: str) -> str:
        """
        Process an academic planning question
        
        Args:
            question: User's question
            
        Returns:
            Answer to the question
        """
        # Track that this agent was used
        self.context_manager.add_agent_used(self.name)
        
        # Get student context if available
        student_context = self.context_manager.get_context_summary()
        
        # Use iterative agent loop
        return self._iterative_process(question, student_context)
    
    def _iterative_process(self, question: str, student_context: str) -> str:
        """
        Iterative processing loop - agent can use multiple tools
        
        Args:
            question: User's question
            student_context: Student information context
            
        Returns:
            Final answer
        """
        tool_results = []
        
        for iteration in range(self.max_iterations):
            # Build context for this iteration
            context = f"Original Question: {question}\n\n"
            
            if student_context:
                context += f"Student Context:\n{student_context}\n\n"
            
            if tool_results:
                context += "Information gathered so far:\n"
                for i, result in enumerate(tool_results, 1):
                    context += f"{i}. {result}\n\n"
            
            # Agent decision making
            decision = self._make_decision(context)
            
            # Check if agent wants to provide final answer
            if decision.get("action") == "answer":
                return decision.get("response", "No response provided.")
            
            # Execute tools
            if decision.get("action") == "tool_call":
                tool_calls = decision.get("tools", [])
                
                for call in tool_calls:
                    tool_name = call.get("tool")
                    tool_args = call.get("args", {})
                    
                    if tool_name in self.available_tools:
                        try:
                            result = self.available_tools[tool_name].invoke(tool_args)
                            tool_results.append(f"[{tool_name}] {result}")
                        except Exception as e:
                            error_msg = f"Error calling {tool_name}: {e}"
                            tool_results.append(error_msg)
        
        # If max iterations reached, compile results
        if tool_results:
            return "Based on the information I found:\n\n" + "\n\n".join(tool_results)
        else:
            return "I couldn't find enough information to answer your question."
    
    def _make_decision(self, context: str) -> dict:
        """
        Let LLM decide what to do next
        
        Args:
            context: Current context including question and results so far
            
        Returns:
            Decision dictionary with action and parameters
        """
        system_prompt = """You are an academic planning specialist for AUC advising.

""" + CATALOG_TOOL_DESCRIPTIONS + """

Your task:
1. Analyze the question and information gathered so far
2. Decide if you need more information or if you can answer
3. Choose appropriate tools - you can use multiple tools in one iteration

Respond with JSON in ONE of these formats:

Format 1 - To call tools:
{"action": "tool_call", "tools": [{"tool": "tool_name", "args": {}}]}

Format 2 - To provide final answer:
{"action": "answer", "response": "your final answer"}

CRITICAL RULES:
- For "How many credits do I need?" questions, use get_program_info
- For "What are the requirements?" questions, use get_core_requirements or get_concentration_requirements
- For "What specializations are available?" use get_program_info
- For "What are the requirements for X specialization?" use get_specialization_requirements
- For "How many courses have I completed?" use calculate_degree_progress with student's completed courses
- If catalog year is not specified, default to "2024-2025"
- If program is not specified but student context shows major (CE/CS), infer the program_id
- Respond ONLY with valid JSON, no markdown code fences

Context:
""" + context
        
        # Use the LLM directly
        decision_str = self.llm.invoke(system_prompt).content
        
        # Clean markdown fences if present
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
        except json.JSONDecodeError as e:
            # If parsing fails, return error
            return {
                "action": "answer",
                "response": "I encountered an error processing your question. Please try rephrasing."
            }