# support/context_manager.py
"""
Context Manager
Stores conversation state and student information across the conversation
Prevents agents from asking repetitive questions
"""

from typing import List, Dict, Optional, Any
from datetime import datetime


class ContextManager:
    """
    Manages conversation context and student information.
    Stores data temporarily for the duration of a conversation.
    """
    
    def __init__(self):
        """Initialize empty context"""
        self.context = {
            "student_info": {
                "major": None,
                "minor": None,
                "catalog_year": None,
                "completed_courses": [],
                "current_semester": None,
                "gpa": None,
            },
            "conversation_history": [],
            "agents_consulted": [],
            "session_start": datetime.now().isoformat(),
        }
    
    # ============ STUDENT INFORMATION METHODS ============
    
    def set_major(self, major: str):
        """Set student's major"""
        self.context["student_info"]["major"] = major.upper()
    
    def get_major(self) -> Optional[str]:
        """Get student's major"""
        return self.context["student_info"]["major"]
    
    def set_minor(self, minor: str):
        """Set student's minor"""
        self.context["student_info"]["minor"] = minor.upper()
    
    def get_minor(self) -> Optional[str]:
        """Get student's minor"""
        return self.context["student_info"]["minor"]
    
    def set_catalog_year(self, year: int):
        """Set student's catalog year"""
        self.context["student_info"]["catalog_year"] = year
    
    def get_catalog_year(self) -> Optional[int]:
        """Get student's catalog year"""
        return self.context["student_info"]["catalog_year"]
    
    def set_completed_courses(self, courses: List[str]):
        """
        Set list of completed courses
        
        Args:
            courses: List of course codes (e.g., ["CSCE 1001", "MATH 1501"])
        """
        # Normalize course codes to uppercase
        self.context["student_info"]["completed_courses"] = [c.strip().upper() for c in courses]
    
    def add_completed_course(self, course_code: str):
        """Add a single completed course"""
        course_code = course_code.strip().upper()
        if course_code not in self.context["student_info"]["completed_courses"]:
            self.context["student_info"]["completed_courses"].append(course_code)
    
    def get_completed_courses(self) -> List[str]:
        """Get list of completed courses"""
        return self.context["student_info"]["completed_courses"]
    
    def has_completed_course(self, course_code: str) -> bool:
        """Check if student has completed a specific course"""
        course_code = course_code.strip().upper()
        return course_code in self.context["student_info"]["completed_courses"]
    
    def set_gpa(self, gpa: float):
        """Set student's GPA"""
        self.context["student_info"]["gpa"] = gpa
    
    def get_gpa(self) -> Optional[float]:
        """Get student's GPA"""
        return self.context["student_info"]["gpa"]
    
    def set_current_semester(self, semester: str):
        """Set current semester (e.g., 'Fall 2024')"""
        self.context["student_info"]["current_semester"] = semester
    
    def get_current_semester(self) -> Optional[str]:
        """Get current semester"""
        return self.context["student_info"]["current_semester"]
    
    # ============ BULK UPDATE METHODS ============
    
    def update_student_info(self, **kwargs):
        """
        Update multiple student info fields at once
        
        Args:
            **kwargs: Any of: major, minor, catalog_year, completed_courses, gpa, current_semester
        """
        if "major" in kwargs:
            self.set_major(kwargs["major"])
        if "minor" in kwargs:
            self.set_minor(kwargs["minor"])
        if "catalog_year" in kwargs:
            self.set_catalog_year(kwargs["catalog_year"])
        if "completed_courses" in kwargs:
            self.set_completed_courses(kwargs["completed_courses"])
        if "gpa" in kwargs:
            self.set_gpa(kwargs["gpa"])
        if "current_semester" in kwargs:
            self.set_current_semester(kwargs["current_semester"])
    
    def get_student_info(self) -> Dict[str, Any]:
        """Get all student information"""
        return self.context["student_info"].copy()
    
    # ============ CONVERSATION HISTORY METHODS ============
    
    def add_message(self, role: str, message: str):
        """
        Add a message to conversation history
        
        Args:
            role: Either "user" or "assistant"
            message: The message content
        """
        self.context["conversation_history"].append({
            "role": role,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get full conversation history"""
        return self.context["conversation_history"].copy()
    
    def get_last_n_messages(self, n: int) -> List[Dict[str, str]]:
        """Get last N messages from conversation"""
        return self.context["conversation_history"][-n:] if n > 0 else []
    
    # ============ AGENT TRACKING METHODS ============
    
    def add_agent_used(self, agent_name: str):
        """Track which agent was consulted"""
        if agent_name not in self.context["agents_consulted"]:
            self.context["agents_consulted"].append(agent_name)
    
    def get_agents_used(self) -> List[str]:
        """Get list of agents that have been consulted"""
        return self.context["agents_consulted"].copy()
    
    def was_agent_used(self, agent_name: str) -> bool:
        """Check if a specific agent was already used"""
        return agent_name in self.context["agents_consulted"]
    
    # ============ CONTEXT SUMMARY METHODS ============
    
    def get_full_context(self) -> Dict[str, Any]:
        """Get complete context (for debugging or passing to agents)"""
        return self.context.copy()
    
    def get_context_summary(self) -> str:
        """
        Get a human-readable summary of current context
        Useful for passing to LLM agents
        """
        summary = []
        
        student_info = self.context["student_info"]
        
        if student_info["major"]:
            summary.append(f"Major: {student_info['major']}")
        if student_info["minor"]:
            summary.append(f"Minor: {student_info['minor']}")
        if student_info["catalog_year"]:
            summary.append(f"Catalog Year: {student_info['catalog_year']}")
        if student_info["completed_courses"]:
            summary.append(f"Completed Courses: {', '.join(student_info['completed_courses'])}")
        if student_info["gpa"]:
            summary.append(f"GPA: {student_info['gpa']}")
        if student_info["current_semester"]:
            summary.append(f"Current Semester: {student_info['current_semester']}")
        
        if not summary:
            return "No student information available yet."
        
        return "\n".join(summary)
    
    # ============ UTILITY METHODS ============
    
    def clear(self):
        """Clear all context (start fresh conversation)"""
        self.__init__()
    
    def has_student_info(self) -> bool:
        """Check if any student information has been provided"""
        info = self.context["student_info"]
        return any([
            info["major"],
            info["minor"],
            info["catalog_year"],
            info["completed_courses"],
            info["gpa"],
            info["current_semester"]
        ])
    
    def __repr__(self):
        """String representation for debugging"""
        return f"ContextManager(messages={len(self.context['conversation_history'])}, has_info={self.has_student_info()})"