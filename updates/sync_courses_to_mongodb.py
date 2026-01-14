"""
MongoDB Course Sync Script
This script syncs all courses from courses_master.json to MongoDB.
It will add new courses and update existing ones.
"""

import json
import sys
import os
from pathlib import Path
from pymongo import MongoClient
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import MONGODB_URI, DATABASE_NAME, COURSES_COLLECTION


class CourseMongoDBSyncer:
    """Syncs courses from courses_master.json to MongoDB"""
    
    def __init__(self):
        """Initialize MongoDB connection"""
        print("Connecting to MongoDB...")
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DATABASE_NAME]
        self.courses_collection = self.db[COURSES_COLLECTION]
        print("[OK] Connected to MongoDB")
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()
    
    def prepare_course_document(self, course: Dict[str, Any], dept_code: str, dept_name: str) -> Dict[str, Any]:
        """
        Prepare a course document for MongoDB insertion.
        Adds department_code and department_name to the course data.
        
        Args:
            course: Course data from JSON
            dept_code: Department code (e.g., "CSCE")
            dept_name: Department name
            
        Returns:
            Prepared course document
        """
        # Create a copy of the course data
        doc = course.copy()
        
        # Add department information
        doc['department_code'] = dept_code
        doc['department_name'] = dept_name
        
        # Ensure all required fields exist with defaults if needed
        if 'difficulty_level' not in doc:
            doc['difficulty_level'] = ""
        if 'when_offered' not in doc:
            doc['when_offered'] = ""
        if 'prerequisite_human_readable' not in doc:
            doc['prerequisite_human_readable'] = ""
        if 'prerequisite_courses' not in doc:
            doc['prerequisite_courses'] = []
        if 'prerequisite_ast' not in doc:
            doc['prerequisite_ast'] = None
        if 'relationships' not in doc:
            doc['relationships'] = {
                'is_prerequisite_for': [],
                'corequisites': [],
                'equivalencies': []
            }
        if 'metadata' not in doc:
            doc['metadata'] = {}
        
        return doc
    
    def sync_courses(self, courses_file: Path) -> Dict[str, int]:
        """
        Sync all courses from JSON file to MongoDB
        
        Args:
            courses_file: Path to courses_master.json
            
        Returns:
            Dictionary with statistics (added, updated, skipped, errors)
        """
        print(f"\nLoading courses from {courses_file}...")
        with open(courses_file, 'r', encoding='utf-8') as f:
            course_data = json.load(f)
        
        stats = {
            'added': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        total_courses = 0
        for dept_code, dept_info in course_data['departments'].items():
            total_courses += len(dept_info['courses'])
        
        print(f"Found {total_courses} courses across {len(course_data['departments'])} departments")
        print("\nSyncing courses to MongoDB...")
        
        for dept_code, dept_info in course_data['departments'].items():
            dept_name = dept_info['department_name']
            print(f"\nProcessing {dept_code} ({dept_name}): {len(dept_info['courses'])} courses")
            
            for course in dept_info['courses']:
                try:
                    # Prepare the document
                    course_doc = self.prepare_course_document(course, dept_code, dept_name)
                    
                    # Check if course_master_id exists
                    if not course_doc.get('course_master_id'):
                        print(f"  [WARNING] Skipping course without course_master_id: {course.get('course_code', 'Unknown')}")
                        stats['skipped'] += 1
                        continue
                    
                    course_master_id = course_doc['course_master_id']
                    
                    # Check if course already exists
                    existing = self.courses_collection.find_one({"course_master_id": course_master_id})
                    
                    if existing:
                        # Update existing course
                        result = self.courses_collection.update_one(
                            {"course_master_id": course_master_id},
                            {"$set": course_doc}
                        )
                        if result.modified_count > 0:
                            stats['updated'] += 1
                            print(f"  [UPDATED] {course_doc.get('course_code', course_master_id)}")
                        else:
                            stats['skipped'] += 1
                            print(f"  [NO CHANGE] {course_doc.get('course_code', course_master_id)}")
                    else:
                        # Insert new course
                        self.courses_collection.insert_one(course_doc)
                        stats['added'] += 1
                        print(f"  [ADDED] {course_doc.get('course_code', course_master_id)}")
                
                except Exception as e:
                    stats['errors'] += 1
                    course_code = course.get('course_code', course.get('course_master_id', 'Unknown'))
                    print(f"  [ERROR] Failed to sync {course_code}: {e}")
        
        return stats
    
    def verify_sync(self, courses_file: Path) -> Dict[str, Any]:
        """
        Verify that all courses from JSON are in MongoDB
        
        Args:
            courses_file: Path to courses_master.json
            
        Returns:
            Verification results
        """
        print("\n" + "="*60)
        print("VERIFYING SYNC")
        print("="*60)
        
        with open(courses_file, 'r', encoding='utf-8') as f:
            course_data = json.load(f)
        
        missing_courses = []
        total_in_json = 0
        
        for dept_code, dept_info in course_data['departments'].items():
            for course in dept_info['courses']:
                total_in_json += 1
                course_master_id = course.get('course_master_id')
                if not course_master_id:
                    continue
                
                existing = self.courses_collection.find_one({"course_master_id": course_master_id})
                if not existing:
                    missing_courses.append({
                        'course_code': course.get('course_code', 'Unknown'),
                        'course_master_id': course_master_id
                    })
        
        # Get total count in MongoDB
        total_in_mongo = self.courses_collection.count_documents({})
        
        print(f"\nTotal courses in JSON: {total_in_json}")
        print(f"Total courses in MongoDB: {total_in_mongo}")
        print(f"Missing courses: {len(missing_courses)}")
        
        if missing_courses:
            print("\nMissing courses:")
            for course in missing_courses[:20]:
                print(f"  - {course['course_code']} ({course['course_master_id']})")
            if len(missing_courses) > 20:
                print(f"  ... and {len(missing_courses) - 20} more")
        else:
            print("\n[SUCCESS] All courses are in MongoDB!")
        
        return {
            'total_in_json': total_in_json,
            'total_in_mongo': total_in_mongo,
            'missing_count': len(missing_courses),
            'missing_courses': missing_courses
        }
    
    def show_statistics(self):
        """Show MongoDB collection statistics"""
        print("\n" + "="*60)
        print("MONGODB STATISTICS")
        print("="*60)
        
        total_courses = self.courses_collection.count_documents({})
        
        # Count by department
        pipeline = [
            {"$group": {"_id": "$department_code", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        dept_counts = list(self.courses_collection.aggregate(pipeline))
        
        print(f"\nTotal courses: {total_courses}")
        print("\nCourses by department:")
        for dept in dept_counts:
            print(f"  {dept['_id']}: {dept['count']} courses")
        
        # Sample courses
        print("\nSample courses:")
        sample = list(self.courses_collection.find().limit(5))
        for course in sample:
            print(f"  - {course.get('course_code', 'Unknown')}: {course.get('title', 'No title')}")
        
        print("="*60)


def main():
    """Main function"""
    # Get the path to courses_master.json
    script_dir = Path(__file__).parent
    courses_file = script_dir.parent / 'data' / 'course' / 'courses_master.json'
    
    if not courses_file.exists():
        print(f"[ERROR] Could not find courses_master.json at {courses_file}")
        return
    
    syncer = CourseMongoDBSyncer()
    
    try:
        print("\n" + "="*60)
        print("MONGODB COURSE SYNC")
        print("="*60)
        
        # Show current statistics
        syncer.show_statistics()
        
        # Sync courses
        stats = syncer.sync_courses(courses_file)
        
        # Show results
        print("\n" + "="*60)
        print("SYNC RESULTS")
        print("="*60)
        print(f"Added: {stats['added']}")
        print(f"Updated: {stats['updated']}")
        print(f"Skipped (no changes): {stats['skipped']}")
        print(f"Errors: {stats['errors']}")
        print("="*60)
        
        # Verify sync
        verification = syncer.verify_sync(courses_file)
        
        # Show final statistics
        syncer.show_statistics()
        
        if verification['missing_count'] == 0:
            print("\n[SUCCESS] All courses successfully synced to MongoDB!")
        else:
            print(f"\n[WARNING] {verification['missing_count']} courses are missing from MongoDB")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        syncer.close()


if __name__ == "__main__":
    main()

