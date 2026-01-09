# agents/__init__.py
from .course_info_agent import CourseInfoAgent
from .academic_planning_agent import AcademicPlanningAgent  # NEW

__all__ = [
    'CourseInfoAgent',
    'AcademicPlanningAgent', 
    'RouterAgent',
]