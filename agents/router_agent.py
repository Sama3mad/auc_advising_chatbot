# agents/router_agent.py
"""
Router Agent
Analyzes user questions and routes them to the appropriate specialized agent
"""

from langchain_google_genai import ChatGoogleGenerativeAI
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import GOOGLE_API_KEY, LLM_MODEL, LLM_TEMPERATURE
from support.context_manager import ContextManager
from support.knowledge_base import KnowledgeBase


class RouterAgent:
    """
    Router Agent that analyzes questions and routes to specialized agents.
    This is the entry point for all user queries.
    """
    
    def __init__(self, context_manager: ContextManager, knowledge_base: KnowledgeBase, agents: dict):
        """
        Initialize Router Agent
        
        Args:
            context_manager: Context manager instance
            knowledge_base: Knowledge base instance
            agents: Dictionary of available agents {"agent_name": agent_instance}
        """
        self.llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=LLM_TEMPERATURE
        )
        
        self.context_manager = context_manager
        self.knowledge_base = knowledge_base
        self.agents = agents
        
        # Agent name for tracking
        self.name = "Router Agent"
    
    def route(self, question: str) -> str:
        """
        Route a question to the appropriate agent
        
        Args:
            question: User's question
            
        Returns:
            Response from the appropriate agent
        """
        # Get student context
        student_context = self.context_manager.get_context_summary()
        
        # Decide which agent to use
        agent_decision = self._classify_question(question, student_context)
        
        agent_name = agent_decision.get("agent")
        reasoning = agent_decision.get("reasoning", "")
        
        # Route to the appropriate agent
        if agent_name in self.agents:
            print(f"[Router] Routing to: {agent_name}")
            if reasoning:
                print(f"[Router] Reason: {reasoning}")
            return self.agents[agent_name].process(question)
        else:
            # Fallback - try to answer directly or use course info agent as default
            if "course_info" in self.agents:
                print(f"[Router] Using default agent: Course Information Agent")
                return self.agents["course_info"].process(question)
            else:
                return "I'm not sure which agent can help with that question. Please try rephrasing."
    
    def _classify_question(self, question: str, student_context: str) -> dict:
        """
        Classify the question and decide which agent should handle it
        
        Args:
            question: User's question
            student_context: Student information context
            
        Returns:
            Dictionary with agent name and reasoning
        """
        system_prompt = """You are a routing assistant for an academic advising chatbot.

Available Agents:
1. "course_info" - Course Information Agent
   - Handles: Course details, prerequisites, corequisites, course search
   - Examples: "What are the prerequisites for CSCE 3312?", "Tell me about CSCE 1001", "Search for database courses"
   
2. "academic_planning" - Academic Planning Agent
   - Handles: Degree requirements, catalog information, specializations, credit requirements, degree progress
   - Examples: "How many credits do I need?", "What are the core requirements?", "What specializations are available?", "What courses do I need for CE?"

Your task:
Analyze the question and decide which agent should handle it.

Respond with JSON in this format:
{"agent": "agent_name", "reasoning": "brief explanation"}

Rules:
- Questions about SPECIFIC COURSES (by code like CSCE 3312) → "course_info"
- Questions about PREREQUISITES or COREQUISITES → "course_info"
- Questions about SEARCHING courses → "course_info"
- Questions about DEGREE REQUIREMENTS or CREDIT HOURS → "academic_planning"
- Questions about SPECIALIZATIONS → "academic_planning"
- Questions about CATALOGS or PROGRAM REQUIREMENTS → "academic_planning"
- Questions about DEGREE PROGRESS → "academic_planning"
- If unclear, default to "course_info"

Question: """ + question + """

Student Context: """ + student_context + """

Respond ONLY with valid JSON, no markdown fences."""
        
        # Use LLM to classify
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
            # Fallback to course_info if parsing fails
            return {
                "agent": "course_info",
                "reasoning": "Failed to parse routing decision, using default"
            }