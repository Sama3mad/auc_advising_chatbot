# config/settings.py
"""
Configuration settings for AUC Advising Chatbot
Store all credentials and configuration variables here
"""

# ============ DATABASE CONFIGURATION ============
MONGODB_URI = "mongodb+srv://samaabuzahra158_db_user:S95ZBCmvLdUUiAOr@aucadvising.1b70f4p.mongodb.net/?appName=aucadvising"
DATABASE_NAME = "auc_advising"
COURSES_COLLECTION = "courses"
CATALOGS_COLLECTION = "catalogs"  

# ============ LLM CONFIGURATION ============
GOOGLE_API_KEY = "AIzaSyAIcD_j5wJHJkZEsk_PTI_cp_Qn1zv6z2o"
LLM_MODEL = "gemini-2.5-flash"
LLM_TEMPERATURE = 0

# ============ AGENT CONFIGURATION ============
MAX_ITERATIONS = 5

# ============ DEFAULT CATALOG ============
DEFAULT_CATALOG_YEAR = "2024-2025"  # NEW - default catalog to use

# ============ DATABASE SCHEMA DOCUMENTATION ============
DATABASE_SCHEMA = """
DATABASE SCHEMA INFORMATION:

Collection: courses
- Each document represents one course
- Fields:
  * course_master_id: string (e.g., "COURSE:CSCE_1001")
  * course_code: string (e.g., "CSCE 1001")
  * title: string (course title)
  * canonical_description: string (course description)
  * credits: number or string
  * level: string ("undergrad", "grad")
  * when_offered: string (e.g., "Fall, Spring")
  * prerequisite_human_readable: string (human-readable prerequisites)
  * prerequisite_courses: array of course_master_ids
  * prerequisite_ast: object representing prerequisite logic tree
  * relationships: object containing:
    - is_prerequisite_for: array of course_master_ids
    - corequisites: array of course_master_ids (courses that must be taken together)
    - equivalencies: array of course_master_ids
  * department_code: string (e.g., "CSCE")
  * department_name: string (e.g., "Computer Science and Engineering")

Collection: catalogs
- Each document represents a program catalog for a specific year
- Fields:
  * catalog_id: string (e.g., "catalog_2024-2025")
  * program_id: string (e.g., "PROGRAM:CE_BS")
  * title: string (program title)
  * degree_type: string (e.g., "Bachelor of Science")
  * total_credits_required: number
  * description: string
  * specializations: array of specialization objects
  * program_requirements: object containing:
    - core_curriculum: core requirements
    - engineering_core: engineering requirements
    - concentration: major-specific requirements
    - concentration_electives: elective requirements
    - general_electives: general elective requirements

Example Query Patterns:
1. Find by course code: {{"course_code": {{"$regex": "^CSCE 1001$", "$options": "i"}}}}
2. Find by department: {{"department_code": "CSCE"}}
3. Find catalog by ID: {{"catalog_id": "catalog_2024-2025", "program_id": "PROGRAM:CE_BS"}}
4. Search by keyword in title or description: {{"$or": [{{"title": {{"$regex": "keyword", "$options": "i"}}}}, {{"canonical_description": {{"$regex": "keyword", "$options": "i"}}}}]}}
"""