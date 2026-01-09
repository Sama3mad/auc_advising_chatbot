# tools/course_tools.py
"""
Course Tools
Basic course information retrieval tools
"""

from langchain_core.tools import tool
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from support.knowledge_base import get_knowledge_base

kb = get_knowledge_base()


@tool
def get_course_details(course_code: str) -> str:
    """
    Get detailed information for a course including code, title, credits, 
    prerequisites, description, and when offered.
    
    Args:
        course_code: Course code (e.g., "CSCE 1001")
        
    Returns:
        Formatted course details
    """
    course = kb.get_course_by_code(course_code)
    
    if not course:
        return f"Course {course_code} not found."
    
    return f"""Course Code: {course.get('course_code', '?')}
Title: {course.get('title', '?')}
Credits: {course.get('credits', '?')}
Prerequisites: {course.get('prerequisite_human_readable', 'None')}
Description: {course.get('canonical_description', 'No description available')}
When Offered: {course.get('when_offered', 'Not specified')}"""


@tool
def get_course_prerequisites(course_code: str) -> str:
    """
    Get prerequisites for a course.
    
    Args:
        course_code: Course code (e.g., "CSCE 3312")
        
    Returns:
        Course prerequisites
    """
    course = kb.get_course_by_code(course_code)
    
    if not course:
        return f"Course {course_code} not found."
    
    prereqs = course.get("prerequisite_human_readable", "None")
    return f"{course['course_code']}: {course['title']}\nPrerequisites: {prereqs}"


@tool
def get_course_corequisites(course_code: str) -> str:
    """
    Get corequisites (courses that must be taken together) for a course.
    
    Args:
        course_code: Course code
        
    Returns:
        Course corequisites
    """
    course = kb.get_course_by_code(course_code)
    
    if not course:
        return f"Course {course_code} not found."
    
    coreq_ids = kb.get_corequisites(course_code)
    
    if not coreq_ids:
        return f"{course['course_code']}: {course['title']}\nCorequisites: None"
    
    coreq_courses = []
    for coreq_id in coreq_ids:
        coreq_course = kb.get_course_by_master_id(coreq_id)
        if coreq_course:
            coreq_courses.append(f"{coreq_course['course_code']} ({coreq_course['title']})")
    
    coreqs_str = ", ".join(coreq_courses) if coreq_courses else "None"
    return f"{course['course_code']}: {course['title']}\nCorequisites: {coreqs_str}"


@tool
def get_course_equivalencies(course_code: str) -> str:
    """
    Find equivalent courses for the given course code.
    
    Args:
        course_code: Course code
        
    Returns:
        Equivalent courses
    """
    course = kb.get_course_by_code(course_code)
    
    if not course:
        return f"Course {course_code} not found."
    
    equiv_ids = kb.get_equivalencies(course_code)
    
    if not equiv_ids:
        return f"{course['course_code']}: {course['title']}\nEquivalent Courses: None"
    
    equiv_courses = []
    for equiv_id in equiv_ids:
        equiv_course = kb.get_course_by_master_id(equiv_id)
        if equiv_course:
            equiv_courses.append(f"{equiv_course['course_code']} ({equiv_course['title']})")
    
    equivs_str = ", ".join(equiv_courses) if equiv_courses else "None"
    return f"{course['course_code']}: {course['title']}\nEquivalent Courses: {equivs_str}"


@tool
def find_courses_that_require(course_code: str) -> str:
    """
    Find all courses that have the given course as a prerequisite.
    
    Args:
        course_code: Course code
        
    Returns:
        List of courses that require this course
    """
    course = kb.get_course_by_code(course_code)
    
    if not course:
        return f"Course {course_code} not found."
    
    course_master_id = course.get("course_master_id")
    dependent_courses = kb.find_courses_requiring(course_master_id)
    
    if not dependent_courses:
        return f"{course['course_code']} is not a prerequisite for any courses."
    
    result = f"Courses that require {course['course_code']} as a prerequisite:\n\n"
    for dep_course in dependent_courses:
        result += f"- {dep_course.get('course_code', '?')}: {dep_course.get('title', '?')}\n"
    
    return result