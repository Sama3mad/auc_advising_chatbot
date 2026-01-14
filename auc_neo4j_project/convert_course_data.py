import json

def convert_course_data(input_file='course_data.json', output_file='courses_simplified.json'):
    """
    Convert the complex course structure to a simplified format
    Note: This is optional - the complex importer reads course_data.json directly
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    courses = []
    
    # Process each department
    for dept_code, dept_info in data['departments'].items():
        dept_name = dept_info['department_name']
        
        # Process each course in the department
        for course in dept_info['courses']:
            # Handle credits (can be string like "1-3" or int)
            credits = course.get('credits', 3)
            if isinstance(credits, str):
                credits = int(credits.split('-')[0])
            
            # Extract prerequisite courses (simplified list)
            prereqs = course.get('prerequisite_courses', [])
            prereq_codes = []
            
            # Convert COURSE:DEPT_CODE format to DEPT CODE format
            for prereq in prereqs:
                if prereq.startswith('COURSE:'):
                    code = prereq.replace('COURSE:', '').replace('_', ' ')
                    prereq_codes.append(code)
            
            # Extract corequisites
            coreqs = course.get('relationships', {}).get('corequisites', [])
            coreq_codes = []
            for coreq in coreqs:
                if coreq.startswith('COURSE:'):
                    code = coreq.replace('COURSE:', '').replace('_', ' ')
                    coreq_codes.append(code)
            
            # Extract courses this is a prerequisite for
            prereq_for = course.get('relationships', {}).get('is_prerequisite_for', [])
            prereq_for_codes = []
            for course_id in prereq_for:
                if course_id.startswith('COURSE:'):
                    code = course_id.replace('COURSE:', '').replace('_', ' ')
                    prereq_for_codes.append(code)
            
            # Create simplified course object
            simplified_course = {
                'code': course['course_code'],
                'title': course['title'],
                'description': course['canonical_description'],
                'credits': credits,
                'level': course.get('level', 'undergrad'),
                'department': dept_name,
                'department_code': dept_code,
                'when_offered': course.get('when_offered', ''),
                'prerequisites': prereq_codes,
                'prerequisite_human': course.get('prerequisite_human_readable', ''),
                'prerequisite_ast': course.get('prerequisite_ast'),  # Keep AST for complex logic
                'corequisites': coreq_codes,
                'is_prerequisite_for': prereq_for_codes,
                'metadata': course.get('metadata', {})
            }
            
            courses.append(simplified_course)
    
    # Save simplified data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Converted {len(courses)} courses")
    print(f"✓ Saved to {output_file}")
    
    # Show statistics
    courses_with_prereqs = sum(1 for c in courses if c['prerequisites'])
    courses_with_ast = sum(1 for c in courses if c['prerequisite_ast'])
    courses_with_coreqs = sum(1 for c in courses if c['corequisites'])
    
    print(f"\nStatistics:")
    print(f"  Courses with prerequisites: {courses_with_prereqs}")
    print(f"  Courses with complex logic (AST): {courses_with_ast}")
    print(f"  Courses with corequisites: {courses_with_coreqs}")
    
    return courses

def analyze_prerequisite_complexity(course_data):
    """Analyze how complex the prerequisite structures are"""
    print("\n" + "="*60)
    print("PREREQUISITE COMPLEXITY ANALYSIS")
    print("="*60 + "\n")
    
    complexity_stats = {
        'simple': 0,       # Direct prerequisite only
        'and': 0,          # Uses AND logic
        'or': 0,           # Uses OR logic
        'concurrent': 0,   # Has concurrent requirements
        'standing': 0,     # Requires standing
        'approval': 0,     # Requires approval
        'mixed': 0         # Complex combinations
    }
    
    complex_examples = []
    
    for course in course_data:
        ast = course.get('prerequisite_ast')
        if not ast:
            continue
        
        op = ast.get('op')
        
        if op == 'COURSE':
            complexity_stats['simple'] += 1
        elif op == 'AND':
            complexity_stats['and'] += 1
            if course['code'] not in [c[0] for c in complex_examples[:5]]:
                complex_examples.append((course['code'], course['prerequisite_human']))
        elif op == 'OR':
            complexity_stats['or'] += 1
        elif op == 'CONCURRENT':
            complexity_stats['concurrent'] += 1
        elif op == 'STANDING':
            complexity_stats['standing'] += 1
        elif op == 'APPROVAL':
            complexity_stats['approval'] += 1
    
    print("Prerequisite types:")
    for ptype, count in complexity_stats.items():
        if count > 0:
            print(f"  {ptype.capitalize()}: {count} courses")
    
    if complex_examples:
        print(f"\nExample complex prerequisites:")
        for code, human in complex_examples[:5]:
            print(f"  {code}: {human}")

if __name__ == "__main__":
    # Convert the data
    courses = convert_course_data()
    
    # Analyze complexity
    analyze_prerequisite_complexity(courses)
    
    # Print sample
    print("\n" + "="*60)
    print("SAMPLE COURSE")
    print("="*60)
    print(json.dumps(courses[0], indent=2))