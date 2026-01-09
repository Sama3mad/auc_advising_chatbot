# tools/__init__.py
"""
Tools module - Contains all LangChain tools that agents can use
"""

from .course_tools import (
    get_course_details,
    get_course_prerequisites,
    get_course_corequisites,
    get_course_equivalencies,
    find_courses_that_require,
)

from .prerequisite_tools import (
    check_prerequisites_satisfied,
    check_if_course_required_for,
    get_all_prerequisites_recursive,
)

from .search_tools import (
    search_courses_by_department,
    search_courses_by_keyword,
    query_database_directly,
)

# All available tools for Course Info Agent
COURSE_INFO_TOOLS = [
    get_course_details,
    get_course_prerequisites,
    get_course_corequisites,
    get_course_equivalencies,
    find_courses_that_require,
    check_prerequisites_satisfied,
    check_if_course_required_for,
    get_all_prerequisites_recursive,
    search_courses_by_department,
    search_courses_by_keyword,
    query_database_directly,
]

# Tool descriptions for LLM
TOOL_DESCRIPTIONS = """
Available Tools for Course Information:

1. get_course_details(course_code: str)
   - Get full details about a course (description, credits, when offered, etc.)

2. get_course_prerequisites(course_code: str)
   - Get direct prerequisites for a specific course

3. get_course_corequisites(course_code: str)
   - Get corequisites (courses that must be taken together) for a course

4. get_course_equivalencies(course_code: str)
   - Find equivalent courses

5. find_courses_that_require(course_code: str)
   - Find all courses that have this course as a prerequisite

6. check_prerequisites_satisfied(course_code: str, completed_courses: list)
   - **USE THIS for "Can I take X if I completed Y and Z?" questions**
   - Check if a student has satisfied prerequisites given their completed courses
   - Understands AND/OR logic in prerequisites
   - Example: check_prerequisites_satisfied("CSCE 3312", ["PHYS 2211", "MACT 3211"])

7. check_if_course_required_for(target_course_code: str, check_course_code: str)
   - Check if check_course is required (directly or indirectly) for target_course
   - Returns the full prerequisite chain if found
   - Example: check_if_course_required_for("CSCE 2303", "CSCE 1001")

8. get_all_prerequisites_recursive(course_code: str)
   - Get all prerequisites recursively (prerequisites of prerequisites)

9. search_courses_by_department(department_code: str, limit: int = 10)
   - List courses in a specific department

10. search_courses_by_keyword(keyword: str, limit: int = 10)
    - Search for courses by keyword in title or description

11. query_database_directly(mongodb_query: str)
    - Execute a custom MongoDB query when other tools are insufficient
    - Query must be valid JSON string format
"""

__all__ = [
    'get_course_details',
    'get_course_prerequisites',
    'get_course_corequisites',
    'get_course_equivalencies',
    'find_courses_that_require',
    'check_prerequisites_satisfied',
    'check_if_course_required_for',
    'get_all_prerequisites_recursive',
    'search_courses_by_department',
    'search_courses_by_keyword',
    'query_database_directly',
    'COURSE_INFO_TOOLS',
    'TOOL_DESCRIPTIONS',
]