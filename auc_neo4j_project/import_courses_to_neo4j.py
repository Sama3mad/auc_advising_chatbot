import json
from neo4j import GraphDatabase

NEO4J_URI = "neo4j+s://6bd58e7f.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "jeiH1Na0rPA67jYospHTY2IjdLoq4AW23ujVAr_c7GM"

class ComplexCourseImporter:
    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.req_counter = 0  # For unique requirement IDs
    
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """Clear all existing data"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("✓ Database cleared!")
    
    def create_constraints(self):
        """Create uniqueness constraints"""
        with self.driver.session() as session:
            session.run("""
                CREATE CONSTRAINT course_code IF NOT EXISTS
                FOR (c:Course) REQUIRE c.code IS UNIQUE
            """)
            session.run("""
                CREATE CONSTRAINT dept_code IF NOT EXISTS
                FOR (d:Department) REQUIRE d.code IS UNIQUE
            """)
            print("✓ Constraints created!")
    
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
            
            print(f"✓ Created {len(departments)} departments")
    
    def import_courses(self, course_data):
        """Import all courses with their properties"""
        total_courses = 0
        
        with self.driver.session() as session:
            for dept_code, dept_info in course_data['departments'].items():
                for course in dept_info['courses']:
                    # Handle credits (can be string like "1-3" or int)
                    credits = course.get('credits', 3)
                    if isinstance(credits, str):
                        credits = int(credits.split('-')[0])
                    
                    # Create course node
                    session.run("""
                        MERGE (c:Course {code: $code})
                        SET c.title = $title,
                            c.description = $description,
                            c.credits = $credits,
                            c.level = $level,
                            c.when_offered = $when_offered,
                            c.prerequisite_human = $prereq_human,
                            c.department_code = $dept_code
                    """, 
                    code=course['course_code'],
                    title=course['title'],
                    description=course['canonical_description'],
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
                    """, code=course['course_code'], dept_code=dept_code)
                    
                    total_courses += 1
        
        print(f"✓ Imported {total_courses} courses")
    
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
            prereq_code = node['course_master_id'].replace('COURSE:', '').replace('_', ' ')
            
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
            prereq_code = node['course_master_id'].replace('COURSE:', '').replace('_', ' ')
            
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
                course_code = course['course_code']
                prereq_ast = course.get('prerequisite_ast')
                
                if prereq_ast:
                    self.parse_prerequisite_ast(course_code, prereq_ast)
                    prereq_count += 1
                    print(f"  Processed: {course_code}")
        
        print(f"\n✓ Created prerequisite structures for {prereq_count} courses")
    
    def create_corequisites(self, course_data):
        """Create corequisite relationships from relationships field"""
        coreq_count = 0
        
        with self.driver.session() as session:
            for dept_code, dept_info in course_data['departments'].items():
                for course in dept_info['courses']:
                    course_code = course['course_code']
                    coreqs = course.get('relationships', {}).get('corequisites', [])
                    
                    for coreq in coreqs:
                        if coreq.startswith('COURSE:'):
                            coreq_code = coreq.replace('COURSE:', '').replace('_', ' ')
                            
                            # Only create if not already created from AST
                            result = session.run("""
                                MATCH (c:Course {code: $course_code})
                                MATCH (co:Course {code: $coreq_code})
                                WHERE NOT (c)-[:COREQUISITE]-(co)
                                MERGE (c)-[:COREQUISITE]->(co)
                                RETURN c, co
                            """, course_code=course_code, coreq_code=coreq_code)
                            
                            if result.single():
                                coreq_count += 1
        
        print(f"✓ Created {coreq_count} additional corequisite relationships")
    
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
            
            print("✓ Created CS and CE programs")
    
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
        
        print("✓ Linked core courses to programs")
    
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
            
            result = session.run("MATCH (r:RequirementGroup) RETURN count(r) as count")
            req_group_count = result.single()['count']
            
            # Sample complex prerequisites
            result = session.run("""
                MATCH (c:Course)-[:HAS_REQUIREMENT]->(r:RequirementGroup)
                RETURN c.code as course, r.type as req_type, r.id as req_id
                LIMIT 5
            """)
            
            print(f"\n{'='*60}")
            print("IMPORT SUMMARY")
            print(f"{'='*60}")
            print(f"Total courses: {course_count}")
            print(f"Total departments: {dept_count}")
            print(f"Total REQUIRES relationships: {prereq_count}")
            print(f"Total COREQUISITE relationships: {coreq_count}")
            print(f"Total RequirementGroups: {req_group_count}")
            print(f"\nSample complex requirements:")
            for record in result:
                print(f"  {record['course']}: {record['req_type']} requirement ({record['req_id']})")
            print(f"{'='*60}\n")

def main():
    print("Loading course data...")
    with open('course_data.json', 'r', encoding='utf-8') as f:
        course_data = json.load(f)
    
    importer = ComplexCourseImporter(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    
    try:
        print("\n" + "="*60)
        print("STARTING COMPLEX NEO4J IMPORT")
        print("="*60 + "\n")
        
        # Clear and recreate
        importer.clear_database()
        importer.create_constraints()
        
        print("\nStep 1: Creating departments...")
        importer.create_departments(course_data)
        
        print("\nStep 2: Importing courses...")
        importer.import_courses(course_data)
        
        print("\nStep 3: Creating complex prerequisite structures from AST...")
        importer.create_prerequisites_from_ast(course_data)
        
        print("\nStep 4: Creating additional corequisites...")
        importer.create_corequisites(course_data)
        
        print("\nStep 5: Creating program structure...")
        importer.create_program_structure()
        
        print("\nStep 6: Linking core courses...")
        importer.link_core_courses()
        
        print("\nStep 7: Verifying import...")
        importer.verify_import()
        
        print("\n" + "="*60)
        print("✓ COMPLEX IMPORT COMPLETED!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        importer.close()

if __name__ == "__main__":
    main()