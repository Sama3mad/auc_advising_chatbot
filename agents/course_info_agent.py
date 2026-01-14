# agents/course_info_agent.py
"""
Course Information Agent
Handles all course-related queries: details, prerequisites, search, etc.
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import KWAIPILOT_API_KEY, LLM_MODEL, LLM_TEMPERATURE, MAX_ITERATIONS
from support.context_manager import ContextManager
from support.knowledge_base import KnowledgeBase
from tools import COURSE_INFO_TOOLS, TOOL_DESCRIPTIONS


class CourseInfoAgent:
    """
    Specialized agent for course information queries.
    Can answer questions about courses, prerequisites, search for courses, etc.
    """
    
    def __init__(self, context_manager: ContextManager, knowledge_base: KnowledgeBase):
        """
        Initialize Course Info Agent
        
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
        self.available_tools = {tool.name: tool for tool in COURSE_INFO_TOOLS}
        
        # Agent name for tracking
        self.name = "Course Information Agent"
    
    def process(self, question: str) -> str:
        """
        Process a course-related question
        
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
        # Build the system prompt WITHOUT template variables in the JSON examples
        system_prompt = """You are a course information specialist for AUC advising.

""" + TOOL_DESCRIPTIONS + """

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
- When asked "Can I take course X if I have completed Y and Z?", use check_prerequisites_satisfied
- When asked "Can I take course X without course Y?", use check_if_course_required_for
- Use predefined tools first whenever possible
- Use query_database_directly only when you need custom search criteria
- For questions about courses that must be taken together, use get_course_corequisites
- Respond ONLY with valid JSON, no markdown code fences

Context:
""" + context
        
        # Use the LLM directly without template
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