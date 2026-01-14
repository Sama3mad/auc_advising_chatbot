from support.context_manager import ContextManager
from support.knowledge_base import KnowledgeBase
from agents.academic_planning_agent import AcademicPlanningAgent

# Initialize
context = ContextManager()
kb = KnowledgeBase()
planning_agent = AcademicPlanningAgent(context, kb)

# Test questions
questions = [
    "How many credits do I need for Computer Engineering?",
    "What specializations are available for CE?",
    "What are the core requirements for CE?",
    "What are the requirements for AI specialization?",
]

for q in questions:
    print(f"\nQ: {q}")
    response = planning_agent.process(q)
    print(f"A: {response}\n" + "="*50)

kb.close()