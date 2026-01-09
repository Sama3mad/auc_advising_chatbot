# tools/catalog_tools.py
"""
Catalog Tools
Tools for querying program catalogs, requirements, and degree planning
"""

from langchain_core.tools import tool
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from support.knowledge_base import get_knowledge_base

kb = get_knowledge_base()


@tool
def get_program_info(program_id: str, catalog_year: str = "2024-2025") -> str:
    """
    Get basic information about a program from a specific catalog.
    
    Args:
        program_id: Program ID (e.g., "PROGRAM:CE_BS", "PROGRAM:CS_BS")
        catalog_year: Catalog year (e.g., "2024-2025", "2023-2024")
        
    Returns:
        Program information including title, degree type, total credits, description
    """
    catalog_id = f"catalog_{catalog_year}"
    catalog = kb.catalogs.find_one({
        "catalog_id": catalog_id,
        "program_id": program_id
    })
    
    if not catalog:
        return f"Program {program_id} not found in catalog {catalog_year}."
    
    result = f"""Program: {catalog.get('title', '?')}
Degree Type: {catalog.get('degree_type', '?')}
Total Credits Required: {catalog.get('total_credits_required', '?')}

Description:
{catalog.get('description', 'No description available')}

Specializations Available:
"""
    
    specializations = catalog.get('specializations', [])
    if specializations:
        for spec in specializations:
            result += f"- {spec.get('name', '?')}: {spec.get('description', '')}\n"
    else:
        result += "None\n"
    
    return result


@tool
def get_core_requirements(program_id: str, catalog_year: str = "2024-2025") -> str:
    """
    Get core curriculum requirements for a program.
    
    Args:
        program_id: Program ID (e.g., "PROGRAM:CE_BS")
        catalog_year: Catalog year
        
    Returns:
        Core curriculum requirements including freshman requirements, cultural foundations, etc.
    """
    catalog_id = f"catalog_{catalog_year}"
    catalog = kb.catalogs.find_one({
        "catalog_id": catalog_id,
        "program_id": program_id
    })
    
    if not catalog:
        return f"Program {program_id} not found in catalog {catalog_year}."
    
    core = catalog.get('program_requirements', {}).get('core_curriculum', {})
    
    if not core:
        return "No core curriculum information found."
    
    result = f"""Core Curriculum Requirements for {catalog.get('title', '?')}
Total Core Credits: {core.get('credits_required', '?')}

"""
    
    # Freshman requirements
    freshman = core.get('freshman_requirements', {})
    if freshman:
        result += f"Freshman Requirements ({freshman.get('credits_required', '?')} credits):\n"
        for course_id in freshman.get('required_course_master_ids', []):
            course = kb.get_course_by_master_id(course_id)
            if course:
                result += f"- {course.get('course_code', '?')}: {course.get('title', '?')}\n"
        result += "\n"
    
    # Cultural foundations
    cultural = core.get('cultural_foundations', {})
    if cultural:
        result += f"Cultural Foundations ({cultural.get('credits_required', '?')} credits):\n"
        result += "Choose one course from the approved list\n\n"
    
    # Secondary level
    secondary = core.get('secondary_level', {})
    if secondary:
        result += f"Secondary Level Requirements ({secondary.get('credits_required', '?')} credits):\n"
        categories = secondary.get('categories', [])
        for category in categories:
            result += f"- {category.get('category_name', '?')}: {category.get('credits_required', '?')} credits\n"
    
    return result


@tool
def get_concentration_requirements(program_id: str, catalog_year: str = "2024-2025") -> str:
    """
    Get concentration (major-specific) requirements.
    
    Args:
        program_id: Program ID
        catalog_year: Catalog year
        
    Returns:
        Required courses for the concentration
    """
    catalog_id = f"catalog_{catalog_year}"
    catalog = kb.catalogs.find_one({
        "catalog_id": catalog_id,
        "program_id": program_id
    })
    
    if not catalog:
        return f"Program {program_id} not found in catalog {catalog_year}."
    
    concentration = catalog.get('program_requirements', {}).get('concentration', {})
    
    if not concentration:
        return "No concentration requirements found."
    
    result = f"""Concentration Requirements for {catalog.get('title', '?')}
Total Concentration Credits: {concentration.get('credits_required', '?')}

Required Courses:
"""
    
    for course_id in concentration.get('required_course_master_ids', []):
        course = kb.get_course_by_master_id(course_id)
        if course:
            result += f"- {course.get('course_code', '?')}: {course.get('title', '?')} ({course.get('credits', '?')} credits)\n"
    
    return result


@tool
def get_specialization_requirements(program_id: str, specialization_name: str, catalog_year: str = "2024-2025") -> str:
    """
    Get requirements for a specific specialization.
    
    Args:
        program_id: Program ID
        specialization_name: Name of specialization (e.g., "Embedded Systems", "Artificial Intelligence", "Cybersecurity")
        catalog_year: Catalog year
        
    Returns:
        Requirements for the specialization
    """
    catalog_id = f"catalog_{catalog_year}"
    catalog = kb.catalogs.find_one({
        "catalog_id": catalog_id,
        "program_id": program_id
    })
    
    if not catalog:
        return f"Program {program_id} not found in catalog {catalog_year}."
    
    # Find specialization
    specializations = catalog.get('specializations', [])
    spec = None
    for s in specializations:
        if specialization_name.lower() in s.get('name', '').lower():
            spec = s
            break
    
    if not spec:
        return f"Specialization '{specialization_name}' not found. Available specializations: {', '.join([s.get('name', '?') for s in specializations])}"
    
    result = f"""Specialization: {spec.get('name', '?')}
Description: {spec.get('description', '?')}

"""
    
    # Get elective requirements for this specialization
    conc_electives = catalog.get('program_requirements', {}).get('concentration_electives', {})
    rules = conc_electives.get('rules_by_specialization', [])
    
    spec_rule = None
    for rule in rules:
        if rule.get('specialization_id') == spec.get('specialization_id'):
            spec_rule = rule
            break
    
    if spec_rule:
        result += f"Requirements:\n{spec_rule.get('requirement', '')}\n\n"
        
        # Show elective groups
        elective_groups = spec_rule.get('elective_groups', [])
        for group in elective_groups:
            result += f"{group.get('group_name', '?')} ({group.get('min_credits', '?')} credits minimum):\n"
            for course_id in group.get('allowed_course_master_ids', []):
                course = kb.get_course_by_master_id(course_id)
                if course:
                    result += f"- {course.get('course_code', '?')}: {course.get('title', '?')}\n"
            if group.get('notes'):
                result += f"Notes: {group.get('notes')}\n"
            result += "\n"
    
    return result


@tool
def get_available_electives(program_id: str, catalog_year: str = "2024-2025") -> str:
    """
    Get list of available elective courses for a program.
    
    Args:
        program_id: Program ID
        catalog_year: Catalog year
        
    Returns:
        List of elective courses
    """
    catalog_id = f"catalog_{catalog_year}"
    catalog = kb.catalogs.find_one({
        "catalog_id": catalog_id,
        "program_id": program_id
    })
    
    if not catalog:
        return f"Program {program_id} not found in catalog {catalog_year}."
    
    conc_electives = catalog.get('program_requirements', {}).get('concentration_electives', {})
    available = conc_electives.get('available_electives', [])
    
    if not available:
        return "No elective information found."
    
    result = f"""Available Elective Courses for {catalog.get('title', '?')}
Total Elective Credits Required: {conc_electives.get('credits_required', '?')}

Elective Courses:
"""
    
    for course_id in available:
        course = kb.get_course_by_master_id(course_id)
        if course:
            result += f"- {course.get('course_code', '?')}: {course.get('title', '?')} ({course.get('credits', '?')} credits)\n"
    
    return result


@tool
def calculate_degree_progress(program_id: str, completed_courses: list, catalog_year: str = "2024-2025") -> str:
    """
    Calculate how many credits completed and remaining for degree.
    
    Args:
        program_id: Program ID
        completed_courses: List of completed course codes
        catalog_year: Catalog year
        
    Returns:
        Degree progress summary
    """
    catalog_id = f"catalog_{catalog_year}"
    catalog = kb.catalogs.find_one({
        "catalog_id": catalog_id,
        "program_id": program_id
    })
    
    if not catalog:
        return f"Program {program_id} not found in catalog {catalog_year}."
    
    total_required = catalog.get('total_credits_required', 0)
    
    # Get completed courses details
    completed_courses = [c.strip().upper() for c in completed_courses]
    completed_credits = 0
    completed_master_ids = set()
    
    for course_code in completed_courses:
        course = kb.get_course_by_code(course_code)
        if course:
            try:
                credits = int(course.get('credits', 0))
                completed_credits += credits
                completed_master_ids.add(course.get('course_master_id'))
            except:
                pass
    
    remaining_credits = total_required - completed_credits
    percentage = (completed_credits / total_required * 100) if total_required > 0 else 0
    
    result = f"""Degree Progress for {catalog.get('title', '?')}

Total Credits Required: {total_required}
Credits Completed: {completed_credits}
Credits Remaining: {remaining_credits}
Progress: {percentage:.1f}%

Completed Courses: {', '.join(completed_courses)}
"""
    
    # Check core requirements
    core = catalog.get('program_requirements', {}).get('core_curriculum', {})
    freshman = core.get('freshman_requirements', {})
    freshman_required = set(freshman.get('required_course_master_ids', []))
    freshman_completed = freshman_required.intersection(completed_master_ids)
    
    result += f"\nFreshman Requirements: {len(freshman_completed)}/{len(freshman_required)} courses completed"
    
    # Check concentration requirements
    concentration = catalog.get('program_requirements', {}).get('concentration', {})
    conc_required = set(concentration.get('required_course_master_ids', []))
    conc_completed = conc_required.intersection(completed_master_ids)
    
    result += f"\nConcentration Requirements: {len(conc_completed)}/{len(conc_required)} courses completed"
    
    return result


@tool
def list_available_catalogs() -> str:
    """
    List all available catalog years.
    
    Returns:
        List of available catalogs
    """
    catalogs = list(kb.catalogs.find({}, {"catalog_id": 1, "title": 1, "program_id": 1}))
    
    if not catalogs:
        return "No catalogs found in the database."
    
    result = "Available Catalogs:\n\n"
    
    for catalog in catalogs:
        catalog_id = catalog.get('catalog_id', '?')
        title = catalog.get('title', '?')
        result += f"- {catalog_id}: {title}\n"
    
    return result


@tool
def compare_catalog_changes(program_id: str, old_catalog: str, new_catalog: str) -> str:
    """
    Compare requirements between two catalog years.
    
    Args:
        program_id: Program ID
        old_catalog: Old catalog year (e.g., "2023-2024")
        new_catalog: New catalog year (e.g., "2024-2025")
        
    Returns:
        Comparison of changes between catalogs
    """
    old_cat_id = f"catalog_{old_catalog}"
    new_cat_id = f"catalog_{new_catalog}"
    
    old = kb.catalogs.find_one({"catalog_id": old_cat_id, "program_id": program_id})
    new = kb.catalogs.find_one({"catalog_id": new_cat_id, "program_id": program_id})
    
    if not old:
        return f"Old catalog {old_catalog} not found."
    if not new:
        return f"New catalog {new_catalog} not found."
    
    result = f"""Catalog Comparison for {program_id}
{old_catalog} vs {new_catalog}

Total Credits:
- {old_catalog}: {old.get('total_credits_required', '?')} credits
- {new_catalog}: {new.get('total_credits_required', '?')} credits
Change: {new.get('total_credits_required', 0) - old.get('total_credits_required', 0):+d} credits

Specializations:
"""
    
    old_specs = [s.get('name') for s in old.get('specializations', [])]
    new_specs = [s.get('name') for s in new.get('specializations', [])]
    
    added_specs = set(new_specs) - set(old_specs)
    removed_specs = set(old_specs) - set(new_specs)
    
    if added_specs:
        result += f"Added: {', '.join(added_specs)}\n"
    if removed_specs:
        result += f"Removed: {', '.join(removed_specs)}\n"
    if not added_specs and not removed_specs:
        result += "No changes\n"
    
    return result