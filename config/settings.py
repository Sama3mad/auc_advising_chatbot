# config/settings.py
"""
Configuration settings for AUC Advising Chatbot
Store all credentials and configuration variables here
"""

# ============ DATABASE CONFIGURATION ============
MONGODB_URI = "mongodb+srv://samaabuzahra158_db_user:S95ZBCmvLdUUiAOr@aucadvising.1b70f4p.mongodb.net/?appName=aucadvising"
DATABASE_NAME = "auc_advising"
COURSES_COLLECTION = "courses"

# ============ LLM CONFIGURATION ============
GOOGLE_API_KEY = "AIzaSyBuxkfMlqR_cj4tdVASjDF8k4pqDrxWBVs"
LLM_MODEL = "gemini-2.5-flash"
LLM_TEMPERATURE = 0

# ============ AGENT CONFIGURATION ============
MAX_ITERATIONS = 5

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

Example Query Patterns:
1. Find by course code: {{"course_code": {{"$regex": "^CSCE 1001$", "$options": "i"}}}}
2. Find by department: {{"department_code": "CSCE"}}
3. Find courses that are prerequisites for X: {{"relationships.is_prerequisite_for": "COURSE:CSCE_1001"}}
4. Search by keyword in title or description: {{"$or": [{{"title": {{"$regex": "keyword", "$options": "i"}}}}, {{"canonical_description": {{"$regex": "keyword", "$options": "i"}}}}]}}
"""