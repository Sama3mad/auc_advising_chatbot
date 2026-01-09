# tools/prerequisite_tools.py
"""
Prerequisite Tools
Advanced prerequisite checking and analysis
"""

from langchain_core.tools import tool
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from support.knowledge_base import get_knowledge_base

kb = get_knowledge_base()


@tool
def check_prerequisites_satisfied(course_code: str, completed_courses: list) -> str:
    """
    Check if a student has satisfied the prerequisites for a course given their completed courses.
    Understands AND/OR logic in prerequisites.
    
    Args:
        course_code: The course code to check (e.g., "CSCE 3312")
        completed_courses: List of course codes the student has completed (e.g., ["PHYS 2211", "MACT 3211"])
    
    Returns:
        Detailed explanation of whether prerequisites are satisfied
    """
    course_code = course_code.strip().upper()
    completed_courses = [c.strip().upper() for c in completed_courses]
    
    # Get the course
    course = kb.get_course_by_code(course_code)
    
    if not course:
        return f"Course {course_code} not found."
    
    # Get prerequisite AST
    prereq_ast = kb.get_prerequisite_ast(course_code)
    
    if not prereq_ast:
        return f"{course['course_code']}: {course['title']}\nNo prerequisites required. You can take this course!"
    
    # Build a map of completed course master IDs
    completed_master_ids = set()
    for cc in completed_courses:
        completed_course = kb.get_course_by_code(cc)
        if completed_course:
            completed_master_ids.add(completed_course.get("course_master_id"))
    
    # Recursive function to evaluate prerequisite AST
    def evaluate_prereq_ast(node):
        if not node:
            return True, "No prerequisites"
        
        op = node.get("op")
        
        if op == "COURSE":
            course_master_id = node.get("course_master_id")
            if course_master_id in completed_master_ids:
                prereq_course = kb.get_course_by_master_id(course_master_id)
                course_name = prereq_course.get("course_code") if prereq_course else course_master_id
                return True, f"✓ {course_name}"
            else:
                prereq_course = kb.get_course_by_master_id(course_master_id)
                course_name = prereq_course.get("course_code") if prereq_course else course_master_id
                return False, f"✗ {course_name} (NOT completed)"
        
        elif op == "AND":
            args = node.get("args", [])
            results = [evaluate_prereq_ast(arg) for arg in args]
            all_satisfied = all(r[0] for r in results)
            explanation = " AND ".join(r[1] for r in results)
            return all_satisfied, f"({explanation})"
        
        elif op == "OR":
            args = node.get("args", [])
            results = [evaluate_prereq_ast(arg) for arg in args]
            any_satisfied = any(r[0] for r in results)
            explanation = " OR ".join(r[1] for r in results)
            return any_satisfied, f"({explanation})"
        
        elif op == "CONCURRENT":
            course_master_id = node.get("course_master_id")
            prereq_course = kb.get_course_by_master_id(course_master_id)
            course_name = prereq_course.get("course_code") if prereq_course else course_master_id
            return True, f"~ {course_name} (can be taken concurrently)"
        
        elif op == "STANDING":
            level = node.get("level", "")
            return True, f"~ {level} standing required"
        
        elif op == "APPROVAL":
            approval_type = node.get("type", "")
            return True, f"~ {approval_type} approval required"
        
        elif op == "EXEMPTION":
            return True, "~ Exemption possible"
        
        elif op == "EXTERNAL_CERT":
            cert = node.get("certificate", "")
            return True, f"~ {cert} required"
        
        return True, "Unknown prerequisite type"
    
    # Evaluate the prerequisite tree
    satisfied, explanation = evaluate_prereq_ast(prereq_ast)
    
    # Build response
    result = f"{course['course_code']}: {course['title']}\n\n"
    result += f"Prerequisites Structure:\n{explanation}\n\n"
    result += f"Completed Courses: {', '.join(completed_courses) if completed_courses else 'None'}\n\n"
    
    if satisfied:
        result += "✓ YES, you have satisfied all prerequisites for this course!"
    else:
        result += "✗ NO, you have NOT satisfied all prerequisites for this course."
        result += "\n\nYou need to complete the courses marked with ✗ before taking this course."
    
    return result


@tool
def check_if_course_required_for(target_course_code: str, check_course_code: str) -> str:
    """
    Check if check_course is required (directly or indirectly) to take target_course.
    Returns detailed explanation of the prerequisite chain if found.
    
    Args:
        target_course_code: The course you want to take
        check_course_code: The course you're checking if it's required
        
    Example: check_if_course_required_for("CSCE 2303", "CSCE 1001")
    """
    target_course_code = target_course_code.strip().upper()
    check_course_code = check_course_code.strip().upper()
    
    # Get target course
    target_course = kb.get_course_by_code(target_course_code)
    
    if not target_course:
        return f"Course {target_course_code} not found."
    
    # Get course to check
    check_course = kb.get_course_by_code(check_course_code)
    
    if not check_course:
        return f"Course {check_course_code} not found."
    
    check_master_id = check_course.get("course_master_id")
    
    # Get all prerequisites recursively with path tracking
    def get_prereq_path(course_master_id, target_id, visited=None, path=None):
        if visited is None:
            visited = set()
        if path is None:
            path = []
        
        if course_master_id in visited:
            return None
        
        visited.add(course_master_id)
        
        course = kb.get_course_by_master_id(course_master_id)
        if not course:
            return None
        
        current_code = course.get("course_code")
        current_path = path + [current_code]
        
        # Check if we found the target
        if course_master_id == target_id:
            return current_path
        
        # Check prerequisites
        prereq_ids = course.get("prerequisite_courses", [])
        for prereq_id in prereq_ids:
            result = get_prereq_path(prereq_id, target_id, visited.copy(), current_path)
            if result:
                return result
        
        return None
    
    # Find path from target to check course
    path = get_prereq_path(target_course.get("course_master_id"), check_master_id)
    
    if path:
        chain = " → ".join(path)
        return f"""YES, {check_course_code} is required for {target_course_code}.

Prerequisite chain: {chain}

Explanation: To take {target_course_code} ({target_course.get('title')}), you need {path[1]} as a prerequisite. {path[1]} in turn requires {check_course_code} ({check_course.get('title')}) as a prerequisite. Therefore, you cannot take {target_course_code} without completing {check_course_code} first."""
    else:
        # Check direct prerequisites
        direct_prereqs = target_course.get("prerequisite_human_readable", "None")
        return f"""NO, {check_course_code} is not required for {target_course_code}.

{target_course_code} ({target_course.get('title')}) has the following prerequisites:
{direct_prereqs}

{check_course_code} is not in the prerequisite chain for {target_course_code}."""


@tool
def get_all_prerequisites_recursive(course_code: str) -> str:
    """
    Get all prerequisites recursively (prerequisites of prerequisites) for a course.
    
    Args:
        course_code: Course code
        
    Returns:
        Complete list of all prerequisites
    """
    course = kb.get_course_by_code(course_code)
    
    if not course:
        return f"Course {course_code} not found."
    
    def get_prereqs_recursive(course_master_id, visited=None):
        if visited is None:
            visited = set()
        
        if course_master_id in visited:
            return []
        
        visited.add(course_master_id)
        
        course = kb.get_course_by_master_id(course_master_id)
        if not course:
            return []
        
        prereq_ids = course.get("prerequisite_courses", [])
        all_prereqs = []
        
        for prereq_id in prereq_ids:
            prereq_course = kb.get_course_by_master_id(prereq_id)
            if prereq_course:
                all_prereqs.append({
                    "code": prereq_course.get("course_code"),
                    "title": prereq_course.get("title")
                })
                # Get prerequisites of this prerequisite
                nested_prereqs = get_prereqs_recursive(prereq_id, visited)
                all_prereqs.extend(nested_prereqs)
        
        return all_prereqs
    
    all_prereqs = get_prereqs_recursive(course.get("course_master_id"))
    
    if not all_prereqs:
        return f"{course['course_code']}: {course['title']}\nNo prerequisites found."
    
    # Remove duplicates
    seen = set()
    unique_prereqs = []
    for p in all_prereqs:
        if p['code'] not in seen:
            seen.add(p['code'])
            unique_prereqs.append(p)
    
    result = f"All prerequisites for {course['course_code']}: {course['title']}\n\n"
    for prereq in unique_prereqs:
        result += f"- {prereq['code']}: {prereq['title']}\n"
    
    return result