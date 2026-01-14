"""
Verification Script for Neo4j Course Relationships
This script verifies that all relationships from courses_master.json exist in Neo4j
"""

import json
from neo4j import GraphDatabase
from pathlib import Path

# Neo4j connection details
NEO4J_URI = "neo4j+s://6bd58e7f.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "jeiH1Na0rPA67jYospHTY2IjdLoq4AW23ujVAr_c7GM"

class RelationshipVerifier:
    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
    
    def close(self):
        self.driver.close()
    
    def convert_master_id_to_code(self, master_id):
        """Convert COURSE:XXX_YYYY to XXX YYYY"""
        if not master_id or not master_id.startswith('COURSE:'):
            return None
        code = master_id.replace('COURSE:', '').replace('_', ' ')
        return code
    
    def verify_all_relationships(self, course_data):
        """Verify that all relationships in JSON are correctly imported"""
        print("\n" + "="*60)
        print("VERIFYING ALL RELATIONSHIPS")
        print("="*60)
        
        missing_prereqs = []
        missing_coreqs = []
        missing_equivs = []
        missing_courses = []
        
        # First, check if all courses exist
        with self.driver.session() as session:
            for dept_code, dept_info in course_data['departments'].items():
                for course in dept_info['courses']:
                    course_code = course.get('course_code')
                    if not course_code:
                        continue
                    
                    result = session.run("""
                        MATCH (c:Course {code: $code})
                        RETURN c
                    """, code=course_code)
                    
                    if not result.single():
                        missing_courses.append(course_code)
        
        if missing_courses:
            print(f"\n[ERROR] Missing {len(missing_courses)} courses in database:")
            for course in missing_courses[:20]:
                print(f"  - {course}")
            if len(missing_courses) > 20:
                print(f"  ... and {len(missing_courses) - 20} more")
        else:
            print("\n[OK] All courses exist in database")
        
        # Check relationships
        with self.driver.session() as session:
            for dept_code, dept_info in course_data['departments'].items():
                for course in dept_info['courses']:
                    course_code = course.get('course_code')
                    if not course_code:
                        continue
                    
                    relationships = course.get('relationships', {})
                    
                    # Check is_prerequisite_for (reverse prerequisite)
                    is_prereq_for = relationships.get('is_prerequisite_for', [])
                    for target_master_id in is_prereq_for:
                        target_code = self.convert_master_id_to_code(target_master_id)
                        if target_code:
                            result = session.run("""
                                MATCH (t:Course {code: $target_code})-[r:REQUIRES]->(c:Course {code: $course_code})
                                RETURN r
                            """, target_code=target_code, course_code=course_code)
                            if not result.single():
                                missing_prereqs.append((course_code, target_code, 'is_prerequisite_for'))
                    
                    # Check prerequisite_courses (forward prerequisite)
                    prereq_list = course.get('prerequisite_courses', [])
                    for prereq_master_id in prereq_list:
                        prereq_code = self.convert_master_id_to_code(prereq_master_id)
                        if prereq_code:
                            result = session.run("""
                                MATCH (c:Course {code: $course_code})-[r:REQUIRES]->(p:Course {code: $prereq_code})
                                RETURN r
                            """, course_code=course_code, prereq_code=prereq_code)
                            if not result.single():
                                # Check if it's in a requirement group
                                result2 = session.run("""
                                    MATCH (c:Course {code: $course_code})-[:HAS_REQUIREMENT]->(rg:RequirementGroup)-[:REQUIRES|OPTION]->(p:Course {code: $prereq_code})
                                    RETURN rg
                                """, course_code=course_code, prereq_code=prereq_code)
                                if not result2.single():
                                    missing_prereqs.append((course_code, prereq_code, 'prerequisite'))
                    
                    # Check corequisites
                    coreqs = relationships.get('corequisites', [])
                    for coreq_master_id in coreqs:
                        coreq_code = self.convert_master_id_to_code(coreq_master_id)
                        if coreq_code:
                            result = session.run("""
                                MATCH (c:Course {code: $course_code})-[r:COREQUISITE]-(co:Course {code: $coreq_code})
                                RETURN r
                            """, course_code=course_code, coreq_code=coreq_code)
                            if not result.single():
                                missing_coreqs.append((course_code, coreq_code))
                    
                    # Check equivalencies
                    equivalencies = relationships.get('equivalencies', [])
                    for equiv_master_id in equivalencies:
                        equiv_code = self.convert_master_id_to_code(equiv_master_id)
                        if equiv_code:
                            result = session.run("""
                                MATCH (c:Course {code: $course_code})-[r:EQUIVALENT]-(e:Course {code: $equiv_code})
                                RETURN r
                            """, course_code=course_code, equiv_code=equiv_code)
                            if not result.single():
                                missing_equivs.append((course_code, equiv_code))
        
        # Report results
        print(f"\n{'='*60}")
        print("VERIFICATION RESULTS")
        print(f"{'='*60}")
        
        if missing_prereqs:
            print(f"\n[ERROR] Missing {len(missing_prereqs)} prerequisite relationships:")
            for course, target, rel_type in missing_prereqs[:20]:
                if rel_type == 'is_prerequisite_for':
                    print(f"  {target} should REQUIRE {course} (from is_prerequisite_for)")
                else:
                    print(f"  {course} should REQUIRE {target} (from prerequisite_courses)")
            if len(missing_prereqs) > 20:
                print(f"  ... and {len(missing_prereqs) - 20} more")
        else:
            print("\n[OK] All prerequisite relationships verified!")
        
        if missing_coreqs:
            print(f"\n[ERROR] Missing {len(missing_coreqs)} corequisite relationships:")
            for course, coreq in missing_coreqs[:20]:
                print(f"  {course} should be COREQUISITE with {coreq}")
            if len(missing_coreqs) > 20:
                print(f"  ... and {len(missing_coreqs) - 20} more")
        else:
            print("\n[OK] All corequisite relationships verified!")
        
        if missing_equivs:
            print(f"\n[ERROR] Missing {len(missing_equivs)} equivalency relationships:")
            for course, equiv in missing_equivs[:20]:
                print(f"  {course} should be EQUIVALENT to {equiv}")
            if len(missing_equivs) > 20:
                print(f"  ... and {len(missing_equivs) - 20} more")
        else:
            print("\n[OK] All equivalency relationships verified!")
        
        print(f"\n{'='*60}")
        
        # Summary
        total_issues = len(missing_courses) + len(missing_prereqs) + len(missing_coreqs) + len(missing_equivs)
        if total_issues == 0:
            print("\n[SUCCESS] ALL RELATIONSHIPS VERIFIED SUCCESSFULLY!")
        else:
            print(f"\n[WARNING] Found {total_issues} issues that need to be fixed")
        
        print("="*60 + "\n")
        
        return {
            'missing_courses': len(missing_courses),
            'missing_prereqs': len(missing_prereqs),
            'missing_coreqs': len(missing_coreqs),
            'missing_equivs': len(missing_equivs)
        }
    
    def show_statistics(self):
        """Show database statistics"""
        with self.driver.session() as session:
            result = session.run("MATCH (c:Course) RETURN count(c) as count")
            course_count = result.single()['count']
            
            result = session.run("MATCH (d:Department) RETURN count(d) as count")
            dept_count = result.single()['count']
            
            result = session.run("MATCH ()-[r:REQUIRES]->() RETURN count(r) as count")
            prereq_count = result.single()['count']
            
            result = session.run("MATCH ()-[r:COREQUISITE]->() RETURN count(r) as count")
            coreq_count = result.single()['count']
            
            result = session.run("MATCH ()-[r:EQUIVALENT]->() RETURN count(r) as count")
            equiv_count = result.single()['count']
            
            result = session.run("MATCH (r:RequirementGroup) RETURN count(r) as count")
            req_group_count = result.single()['count']
            
            print(f"\n{'='*60}")
            print("DATABASE STATISTICS")
            print(f"{'='*60}")
            print(f"Total courses: {course_count}")
            print(f"Total departments: {dept_count}")
            print(f"Total REQUIRES relationships: {prereq_count}")
            print(f"Total COREQUISITE relationships: {coreq_count}")
            print(f"Total EQUIVALENT relationships: {equiv_count}")
            print(f"Total RequirementGroups: {req_group_count}")
            print(f"{'='*60}\n")


def main():
    # Get the path to courses_master.json
    script_dir = Path(__file__).parent
    courses_file = script_dir.parent / 'data' / 'course' / 'courses_master.json'
    
    if not courses_file.exists():
        print(f"[ERROR] Could not find courses_master.json at {courses_file}")
        return
    
    print("Loading course data...")
    with open(courses_file, 'r', encoding='utf-8') as f:
        course_data = json.load(f)
    
    verifier = RelationshipVerifier(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    
    try:
        print("\n" + "="*60)
        print("NEO4J RELATIONSHIP VERIFICATION")
        print("="*60)
        
        verifier.show_statistics()
        results = verifier.verify_all_relationships(course_data)
        
        if results['missing_courses'] + results['missing_prereqs'] + results['missing_coreqs'] + results['missing_equivs'] == 0:
            print("[SUCCESS] Database is fully synchronized with courses_master.json!")
        else:
            print("[WARNING] Please run import_courses_complete.py to fix the issues.")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        verifier.close()


if __name__ == "__main__":
    main()

