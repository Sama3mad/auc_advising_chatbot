# support/knowledge_base.py
"""
Knowledge Base Access Layer
Provides unified access to all data sources (MongoDB courses, catalogs, etc.)
This is NOT a tool - just raw data retrieval
"""

from pymongo import MongoClient
from neo4j import GraphDatabase
from typing import Optional, List, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    MONGODB_URI,
    DATABASE_NAME,
    COURSES_COLLECTION,
    CATALOGS_COLLECTION,
    RULES_COLLECTION,
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
)


class KnowledgeBase:
    """
    Centralized data access layer for the chatbot.
    All agents and tools should use this to access data.
    """
    
    def __init__(self):
        """Initialize MongoDB and Neo4j connections"""
        # MongoDB connection for course data and rules
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DATABASE_NAME]
        self.courses = self.db[COURSES_COLLECTION]
        self.catalogs = self.db[CATALOGS_COLLECTION]  # NEW - catalogs collection
        self.rules = self.db[RULES_COLLECTION]        # Core academic and policy rules
        
        # Neo4j connection for relationships
        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    
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
    
    # ============ NEO4J-BASED RELATIONSHIP METHODS ============
    
    def find_courses_requiring(self, course_master_id: str) -> List[Dict[str, Any]]:
        """
        Find all courses that have the given course as a prerequisite (using Neo4j)
        
        Args:
            course_master_id: Master ID of the prerequisite course (e.g., "COURSE:CSCE_1001")
            
        Returns:
            List of course documents
        """
        # Convert master ID to course code
        course_code = course_master_id.replace('COURSE:', '').replace('_', ' ')
        
        with self.neo4j_driver.session() as session:
            # Find all courses that require this course
            result = session.run("""
                MATCH (c:Course)-[:REQUIRES]->(p:Course {code: $code})
                RETURN DISTINCT c.code as code, c.master_id as master_id
                UNION
                MATCH (c:Course)-[:HAS_REQUIREMENT]->(rg:RequirementGroup)-[:REQUIRES|OPTION]->(p:Course {code: $code})
                RETURN DISTINCT c.code as code, c.master_id as master_id
            """, code=course_code)
            
            course_codes = [record['code'] for record in result]
        
        # Get full course documents from MongoDB
        if course_codes:
            return self.get_multiple_courses_by_codes(course_codes)
        return []
    
    # ============ COMMENTED OUT: MONGODB-BASED RELATIONSHIP METHODS ============
    # These methods are kept for fallback but are replaced by Neo4j implementations above
    
    # def find_courses_requiring(self, course_master_id: str) -> List[Dict[str, Any]]:
    #     """
    #     Find all courses that have the given course as a prerequisite
    #     
    #     Args:
    #         course_master_id: Master ID of the prerequisite course
    #         
    #     Returns:
    #         List of course documents
    #     """
    #     return list(self.courses.find(
    #         {"relationships.is_prerequisite_for": course_master_id}
    #     ))
    
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
    
    # ============ RULES / POLICIES METHODS ============
    
    def get_rule_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single policy/rule document by its _id
        
        Args:
            rule_id: Rule identifier (e.g., "freshman_level_requirements")
        
        Returns:
            Rule document or None
        """
        return self.rules.find_one({"_id": rule_id})
    
    def search_rules_by_tag(self, tag: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search rules by tag (e.g., 'freshman', 'declaration', 'registration_hold')
        """
        tag = tag.strip().lower()
        return list(
            self.rules.find({"tags": {"$regex": tag, "$options": "i"}}).limit(limit)
        )
    
    def search_rules_by_keyword(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search rules by keyword in section title or rule texts.
        """
        keyword = keyword.strip()
        return list(
            self.rules.find(
                {
                    "$or": [
                        {"section": {"$regex": keyword, "$options": "i"}},
                        {"rules": {"$elemMatch": {"$regex": keyword, "$options": "i"}}},
                    ]
                }
            ).limit(limit)
        )
    
    def get_rules_for_level(self, level: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get rules that apply to a certain academic level (e.g., 'undergraduate', 'graduate').
        """
        level = level.strip().lower()
        return list(
            self.rules.find({"applies_to": {"$regex": level, "$options": "i"}}).limit(
                limit
            )
        )
    
    def list_rule_sections(self) -> List[Dict[str, str]]:
        """
        List all rule sections with their IDs and titles.
        """
        cursor = self.rules.find({}, {"_id": 1, "section": 1}).sort("section", 1)
        return [{"id": doc["_id"], "section": doc.get("section", "")} for doc in cursor]
    
    # ============ PREREQUISITE METHODS ============
    
    def get_prerequisite_ast(self, course_code: str) -> Optional[Dict[str, Any]]:
        """
        Get the prerequisite AST for a course (from MongoDB - AST not stored in Neo4j)
        
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
        Get list of prerequisite course master IDs (using Neo4j)
        
        Args:
            course_code: Course code
            
        Returns:
            List of prerequisite master IDs
        """
        course_code = course_code.strip().upper()
        prereq_master_ids = []
        
        with self.neo4j_driver.session() as session:
            # Get direct prerequisites
            result = session.run("""
                MATCH (c:Course {code: $code})-[:REQUIRES]->(p:Course)
                RETURN p.master_id as master_id, p.code as code
            """, code=course_code)
            
            for record in result:
                master_id = record.get('master_id')
                if master_id:
                    prereq_master_ids.append(master_id)
                else:
                    # If master_id not in Neo4j, construct it from code
                    code = record.get('code', '')
                    if code:
                        master_id = f"COURSE:{code.replace(' ', '_')}"
                        prereq_master_ids.append(master_id)
            
            # Get prerequisites from requirement groups
            result = session.run("""
                MATCH (c:Course {code: $code})-[:HAS_REQUIREMENT]->(rg:RequirementGroup)-[:REQUIRES|OPTION]->(p:Course)
                RETURN DISTINCT p.master_id as master_id, p.code as code
            """, code=course_code)
            
            for record in result:
                master_id = record.get('master_id')
                if master_id and master_id not in prereq_master_ids:
                    prereq_master_ids.append(master_id)
                elif not master_id:
                    code = record.get('code', '')
                    if code:
                        master_id = f"COURSE:{code.replace(' ', '_')}"
                        if master_id not in prereq_master_ids:
                            prereq_master_ids.append(master_id)
        
        return prereq_master_ids
    
    # ============ COMMENTED OUT: MONGODB-BASED PREREQUISITE METHODS ============
    # These methods are kept for fallback but are replaced by Neo4j implementations above
    
    # def get_prerequisite_courses(self, course_code: str) -> List[str]:
    #     """
    #     Get list of prerequisite course master IDs
    #     
    #     Args:
    #         course_code: Course code
    #         
    #     Returns:
    #         List of prerequisite master IDs
    #     """
    #     course = self.get_course_by_code(course_code)
    #     if course:
    #         return course.get("prerequisite_courses", [])
    #     return []
    
    # ============ RELATIONSHIP METHODS (NEO4J-BASED) ============
    
    def get_corequisites(self, course_code: str) -> List[str]:
        """
        Get corequisite master IDs for a course (using Neo4j)
        
        Args:
            course_code: Course code
            
        Returns:
            List of corequisite master IDs
        """
        course_code = course_code.strip().upper()
        coreq_master_ids = []
        
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (c:Course {code: $code})-[:COREQUISITE]-(co:Course)
                RETURN DISTINCT co.master_id as master_id, co.code as code
            """, code=course_code)
            
            for record in result:
                master_id = record.get('master_id')
                if master_id:
                    coreq_master_ids.append(master_id)
                else:
                    # If master_id not in Neo4j, construct it from code
                    code = record.get('code', '')
                    if code:
                        master_id = f"COURSE:{code.replace(' ', '_')}"
                        coreq_master_ids.append(master_id)
        
        return coreq_master_ids
    
    def get_equivalencies(self, course_code: str) -> List[str]:
        """
        Get equivalent course master IDs (using Neo4j)
        
        Args:
            course_code: Course code
            
        Returns:
            List of equivalent course master IDs
        """
        course_code = course_code.strip().upper()
        equiv_master_ids = []
        
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (c:Course {code: $code})-[:EQUIVALENT]-(e:Course)
                RETURN DISTINCT e.master_id as master_id, e.code as code
            """, code=course_code)
            
            for record in result:
                master_id = record.get('master_id')
                if master_id:
                    equiv_master_ids.append(master_id)
                else:
                    # If master_id not in Neo4j, construct it from code
                    code = record.get('code', '')
                    if code:
                        master_id = f"COURSE:{code.replace(' ', '_')}"
                        equiv_master_ids.append(master_id)
        
        return equiv_master_ids
    
    def get_courses_with_corequisite(self, course_code: str) -> List[Dict[str, Any]]:
        """
        Get all courses that have the given course as a corequisite (using Neo4j)
        This is the reverse of get_corequisites - finds courses that require this course as a corequisite
        
        Args:
            course_code: Course code
            
        Returns:
            List of course documents that have this course as a corequisite
        """
        course_code = course_code.strip().upper()
        
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (c:Course {code: $code})<-[:COREQUISITE]-(other:Course)
                RETURN DISTINCT other.code as code
            """, code=course_code)
            
            course_codes = [record['code'] for record in result]
        
        # Get full course documents from MongoDB
        if course_codes:
            return self.get_multiple_courses_by_codes(course_codes)
        return []
    
    # ============ COMMENTED OUT: MONGODB-BASED RELATIONSHIP METHODS ============
    # These methods are kept for fallback but are replaced by Neo4j implementations above
    
    # def get_corequisites(self, course_code: str) -> List[str]:
    #     """
    #     Get corequisite master IDs for a course
    #     
    #     Args:
    #         course_code: Course code
    #         
    #     Returns:
    #         List of corequisite master IDs
    #     """
    #     course = self.get_course_by_code(course_code)
    #     if course:
    #         return course.get("relationships", {}).get("corequisites", [])
    #     return []
    # 
    # def get_equivalencies(self, course_code: str) -> List[str]:
    #     """
    #     Get equivalent course master IDs
    #     
    #     Args:
    #         course_code: Course code
    #         
    #     Returns:
    #         List of equivalent course master IDs
    #     """
    #     course = self.get_course_by_code(course_code)
    #     if course:
    #         return course.get("relationships", {}).get("equivalencies", [])
    #     return []
    
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
        """Close database connections"""
        self.client.close()
        self.neo4j_driver.close()
    
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