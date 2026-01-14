"""
Complete Neo4j Import Script for AUC Course Data
This script imports all courses and their relationships from courses_master.json
"""

import json
import os
from neo4j import GraphDatabase
from pathlib import Path

# Neo4j connection details
NEO4J_URI = "neo4j+s://6bd58e7f.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "jeiH1Na0rPA67jYospHTY2IjdLoq4AW23ujVAr_c7GM"

class CompleteCourseImporter:
    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.req_counter = 0
        self.course_master_id_to_code = {}  # Map COURSE:XXX_YYYY to "XXX YYYY"
    
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """Clear all existing data"""
        with self.driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as count")
            count = result.single()['count']
            session.run("MATCH (n) DETACH DELETE n")
            print(f"[OK] Database cleared! (Removed {count} nodes)")
    
    def create_constraints(self):
        """Create uniqueness constraints"""
        with self.driver.session() as session:
            # Drop existing constraints if they exist
            try:
                session.run("DROP CONSTRAINT course_code IF EXISTS")
            except:
                pass
            try:
                session.run("DROP CONSTRAINT course_master_id IF EXISTS")
            except:
                pass
            try:
                session.run("DROP CONSTRAINT dept_code IF EXISTS")
            except:
                pass
            
            # Create constraints
            session.run("""
                CREATE CONSTRAINT course_code IF NOT EXISTS
                FOR (c:Course) REQUIRE c.code IS UNIQUE
            """)
            session.run("""
                CREATE CONSTRAINT course_master_id IF NOT EXISTS
                FOR (c:Course) REQUIRE c.master_id IS UNIQUE
            """)
            session.run("""
                CREATE CONSTRAINT dept_code IF NOT EXISTS
                FOR (d:Department) REQUIRE d.code IS UNIQUE
            """)
            print("[OK] Constraints created!")
    
    def convert_master_id_to_code(self, master_id):
        """Convert COURSE:XXX_YYYY to XXX YYYY"""
        if not master_id or not master_id.startswith('COURSE:'):
            return None
        code = master_id.replace('COURSE:', '').replace('_', ' ')
        return code
    
    def build_course_mapping(self, course_data):
        """Build mapping from course_master_id to course_code"""
        for dept_code, dept_info in course_data['departments'].items():
            for course in dept_info['courses']:
                master_id = course.get('course_master_id')
                course_code = course.get('course_code')
                if master_id and course_code:
                    self.course_master_id_to_code[master_id] = course_code
        print(f"[OK] Built mapping for {len(self.course_master_id_to_code)} courses")
    
    def create_departments(self, course_data):
        """Create department nodes"""
        departments = {}
        for dept_code, dept_info in course_data['departments'].items():
            departments[dept_code] = dept_info['department_name']
        
        with self.driver.session() as session:
            for code, name in departments.items():
                session.run("""
                    MERGE (d:Department {code: $code})
                    SET d.name = $name
                """, code=code, name=name)
        
        print(f"[OK] Created {len(departments)} departments")
    
    def import_courses(self, course_data):
        """Import all courses with their properties"""
        total_courses = 0
        
        with self.driver.session() as session:
            for dept_code, dept_info in course_data['departments'].items():
                for course in dept_info['courses']:
                    course_code = course.get('course_code')
                    master_id = course.get('course_master_id')
                    
                    if not course_code:
                        print(f"  [WARNING] Skipping course without course_code: {master_id}")
                        continue
                    
                    # Handle credits (can be string like "1-3" or int)
                    credits = course.get('credits', 3)
                    if isinstance(credits, str):
                        try:
                            credits = int(credits.split('-')[0])
                        except:
                            credits = 3
                    
                    # Create course node with both code and master_id
                    session.run("""
                        MERGE (c:Course {code: $code})
                        SET c.master_id = $master_id,
                            c.title = $title,
                            c.description = $description,
                            c.credits = $credits,
                            c.level = $level,
                            c.when_offered = $when_offered,
                            c.prerequisite_human = $prereq_human,
                            c.department_code = $dept_code
                    """, 
                    code=course_code,
                    master_id=master_id or course_code,
                    title=course.get('title', ''),
                    description=course.get('canonical_description', ''),
                    credits=credits,
                    level=course.get('level', 'undergrad'),
                    when_offered=course.get('when_offered', ''),
                    prereq_human=course.get('prerequisite_human_readable', ''),
                    dept_code=dept_code
                    )
                    
                    # Link course to department
                    session.run("""
                        MATCH (c:Course {code: $code})
                        MATCH (d:Department {code: $dept_code})
                        MERGE (c)-[:BELONGS_TO]->(d)
                    """, code=course_code, dept_code=dept_code)
                    
                    total_courses += 1
        
        print(f"[OK] Imported {total_courses} courses")
    
    def parse_prerequisite_ast(self, course_code, prereq_ast):
        """Parse the prerequisite AST and create appropriate relationships"""
        if not prereq_ast:
            return
        
        with self.driver.session() as session:
            self._process_ast_node(session, course_code, prereq_ast, is_root=True)
    
    def _process_ast_node(self, session, course_code, node, is_root=False, parent_req_id=None):
        """Recursively process AST nodes"""
        if not node:
            return None
        
        op = node.get('op')
        
        # Handle simple COURSE prerequisite
        if op == 'COURSE':
            prereq_master_id = node.get('course_master_id')
            if not prereq_master_id:
                return None
            
            prereq_code = self.convert_master_id_to_code(prereq_master_id)
            if not prereq_code:
                return None
            
            if is_root:
                # Direct prerequisite (no grouping needed)
                session.run("""
                    MATCH (c:Course {code: $course_code})
                    MATCH (p:Course {code: $prereq_code})
                    MERGE (c)-[:REQUIRES]->(p)
                """, course_code=course_code, prereq_code=prereq_code)
            
            return prereq_code
        
        # Handle CONCURRENT (corequisite)
        elif op == 'CONCURRENT':
            prereq_master_id = node.get('course_master_id')
            if not prereq_master_id:
                return None
            
            prereq_code = self.convert_master_id_to_code(prereq_master_id)
            if not prereq_code:
                return None
            
            session.run("""
                MATCH (c:Course {code: $course_code})
                MATCH (p:Course {code: $prereq_code})
                MERGE (c)-[:COREQUISITE]->(p)
            """, course_code=course_code, prereq_code=prereq_code)
            
            return prereq_code
        
        # Handle AND logic
        elif op == 'AND':
            self.req_counter += 1
            req_id = f"req_{course_code}_{self.req_counter}"
            
            # Create AND requirement group
            session.run("""
                MATCH (c:Course {code: $course_code})
                MERGE (r:RequirementGroup {id: $req_id})
                SET r.type = 'AND',
                    r.description = 'All of these courses required'
                MERGE (c)-[:HAS_REQUIREMENT]->(r)
            """, course_code=course_code, req_id=req_id)
            
            # Process all children
            for arg in node.get('args', []):
                child_result = self._process_ast_node(session, course_code, arg, parent_req_id=req_id)
                
                if child_result and isinstance(child_result, str):
                    # Direct course
                    session.run("""
                        MATCH (r:RequirementGroup {id: $req_id})
                        MATCH (p:Course {code: $prereq_code})
                        MERGE (r)-[:REQUIRES]->(p)
                    """, req_id=req_id, prereq_code=child_result)
            
            return req_id
        
        # Handle OR logic
        elif op == 'OR':
            self.req_counter += 1
            req_id = f"req_{course_code}_{self.req_counter}"
            
            # Create OR requirement group
            session.run("""
                MATCH (c:Course {code: $course_code})
                MERGE (r:RequirementGroup {id: $req_id})
                SET r.type = 'OR',
                    r.description = 'One of these courses required'
                MERGE (c)-[:HAS_REQUIREMENT]->(r)
            """, course_code=course_code, req_id=req_id)
            
            # Process all children
            for arg in node.get('args', []):
                child_result = self._process_ast_node(session, course_code, arg, parent_req_id=req_id)
                
                if child_result and isinstance(child_result, str):
                    # Direct course
                    session.run("""
                        MATCH (r:RequirementGroup {id: $req_id})
                        MATCH (p:Course {code: $prereq_code})
                        MERGE (r)-[:OPTION]->(p)
                    """, req_id=req_id, prereq_code=child_result)
            
            return req_id
        
        # Handle STANDING requirements
        elif op == 'STANDING':
            level = node.get('level', 'unknown')
            session.run("""
                MATCH (c:Course {code: $course_code})
                MERGE (s:StandingRequirement {level: $level})
                MERGE (c)-[:REQUIRES_STANDING]->(s)
            """, course_code=course_code, level=level)
            
            return None
        
        # Handle APPROVAL requirements
        elif op == 'APPROVAL':
            approval_type = node.get('type', 'unknown')
            session.run("""
                MATCH (c:Course {code: $course_code})
                MERGE (a:ApprovalRequirement {type: $approval_type})
                MERGE (c)-[:REQUIRES_APPROVAL]->(a)
            """, course_code=course_code, approval_type=approval_type)
            
            return None
        
        return None
    
    def create_prerequisites_from_ast(self, course_data):
        """Create prerequisite relationships from AST"""
        prereq_count = 0
        
        for dept_code, dept_info in course_data['departments'].items():
            for course in dept_info['courses']:
                course_code = course.get('course_code')
                if not course_code:
                    continue
                
                prereq_ast = course.get('prerequisite_ast')
                
                if prereq_ast:
                    self.parse_prerequisite_ast(course_code, prereq_ast)
                    prereq_count += 1
        
        print(f"[OK] Created prerequisite structures for {prereq_count} courses")
    
    def create_prerequisites_from_list(self, course_data):
        """Create prerequisite relationships from prerequisite_courses list"""
        prereq_count = 0
        
        with self.driver.session() as session:
            for dept_code, dept_info in course_data['departments'].items():
                for course in dept_info['courses']:
                    course_code = course.get('course_code')
                    if not course_code:
                        continue
                    
                    prereq_list = course.get('prerequisite_courses', [])
                    
                    for prereq_master_id in prereq_list:
                        prereq_code = self.convert_master_id_to_code(prereq_master_id)
                        if not prereq_code:
                            continue
                        
                        # Check if relationship already exists (from AST)
                        result = session.run("""
                            MATCH (c:Course {code: $course_code})
                            MATCH (p:Course {code: $prereq_code})
                            WHERE NOT (c)-[:REQUIRES]->(p)
                            MERGE (c)-[:REQUIRES]->(p)
                            RETURN c, p
                        """, course_code=course_code, prereq_code=prereq_code)
                        
                        if result.single():
                            prereq_count += 1
        
        print(f"[OK] Created {prereq_count} additional prerequisite relationships from lists")
    
    def create_is_prerequisite_for(self, course_data):
        """Create reverse prerequisite relationships from is_prerequisite_for field"""
        prereq_count = 0
        
        with self.driver.session() as session:
            for dept_code, dept_info in course_data['departments'].items():
                for course in dept_info['courses']:
                    course_code = course.get('course_code')
                    if not course_code:
                        continue
                    
                    relationships = course.get('relationships', {})
                    is_prereq_for = relationships.get('is_prerequisite_for', [])
                    
                    for target_master_id in is_prereq_for:
                        target_code = self.convert_master_id_to_code(target_master_id)
                        if not target_code:
                            continue
                        
                        # Create reverse relationship (this course is prerequisite for target)
                        result = session.run("""
                            MATCH (c:Course {code: $course_code})
                            MATCH (t:Course {code: $target_code})
                            WHERE NOT (t)-[:REQUIRES]->(c)
                            MERGE (t)-[:REQUIRES]->(c)
                            RETURN c, t
                        """, course_code=course_code, target_code=target_code)
                        
                        if result.single():
                            prereq_count += 1
        
        print(f"[OK] Created {prereq_count} prerequisite relationships from is_prerequisite_for")
    
    def create_corequisites(self, course_data):
        """Create corequisite relationships from relationships field"""
        coreq_count = 0
        
        with self.driver.session() as session:
            for dept_code, dept_info in course_data['departments'].items():
                for course in dept_info['courses']:
                    course_code = course.get('course_code')
                    if not course_code:
                        continue
                    
                    relationships = course.get('relationships', {})
                    coreqs = relationships.get('corequisites', [])
                    
                    for coreq_master_id in coreqs:
                        coreq_code = self.convert_master_id_to_code(coreq_master_id)
                        if not coreq_code:
                            continue
                        
                        # Create bidirectional corequisite relationship
                        result = session.run("""
                            MATCH (c:Course {code: $course_code})
                            MATCH (co:Course {code: $coreq_code})
                            WHERE NOT (c)-[:COREQUISITE]-(co)
                            MERGE (c)-[:COREQUISITE]->(co)
                            MERGE (co)-[:COREQUISITE]->(c)
                            RETURN c, co
                        """, course_code=course_code, coreq_code=coreq_code)
                        
                        if result.single():
                            coreq_count += 1
        
        print(f"[OK] Created {coreq_count} corequisite relationships")
    
    def create_equivalencies(self, course_data):
        """Create equivalency relationships"""
        equiv_count = 0
        
        with self.driver.session() as session:
            for dept_code, dept_info in course_data['departments'].items():
                for course in dept_info['courses']:
                    course_code = course.get('course_code')
                    if not course_code:
                        continue
                    
                    relationships = course.get('relationships', {})
                    equivalencies = relationships.get('equivalencies', [])
                    
                    for equiv_master_id in equivalencies:
                        equiv_code = self.convert_master_id_to_code(equiv_master_id)
                        if not equiv_code:
                            continue
                        
                        # Create bidirectional equivalency relationship
                        result = session.run("""
                            MATCH (c:Course {code: $course_code})
                            MATCH (e:Course {code: $equiv_code})
                            WHERE NOT (c)-[:EQUIVALENT]-(e)
                            MERGE (c)-[:EQUIVALENT]->(e)
                            MERGE (e)-[:EQUIVALENT]->(c)
                            RETURN c, e
                        """, course_code=course_code, equiv_code=equiv_code)
                        
                        if result.single():
                            equiv_count += 1
        
        print(f"[OK] Created {equiv_count} equivalency relationships")
    
    def create_program_structure(self):
        """Create CS and CE program nodes"""
        with self.driver.session() as session:
            session.run("""
                MERGE (p:Program {code: 'CS'})
                SET p.name = 'Computer Science',
                    p.total_credits = 120,
                    p.department = 'Computer Science and Engineering'
            """)
            
            session.run("""
                MERGE (p:Program {code: 'CE'})
                SET p.name = 'Computer Engineering',
                    p.total_credits = 120,
                    p.department = 'Computer Science and Engineering'
            """)
        
        print("[OK] Created CS and CE programs")
    
    def link_core_courses(self):
        """Link fundamental courses to programs as core requirements"""
        core_courses = {
            'CS': [
                'CSCE 1001', 'CSCE 1101', 'CSCE 1102', 'CSCE 2211', 
                'CSCE 2202', 'CSCE 2203', 'CSCE 2501', 'CSCE 3701',
                'CSCE 3601', 'CSCE 4980', 'CSCE 4981'
            ],
            'CE': [
                'CSCE 1001', 'CSCE 1101', 'CSCE 1102', 'CSCE 2211',
                'CSCE 2301', 'CSCE 2302', 'CSCE 2303', 'CSCE 3301',
                'CSCE 3302', 'CSCE 3312', 'CSCE 3313', 'CSCE 3401',
                'CSCE 4301', 'CSCE 4302', 'CSCE 4980', 'CSCE 4981'
            ]
        }
        
        with self.driver.session() as session:
            for program, courses in core_courses.items():
                for course_code in courses:
                    session.run("""
                        MATCH (p:Program {code: $program})
                        MATCH (c:Course {code: $course_code})
                        MERGE (p)-[r:REQUIRES]->(c)
                        SET r.type = 'core'
                    """, program=program, course_code=course_code)
        
        print("[OK] Linked core courses to programs")
    
    def verify_import(self):
        """Verify the import and show statistics"""
        with self.driver.session() as session:
            # Count everything
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
            
            # Sample relationships
            print(f"\n{'='*60}")
            print("IMPORT SUMMARY")
            print(f"{'='*60}")
            print(f"Total courses: {course_count}")
            print(f"Total departments: {dept_count}")
            print(f"Total REQUIRES relationships: {prereq_count}")
            print(f"Total COREQUISITE relationships: {coreq_count}")
            print(f"Total EQUIVALENT relationships: {equiv_count}")
            print(f"Total RequirementGroups: {req_group_count}")
            
            # Sample prerequisite chain
            print(f"\nSample prerequisite chain:")
            result = session.run("""
                MATCH (c:Course)-[:REQUIRES*2]->(p:Course)
                WHERE c.code STARTS WITH 'CSCE'
                RETURN c.code as course, p.code as prereq
                LIMIT 5
            """)
            for record in result:
                print(f"  {record['course']} requires (via chain) {record['prereq']}")
            
            # Sample corequisites
            print(f"\nSample corequisites:")
            result = session.run("""
                MATCH (c:Course)-[:COREQUISITE]->(co:Course)
                WHERE c.code STARTS WITH 'CSCE'
                RETURN c.code as course1, co.code as course2
                LIMIT 5
            """)
            for record in result:
                print(f"  {record['course1']} <-> {record['course2']}")
            
            # Sample equivalencies
            result = session.run("""
                MATCH (c:Course)-[:EQUIVALENT]->(e:Course)
                WHERE c.code STARTS WITH 'CSCE'
                RETURN c.code as course1, e.code as course2
                LIMIT 5
            """)
            if result.peek():
                print(f"\nSample equivalencies:")
                for record in result:
                    print(f"  {record['course1']} ≡ {record['course2']}")
            
            print(f"{'='*60}\n")
    
    def verify_relationships(self, course_data):
        """Verify that all relationships in JSON are correctly imported"""
        print("\n" + "="*60)
        print("VERIFYING RELATIONSHIPS")
        print("="*60)
        
        missing_prereqs = []
        missing_coreqs = []
        missing_equivs = []
        
        with self.driver.session() as session:
            for dept_code, dept_info in course_data['departments'].items():
                for course in dept_info['courses']:
                    course_code = course.get('course_code')
                    if not course_code:
                        continue
                    
                    relationships = course.get('relationships', {})
                    
                    # Check is_prerequisite_for
                    is_prereq_for = relationships.get('is_prerequisite_for', [])
                    for target_master_id in is_prereq_for:
                        target_code = self.convert_master_id_to_code(target_master_id)
                        if target_code:
                            result = session.run("""
                                MATCH (t:Course {code: $target_code})-[r:REQUIRES]->(c:Course {code: $course_code})
                                RETURN r
                            """, target_code=target_code, course_code=course_code)
                            if not result.single():
                                missing_prereqs.append((course_code, target_code))
                    
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
        
        if missing_prereqs:
            print(f"\n[WARNING] Missing {len(missing_prereqs)} prerequisite relationships:")
            for course, target in missing_prereqs[:10]:
                print(f"  {target} should REQUIRE {course}")
        else:
            print("\n[OK] All prerequisite relationships verified!")
        
        if missing_coreqs:
            print(f"\n[WARNING] Missing {len(missing_coreqs)} corequisite relationships:")
            for course, coreq in missing_coreqs[:10]:
                print(f"  {course} should be COREQUISITE with {coreq}")
        else:
            print("\n[OK] All corequisite relationships verified!")
        
        if missing_equivs:
            print(f"\n[WARNING] Missing {len(missing_equivs)} equivalency relationships:")
            for course, equiv in missing_equivs[:10]:
                print(f"  {course} should be EQUIVALENT to {equiv}")
        else:
            print("\n[OK] All equivalency relationships verified!")
        
        print("="*60 + "\n")


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
    
    importer = CompleteCourseImporter(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    
    try:
        print("\n" + "="*60)
        print("STARTING COMPLETE NEO4J IMPORT")
        print("="*60 + "\n")
        
        # Clear and recreate
        importer.clear_database()
        importer.create_constraints()
        
        # Build course mapping first
        print("\nStep 0: Building course mapping...")
        importer.build_course_mapping(course_data)
        
        print("\nStep 1: Creating departments...")
        importer.create_departments(course_data)
        
        print("\nStep 2: Importing courses...")
        importer.import_courses(course_data)
        
        print("\nStep 3: Creating prerequisite relationships from AST...")
        importer.create_prerequisites_from_ast(course_data)
        
        print("\nStep 4: Creating prerequisite relationships from lists...")
        importer.create_prerequisites_from_list(course_data)
        
        print("\nStep 5: Creating reverse prerequisite relationships (is_prerequisite_for)...")
        importer.create_is_prerequisite_for(course_data)
        
        print("\nStep 6: Creating corequisite relationships...")
        importer.create_corequisites(course_data)
        
        print("\nStep 7: Creating equivalency relationships...")
        importer.create_equivalencies(course_data)
        
        print("\nStep 8: Creating program structure...")
        importer.create_program_structure()
        
        print("\nStep 9: Linking core courses...")
        importer.link_core_courses()
        
        print("\nStep 10: Verifying import...")
        importer.verify_import()
        
        print("\nStep 11: Verifying relationships...")
        importer.verify_relationships(course_data)
        
        print("\n" + "="*60)
        print("[SUCCESS] COMPLETE IMPORT FINISHED!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        importer.close()


if __name__ == "__main__":
    main()

