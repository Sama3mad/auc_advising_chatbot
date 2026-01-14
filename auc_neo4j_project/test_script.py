from neo4j import GraphDatabase

NEO4J_URI = "neo4j+s://6bd58e7f.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "jeiH1Na0rPA67jYospHTY2IjdLoq4AW23ujVAr_c7GM"

class CourseAdvisor:
    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
    
    def close(self):
        self.driver.close()
    
    def get_course_info(self, course_code):
        """Get detailed information about a specific course"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Course {code: $code})
                RETURN c.code as code, c.title as title, c.credits as credits,
                       c.description as description, c.department_code as department,
                       c.when_offered as when_offered, c.prerequisite_human as prereq_text
            """, code=course_code)
            
            record = result.single()
            if record:
                return dict(record)
            return None
    
    def get_prerequisites_detailed(self, course_code):
        """Get detailed prerequisite structure including AND/OR logic"""
        with self.driver.session() as session:
            # Check for simple direct prerequisites
            result = session.run("""
                MATCH (c:Course {code: $code})-[:REQUIRES]->(p:Course)
                RETURN 'direct' as type, p.code as code, p.title as title, 
                       p.credits as credits
            """, code=course_code)
            
            direct_prereqs = [dict(record) for record in result]
            
            # Check for complex requirement groups
            result = session.run("""
                MATCH (c:Course {code: $code})-[:HAS_REQUIREMENT]->(rg:RequirementGroup)
                RETURN rg.id as req_id, rg.type as req_type, rg.description as description
            """, code=course_code)
            
            requirement_groups = []
            for record in result:
                req_id = record['req_id']
                req_type = record['req_type']
                
                # Get courses in this requirement group
                if req_type == 'AND':
                    courses_result = session.run("""
                        MATCH (rg:RequirementGroup {id: $req_id})-[:REQUIRES]->(p:Course)
                        RETURN p.code as code, p.title as title, p.credits as credits
                    """, req_id=req_id)
                elif req_type == 'OR':
                    courses_result = session.run("""
                        MATCH (rg:RequirementGroup {id: $req_id})-[:OPTION]->(p:Course)
                        RETURN p.code as code, p.title as title, p.credits as credits
                    """, req_id=req_id)
                else:
                    courses_result = []
                
                courses = [dict(r) for r in courses_result]
                
                requirement_groups.append({
                    'type': req_type,
                    'description': record['description'],
                    'courses': courses
                })
            
            # Check for standing requirements
            result = session.run("""
                MATCH (c:Course {code: $code})-[:REQUIRES_STANDING]->(s:StandingRequirement)
                RETURN s.level as level
            """, code=course_code)
            
            standing_reqs = [record['level'] for record in result]
            
            # Check for approval requirements
            result = session.run("""
                MATCH (c:Course {code: $code})-[:REQUIRES_APPROVAL]->(a:ApprovalRequirement)
                RETURN a.type as type
            """, code=course_code)
            
            approval_reqs = [record['type'] for record in result]
            
            return {
                'direct': direct_prereqs,
                'groups': requirement_groups,
                'standing': standing_reqs,
                'approval': approval_reqs
            }
    
    def get_prerequisites_simple(self, course_code):
        """Get simple list of all prerequisite courses (flattened)"""
        with self.driver.session() as session:
            # Get all courses that are prerequisites (direct or in groups)
            result = session.run("""
                MATCH (c:Course {code: $code})
                OPTIONAL MATCH (c)-[:REQUIRES]->(p1:Course)
                OPTIONAL MATCH (c)-[:HAS_REQUIREMENT]->()-[:REQUIRES]->(p2:Course)
                OPTIONAL MATCH (c)-[:HAS_REQUIREMENT]->()-[:OPTION]->(p3:Course)
                WITH c, collect(DISTINCT p1) + collect(DISTINCT p2) + collect(DISTINCT p3) as prereqs
                UNWIND prereqs as p
                WHERE p IS NOT NULL
                RETURN DISTINCT p.code as code, p.title as title, p.credits as credits
                ORDER BY p.code
            """, code=course_code)
            
            return [dict(record) for record in result]
    
    def get_corequisites(self, course_code):
        """Get corequisites for a course"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Course {code: $code})-[:COREQUISITE]->(co:Course)
                RETURN co.code as code, co.title as title, co.credits as credits
            """, code=course_code)
            
            return [dict(record) for record in result]
    
    def can_take_course(self, course_code, completed_courses):
        """Check if student can take a course based on completed courses
        Returns: (can_take: bool, missing: list, details: dict)
        """
        prereq_structure = self.get_prerequisites_detailed(course_code)
        
        missing = []
        details = {
            'direct_missing': [],
            'group_status': [],
            'standing_missing': [],
            'approval_missing': []
        }
        
        # Check direct prerequisites
        for prereq in prereq_structure['direct']:
            if prereq['code'] not in completed_courses:
                missing.append(prereq['code'])
                details['direct_missing'].append(prereq)
        
        # Check requirement groups
        for group in prereq_structure['groups']:
            if group['type'] == 'AND':
                # All courses in AND group must be completed
                group_missing = []
                for course in group['courses']:
                    if course['code'] not in completed_courses:
                        group_missing.append(course['code'])
                        missing.append(course['code'])
                
                details['group_status'].append({
                    'type': 'AND',
                    'satisfied': len(group_missing) == 0,
                    'missing': group_missing,
                    'description': f"Need ALL: {', '.join([c['code'] for c in group['courses']])}"
                })
            
            elif group['type'] == 'OR':
                # At least one course in OR group must be completed
                satisfied = any(course['code'] in completed_courses for course in group['courses'])
                
                if not satisfied:
                    # Add all options to missing (student needs to pick one)
                    group_codes = [c['code'] for c in group['courses']]
                    details['group_status'].append({
                        'type': 'OR',
                        'satisfied': False,
                        'options': group_codes,
                        'description': f"Need ONE OF: {', '.join(group_codes)}"
                    })
                    # Don't add individual courses to missing list for OR groups
                else:
                    details['group_status'].append({
                        'type': 'OR',
                        'satisfied': True,
                        'options': [c['code'] for c in group['courses']],
                        'description': f"✓ Satisfied (one of: {', '.join([c['code'] for c in group['courses']])})"
                    })
        
        # Check standing requirements
        for standing in prereq_structure['standing']:
            details['standing_missing'].append(f"{standing.capitalize()} standing required")
        
        # Check approval requirements
        for approval in prereq_structure['approval']:
            details['approval_missing'].append(f"{approval.capitalize()} approval required")
        
        # Can take if:
        # 1. No direct prerequisites missing
        # 2. All AND groups satisfied
        # 3. All OR groups satisfied
        can_take = (
            len(details['direct_missing']) == 0 and 
            all(g['satisfied'] for g in details['group_status'] if g['type'] == 'AND') and
            all(g['satisfied'] for g in details['group_status'] if g['type'] == 'OR')
        )
        
        return can_take, missing, details
    
    def get_courses_available(self, completed_courses):
        """Get all courses a student can take based on completed courses"""
        with self.driver.session() as session:
            # This is complex - we need to check each course
            result = session.run("""
                MATCH (c:Course)
                WHERE NOT c.code IN $completed
                RETURN c.code as code, c.title as title, c.credits as credits
                ORDER BY c.code
            """, completed=completed_courses)
            
            all_courses = [dict(record) for record in result]
            
            # Check which ones the student can actually take
            available = []
            for course in all_courses:
                can_take, _, _ = self.can_take_course(course['code'], completed_courses)
                if can_take:
                    available.append(course)
            
            return available
    
    def get_prerequisite_chain(self, course_code, completed_courses=None):
        """Get the entire prerequisite tree with visual indentation"""
        if completed_courses is None:
            completed_courses = []
        
        chain = []
        self._build_prereq_tree(course_code, completed_courses, chain, depth=0, visited=set())
        return chain
    
    def _build_prereq_tree(self, course_code, completed_courses, chain, depth, visited):
        """Recursively build prerequisite tree"""
        if course_code in visited:
            return
        visited.add(course_code)
        
        # Get course info
        course_info = self.get_course_info(course_code)
        if not course_info:
            return
        
        is_completed = course_code in completed_courses
        
        chain.append({
            'code': course_code,
            'title': course_info['title'],
            'depth': depth,
            'completed': is_completed
        })
        
        # Get prerequisites
        prereqs = self.get_prerequisites_simple(course_code)
        for prereq in prereqs:
            self._build_prereq_tree(prereq['code'], completed_courses, chain, depth + 1, visited)
    
    def get_program_requirements(self, program_code):
        """Get all required courses for a program"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Program {code: $program})-[r:REQUIRES]->(c:Course)
                RETURN c.code as code, c.title as title, c.credits as credits,
                       r.type as type
                ORDER BY r.type, c.code
            """, program=program_code)
            
            requirements = {'core': [], 'major': [], 'elective': []}
            for record in result:
                req_type = record.get('type', 'core')
                requirements[req_type].append({
                    'code': record['code'],
                    'title': record['title'],
                    'credits': record['credits']
                })
            
            return requirements
    
    def get_remaining_requirements(self, program_code, completed_courses):
        """Get remaining requirements for program completion"""
        requirements = self.get_program_requirements(program_code)
        remaining = {'core': [], 'major': [], 'elective': []}
        
        for req_type in requirements:
            for course in requirements[req_type]:
                if course['code'] not in completed_courses:
                    remaining[req_type].append(course)
        
        return remaining
    
    def recommend_next_courses(self, program_code, completed_courses, max_credits=18):
        """Recommend next courses based on prerequisites and credit limit"""
        available = self.get_courses_available(completed_courses)
        remaining = self.get_remaining_requirements(program_code, completed_courses)
        
        recommendations = []
        total_credits = 0
        
        # Prioritize core courses
        for course in remaining['core']:
            if total_credits + course['credits'] <= max_credits:
                if course['code'] in [c['code'] for c in available]:
                    recommendations.append(course)
                    total_credits += course['credits']
        
        # Then major courses
        for course in remaining.get('major', []):
            if total_credits + course['credits'] <= max_credits:
                if course['code'] in [c['code'] for c in available]:
                    recommendations.append(course)
                    total_credits += course['credits']
        
        return recommendations, total_credits
    
    def find_courses_by_name(self, search_term):
        """Search courses by name or code"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Course)
                WHERE toLower(c.title) CONTAINS toLower($term) 
                   OR toLower(c.code) CONTAINS toLower($term)
                   OR toLower(c.description) CONTAINS toLower($term)
                RETURN c.code as code, c.title as title, c.credits as credits
                ORDER BY c.code
                LIMIT 20
            """, term=search_term)
            
            return [dict(record) for record in result]
    
    def get_courses_by_department(self, department_code):
        """Get all courses in a specific department"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Course)
                WHERE c.department_code = $dept
                RETURN c.code as code, c.title as title, c.credits as credits
                ORDER BY c.code
            """, dept=department_code)
            
            return [dict(record) for record in result]
    
    def get_course_dependencies(self, course_code):
        """Get all courses that require this course as a prerequisite"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Course)-[:REQUIRES]->(p:Course {code: $code})
                RETURN c.code as code, c.title as title, c.credits as credits
                UNION
                MATCH (c:Course)-[:HAS_REQUIREMENT]->()-[:REQUIRES]->(p:Course {code: $code})
                RETURN c.code as code, c.title as title, c.credits as credits
                UNION
                MATCH (c:Course)-[:HAS_REQUIREMENT]->()-[:OPTION]->(p:Course {code: $code})
                RETURN c.code as code, c.title as title, c.credits as credits
                ORDER BY code
            """, code=course_code)
            
            return [dict(record) for record in result]
    
    def get_all_departments(self):
        """Get list of all departments"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (d:Department)
                RETURN d.code as code, d.name as name
                ORDER BY d.name
            """)
            
            return [dict(record) for record in result]
    
    def explain_prerequisites(self, course_code):
        """Get a human-readable explanation of prerequisites"""
        prereqs = self.get_prerequisites_detailed(course_code)
        
        explanation = []
        
        if prereqs['direct']:
            explanation.append("Direct prerequisites:")
            for p in prereqs['direct']:
                explanation.append(f"  • {p['code']}: {p['title']}")
        
        if prereqs['groups']:
            explanation.append("\nComplex requirements:")
            for group in prereqs['groups']:
                if group['type'] == 'AND':
                    explanation.append(f"  ALL of these courses:")
                    for c in group['courses']:
                        explanation.append(f"    • {c['code']}: {c['title']}")
                elif group['type'] == 'OR':
                    explanation.append(f"  ONE of these courses:")
                    for c in group['courses']:
                        explanation.append(f"    • {c['code']}: {c['title']}")
        
        if prereqs['standing']:
            explanation.append("\nStanding requirements:")
            for s in prereqs['standing']:
                explanation.append(f"  • {s.capitalize()} standing")
        
        if prereqs['approval']:
            explanation.append("\nApproval requirements:")
            for a in prereqs['approval']:
                explanation.append(f"  • {a.capitalize()} approval")
        
        return "\n".join(explanation) if explanation else "No prerequisites"

# Example usage
def example_queries():
    advisor = CourseAdvisor(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    
    try:
        print("="*60)
        print("Example 1: Get Prerequisites for CSCE 3301")
        print("="*60)
        
        print("\nDetailed structure:")
        prereqs = advisor.get_prerequisites_detailed("CSCE 3301")
        print(f"Direct: {prereqs['direct']}")
        print(f"Groups: {prereqs['groups']}")
        
        print("\nHuman explanation:")
        print(advisor.explain_prerequisites("CSCE 3301"))
        
        print("\n" + "="*60)
        print("Example 2: Can Student Take CSCE 3301?")
        print("="*60)
        
        completed = ["CSCE 1001", "CSCE 1101", "CSCE 2301", "CSCE 2302", "PHYS 2211"]
        can_take, missing, details = advisor.can_take_course("CSCE 3301", completed)
        
        print(f"\nCompleted courses: {', '.join(completed)}")
        print(f"Can take CSCE 3301? {can_take}")
        
        if not can_take:
            print("\nMissing requirements:")
            for status in details['group_status']:
                if not status['satisfied']:
                    print(f"  {status['description']}")
        
        print("\n" + "="*60)
        print("Example 3: Available Courses")
        print("="*60)
        
        available = advisor.get_courses_available(completed)
        print(f"\nYou can take {len(available)} courses:")
        for course in available[:10]:
            print(f"  • {course['code']}: {course['title']}")
        
    finally:
        advisor.close()

if __name__ == "__main__":
    example_queries()