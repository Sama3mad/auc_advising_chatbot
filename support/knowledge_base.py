# support/knowledge_base.py
"""
Knowledge Base Access Layer
Provides unified access to all data sources (MongoDB courses, catalogs, etc.)
This is NOT a tool - just raw data retrieval
"""

from pymongo import MongoClient
from typing import Optional, List, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import MONGODB_URI, DATABASE_NAME, COURSES_COLLECTION, CATALOGS_COLLECTION


class KnowledgeBase:
    """
    Centralized data access layer for the chatbot.
    All agents and tools should use this to access data.
    """
    
    def __init__(self):
        """Initialize MongoDB connection"""
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DATABASE_NAME]
        self.courses = self.db[COURSES_COLLECTION]
        self.catalogs = self.db[CATALOGS_COLLECTION]  # NEW - catalogs collection
    
    # ============ COURSE RETRIEVAL METHODS ============
    
    def get_course_by_code(self, course_code: str) -> Optional[Dict[str, Any]]:
        """
        Get a single course by its course code
        
        Args:
            course_code: Course code (e.g., "CSCE 1001")
            
        Returns:
            Course document or None if not found
        """
        course_code = course_code.strip().upper()
        return self.courses.find_one(
            {"course_code": {"$regex": f"^{course_code}$", "$options": "i"}}
        )
    
    def get_course_by_master_id(self, master_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a course by its master ID
        
        Args:
            master_id: Course master ID (e.g., "COURSE:CSCE_1001")
            
        Returns:
            Course document or None if not found
        """
        return self.courses.find_one({"course_master_id": master_id})
    
    def get_multiple_courses_by_codes(self, course_codes: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple courses by their course codes
        
        Args:
            course_codes: List of course codes
            
        Returns:
            List of course documents
        """
        course_codes = [code.strip().upper() for code in course_codes]
        regex_pattern = "|".join([f"^{code}$" for code in course_codes])
        return list(self.courses.find(
            {"course_code": {"$regex": regex_pattern, "$options": "i"}}
        ))
    
    # ============ SEARCH METHODS ============
    
    def search_by_department(self, department_code: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search courses by department code
        
        Args:
            department_code: Department code (e.g., "CSCE")
            limit: Maximum number of results
            
        Returns:
            List of course documents
        """
        return list(self.courses.find(
            {"department_code": {"$regex": f"^{department_code}$", "$options": "i"}}
        ).limit(limit))
    
    def search_by_keyword(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search courses by keyword in title or description
        
        Args:
            keyword: Search keyword
            limit: Maximum number of results
            
        Returns:
            List of course documents
        """
        return list(self.courses.find(
            {
                "$or": [
                    {"title": {"$regex": keyword, "$options": "i"}},
                    {"canonical_description": {"$regex": keyword, "$options": "i"}},
                ]
            }
        ).limit(limit))
    
    def find_courses_requiring(self, course_master_id: str) -> List[Dict[str, Any]]:
        """
        Find all courses that have the given course as a prerequisite
        
        Args:
            course_master_id: Master ID of the prerequisite course
            
        Returns:
            List of course documents
        """
        return list(self.courses.find(
            {"relationships.is_prerequisite_for": course_master_id}
        ))
    
    def execute_custom_query(self, query: Dict[str, Any], limit: int = 20) -> List[Dict[str, Any]]:
        """
        Execute a custom MongoDB query
        
        Args:
            query: MongoDB query dictionary
            limit: Maximum number of results
            
        Returns:
            List of course documents
        """
        return list(self.courses.find(query).limit(limit))
    
    # ============ PREREQUISITE METHODS ============
    
    def get_prerequisite_ast(self, course_code: str) -> Optional[Dict[str, Any]]:
        """
        Get the prerequisite AST for a course
        
        Args:
            course_code: Course code
            
        Returns:
            Prerequisite AST or None
        """
        course = self.get_course_by_code(course_code)
        if course:
            return course.get("prerequisite_ast")
        return None
    
    def get_prerequisite_courses(self, course_code: str) -> List[str]:
        """
        Get list of prerequisite course master IDs
        
        Args:
            course_code: Course code
            
        Returns:
            List of prerequisite master IDs
        """
        course = self.get_course_by_code(course_code)
        if course:
            return course.get("prerequisite_courses", [])
        return []
    
    # ============ RELATIONSHIP METHODS ============
    
    def get_corequisites(self, course_code: str) -> List[str]:
        """
        Get corequisite master IDs for a course
        
        Args:
            course_code: Course code
            
        Returns:
            List of corequisite master IDs
        """
        course = self.get_course_by_code(course_code)
        if course:
            return course.get("relationships", {}).get("corequisites", [])
        return []
    
    def get_equivalencies(self, course_code: str) -> List[str]:
        """
        Get equivalent course master IDs
        
        Args:
            course_code: Course code
            
        Returns:
            List of equivalent course master IDs
        """
        course = self.get_course_by_code(course_code)
        if course:
            return course.get("relationships", {}).get("equivalencies", [])
        return []
    
    # ============ CATALOG METHODS (NEW) ============
    
    def get_catalog_by_id(self, catalog_id: str, program_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Get a specific catalog by ID
        
        Args:
            catalog_id: Catalog ID (e.g., "catalog_2024-2025")
            program_id: Optional program ID filter (e.g., "PROGRAM:CE_BS")
            
        Returns:
            Catalog document or None if not found
        """
        query = {"catalog_id": catalog_id}
        if program_id:
            query["program_id"] = program_id
        return self.catalogs.find_one(query)
    
    def get_all_catalogs(self) -> List[Dict[str, Any]]:
        """
        Get list of all available catalogs
        
        Returns:
            List of catalog documents (with limited fields)
        """
        return list(self.catalogs.find({}, {"catalog_id": 1, "program_id": 1, "title": 1, "total_credits_required": 1}))
    
    def get_program_requirements(self, program_id: str, catalog_year: str) -> Optional[Dict[str, Any]]:
        """
        Get program requirements from a specific catalog
        
        Args:
            program_id: Program ID (e.g., "PROGRAM:CE_BS")
            catalog_year: Catalog year (e.g., "2024-2025")
            
        Returns:
            Program requirements dictionary or None
        """
        catalog_id = f"catalog_{catalog_year}"
        catalog = self.get_catalog_by_id(catalog_id, program_id)
        if catalog:
            return catalog.get("program_requirements")
        return None
    
    def get_specializations(self, program_id: str, catalog_year: str) -> List[Dict[str, Any]]:
        """
        Get available specializations for a program
        
        Args:
            program_id: Program ID
            catalog_year: Catalog year
            
        Returns:
            List of specialization objects
        """
        catalog_id = f"catalog_{catalog_year}"
        catalog = self.get_catalog_by_id(catalog_id, program_id)
        if catalog:
            return catalog.get("specializations", [])
        return []
    
    # ============ CLEANUP ============
    
    def close(self):
        """Close database connection"""
        self.client.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Singleton instance for easy import
_kb_instance = None

def get_knowledge_base() -> KnowledgeBase:
    """Get singleton instance of KnowledgeBase"""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
    return _kb_instance