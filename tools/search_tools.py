# tools/search_tools.py
"""
Search Tools
Course search and query tools
"""

from langchain_core.tools import tool
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from support.knowledge_base import get_knowledge_base

kb = get_knowledge_base()


@tool
def search_courses_by_department(department_code: str, limit: int = 10) -> str:
    """
    List courses for a specific department code (e.g., CSCE).
    
    Args:
        department_code: Department code (e.g., "CSCE", "MATH")
        limit: Maximum number of courses to return (default: 10)
        
    Returns:
        List of courses in the department
    """
    courses = kb.search_by_department(department_code, limit)
    
    if not courses:
        return f"No courses found for department {department_code}."
    
    result = f"Found {len(courses)} courses in {department_code} department:\n\n"
    for course in courses:
        result += f"- {course.get('course_code', '?')}: {course.get('title', '?')} ({course.get('credits', '?')} credits)\n"
    
    return result


@tool
def search_courses_by_keyword(keyword: str, limit: int = 10) -> str:
    """
    Search for courses by keyword in title or description.
    
    Args:
        keyword: Search keyword (e.g., "algorithms", "database")
        limit: Maximum number of courses to return (default: 10)
        
    Returns:
        List of courses matching the keyword
    """
    courses = kb.search_by_keyword(keyword, limit)
    
    if not courses:
        return f"No courses found matching keyword '{keyword}'."
    
    result = f"Found {len(courses)} courses matching '{keyword}':\n\n"
    for course in courses:
        result += f"- {course.get('course_code', '?')}: {course.get('title', '?')}\n"
    
    return result


@tool
def query_database_directly(mongodb_query: str) -> str:
    """
    Execute a MongoDB query directly on the courses collection when predefined tools are insufficient.
    The query should be a valid MongoDB query in JSON string format.
    
    Args:
        mongodb_query: MongoDB query as JSON string
        
    Example queries:
    - Find courses with 3 credits: '{"credits": 3}'
    - Find courses offered in Fall: '{"when_offered": {"$regex": "Fall", "$options": "i"}}'
    - Find 300-level CSCE courses: '{"course_code": {"$regex": "^CSCE 3", "$options": "i"}}'
    
    Returns:
        List of courses matching the query
    """
    try:
        query = json.loads(mongodb_query)
        courses = kb.execute_custom_query(query, limit=20)
        
        if not courses:
            return "No courses found matching the query."
        
        result = f"Found {len(courses)} courses:\n\n"
        for course in courses:
            result += f"- {course.get('course_code', '?')}: {course.get('title', '?')}\n"
            if 'credits' in course:
                result += f"  Credits: {course.get('credits')}\n"
            if 'when_offered' in course:
                result += f"  Offered: {course.get('when_offered')}\n"
            result += "\n"
        
        return result
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON query format. {str(e)}"
    except Exception as e:
        return f"Error executing query: {str(e)}"