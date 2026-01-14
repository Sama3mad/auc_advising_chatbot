from course_advisor import CourseAdvisor

NEO4J_URI = "neo4j+s://6bd58e7f.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "jeiH1Na0rPA67jYospHTY2IjdLoq4AW23ujVAr_c7GM"

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_courses(courses, show_credits=True):
    if not courses:
        print("  No courses found.")
        return
    
    for course in courses:
        if show_credits and 'credits' in course:
            print(f"  • {course['code']}: {course['title']} ({course['credits']} credits)")
        else:
            print(f"  • {course['code']}: {course['title']}")

def demo_chatbot():
    """Demonstrate chatbot capabilities"""
    advisor = CourseAdvisor(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    
    try:
        # Example 1: Search for a course
        print_header("Example 1: Finding Course Information")
        print("Student asks: 'Tell me about CSCE 2211'")
        
        course = advisor.get_course_info("CSCE 2211")
        if course:
            print(f"\nCourse: {course['code']}")
            print(f"Title: {course['title']}")
            print(f"Credits: {course['credits']}")
            print(f"When Offered: {course['when_offered']}")
            print(f"Prerequisites: {course['prereq_text']}")
            print(f"Description: {course['description'][:200]}...")
        
        # Example 2: Check prerequisites (with complex logic)
        print_header("Example 2: Checking Prerequisites")
        print("Student asks: 'What are the prerequisites for CSCE 3301?'")
        
        print("\nDetailed explanation:")
        print(advisor.explain_prerequisites("CSCE 3301"))
        
        # Example 3: Check if student can take a course
        print_header("Example 3: Can I Take This Course?")
        print("Student asks: 'I completed CSCE 1001 and MACT 1111. Can I take CSCE 1101?'")
        
        completed = ["CSCE 1001", "MACT 1111"]
        can_take, missing, details = advisor.can_take_course("CSCE 1101", completed)
        
        print(f"\nCompleted courses: {', '.join(completed)}")
        if can_take:
            print("✓ Yes! You can take CSCE 1101")
            
            # Show corequisites if any
            coreqs = advisor.get_corequisites("CSCE 1101")
            if coreqs:
                print("\nNote: This course has corequisites (must take together):")
                print_courses(coreqs)
        else:
            print("✗ No, you still need to complete:")
            if details['direct_missing']:
                for prereq in details['direct_missing']:
                    print(f"  • {prereq['code']}: {prereq['title']}")
            for group in details['group_status']:
                if not group['satisfied']:
                    print(f"  • {group['description']}")
        
        # Example 4: What courses are available now?
        print_header("Example 4: What Courses Can I Take?")
        print("Student asks: 'I completed CSCE 1001, CSCE 1101, CSCE 1102. What can I take next?'")
        
        completed = ["CSCE 1001", "CSCE 1101", "CSCE 1102"]
        available = advisor.get_courses_available(completed)
        
        print(f"\nBased on your completed courses: {', '.join(completed)}")
        print(f"\nYou can take {len(available)} courses:")
        print_courses(available[:10], show_credits=True)
        if len(available) > 10:
            print(f"  ... and {len(available) - 10} more")
        
        # Example 5: Program requirements
        print_header("Example 5: CS Program Requirements")
        print("Student asks: 'What are the core requirements for Computer Science?'")
        
        requirements = advisor.get_program_requirements("CS")
        print("\nComputer Science Core Courses:")
        if requirements['core']:
            print_courses(requirements['core'][:15])
            if len(requirements['core']) > 15:
                print(f"  ... and {len(requirements['core']) - 15} more")
        
        # Example 6: Course recommendations
        print_header("Example 6: Recommended Next Courses")
        print("Student asks: 'I'm a CS student. What should I take next semester?'")
        
        completed = [
            "CSCE 1001", "CSCE 1101", "CSCE 1102", "MACT 1121", 
            "MACT 1122", "PHYS 1011", "PHYS 1012"
        ]
        
        recommendations, total_credits = advisor.recommend_next_courses(
            "CS", completed, max_credits=15
        )
        
        print(f"\nBased on your progress, I recommend these courses (total: {total_credits} credits):")
        if recommendations:
            print_courses(recommendations, show_credits=True)
        else:
            print("  Complete more prerequisites to unlock new courses!")
        
        # Example 7: Search courses by name
        print_header("Example 7: Search Courses")
        print("Student asks: 'What courses are available about machine learning?'")
        
        results = advisor.find_courses_by_name("machine learning")
        print("\nFound these courses:")
        print_courses(results, show_credits=True)
        
        # Example 8: What unlocks after taking a course?
        print_header("Example 8: Course Unlocks")
        print("Student asks: 'If I take CSCE 1101, what courses will that unlock?'")
        
        deps = advisor.get_course_dependencies("CSCE 1101")
        print(f"\nTaking CSCE 1101 will unlock {len(deps)} courses:")
        print_courses(deps[:10], show_credits=True)
        if len(deps) > 10:
            print(f"  ... and {len(deps) - 10} more")
        
        # Example 9: Department courses
        print_header("Example 9: All CSCE Courses")
        print("Student asks: 'Show me all Computer Science courses'")
        
        csce_courses = advisor.get_courses_by_department("CSCE")
        print(f"\nFound {len(csce_courses)} CSCE courses:")
        print_courses(csce_courses[:10], show_credits=True)
        if len(csce_courses) > 10:
            print(f"  ... and {len(csce_courses) - 10} more")
        
        # Example 10: Complex prerequisite checking
        print_header("Example 10: Complex Prerequisite Example")
        print("Student asks: 'Can I take CSCE 2202 if I have MACT 2131 and CSCE 2211?'")
        
        completed = ["MACT 2131", "CSCE 2211", "CSCE 1101"]
        can_take, missing, details = advisor.can_take_course("CSCE 2202", completed)
        
        print(f"\nCompleted: {', '.join(completed)}")
        print(f"Can take CSCE 2202? {can_take}")
        
        if not can_take:
            print("\nMissing requirements:")
            for group in details['group_status']:
                if not group['satisfied']:
                    print(f"  • {group['description']}")
        
    finally:
        advisor.close()

def interactive_chatbot():
    """Simple interactive chatbot with complex prerequisite support"""
    advisor = CourseAdvisor(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    
    print("\n" + "="*60)
    print("  AUC Course Advisor Chatbot")
    print("  Type 'help' for commands, 'quit' to exit")
    print("="*60 + "\n")
    
    try:
        while True:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("Goodbye! Good luck with your studies!")
                break
            
            if user_input.lower() == 'help':
                print("\nAvailable commands:")
                print("  info <course code>       - Get course information")
                print("  prereq <course code>     - Get prerequisites (with AND/OR logic)")
                print("  explain <course code>    - Get detailed prerequisite explanation")
                print("  coreq <course code>      - Get corequisites")
                print("  search <term>            - Search courses")
                print("  unlock <course code>     - See what courses this unlocks")
                print("  dept <dept code>         - List courses in department")
                print("  can <course> [courses]   - Check if you can take a course")
                print("  quit                     - Exit")
                print()
                continue
            
            # Simple command parsing
            parts = user_input.split(maxsplit=1)
            command = parts[0].lower()
            
            if command == 'info' and len(parts) > 1:
                course_code = parts[1].upper()
                course = advisor.get_course_info(course_code)
                if course:
                    print(f"\n{course['code']}: {course['title']}")
                    print(f"Credits: {course['credits']}")
                    print(f"When Offered: {course['when_offered']}")
                    print(f"Prerequisites: {course['prereq_text']}")
                    print(f"\nDescription: {course['description']}")
                else:
                    print(f"\nCourse {course_code} not found.")
            
            elif command == 'prereq' and len(parts) > 1:
                course_code = parts[1].upper()
                prereqs = advisor.get_prerequisites_simple(course_code)
                if prereqs:
                    print(f"\nAll prerequisite courses for {course_code}:")
                    print_courses(prereqs)
                else:
                    print(f"\n{course_code} has no prerequisites.")
            
            elif command == 'explain' and len(parts) > 1:
                course_code = parts[1].upper()
                explanation = advisor.explain_prerequisites(course_code)
                print(f"\nPrerequisites for {course_code}:")
                print(explanation)
            
            elif command == 'coreq' and len(parts) > 1:
                course_code = parts[1].upper()
                coreqs = advisor.get_corequisites(course_code)
                if coreqs:
                    print(f"\nCorequisites for {course_code} (must take together):")
                    print_courses(coreqs)
                else:
                    print(f"\n{course_code} has no corequisites.")
            
            elif command == 'unlock' and len(parts) > 1:
                course_code = parts[1].upper()
                deps = advisor.get_course_dependencies(course_code)
                if deps:
                    print(f"\nTaking {course_code} will unlock:")
                    print_courses(deps)
                else:
                    print(f"\n{course_code} doesn't unlock any courses.")
            
            elif command == 'search' and len(parts) > 1:
                search_term = parts[1]
                results = advisor.find_courses_by_name(search_term)
                if results:
                    print(f"\nFound {len(results)} courses:")
                    print_courses(results[:10])
                    if len(results) > 10:
                        print(f"  ... and {len(results) - 10} more")
                else:
                    print(f"\nNo courses found matching '{search_term}'")
            
            elif command == 'dept' and len(parts) > 1:
                dept_code = parts[1].upper()
                courses = advisor.get_courses_by_department(dept_code)
                if courses:
                    print(f"\n{dept_code} courses ({len(courses)} total):")
                    print_courses(courses[:15])
                    if len(courses) > 15:
                        print(f"  ... and {len(courses) - 15} more")
                else:
                    print(f"\nNo courses found for department {dept_code}")
            
            elif command == 'can' and len(parts) > 1:
                # Format: can CSCE2211 CSCE1001 CSCE1101
                args = parts[1].split()
                if len(args) >= 1:
                    course_code = args[0].upper()
                    completed = [c.upper() for c in args[1:]] if len(args) > 1 else []
                    
                    can_take, missing, details = advisor.can_take_course(course_code, completed)
                    
                    if completed:
                        print(f"\nCompleted: {', '.join(completed)}")
                    
                    if can_take:
                        print(f"✓ Yes, you can take {course_code}!")
                    else:
                        print(f"✗ No, you're missing:")
                        if details['direct_missing']:
                            print("\n  Direct prerequisites:")
                            for prereq in details['direct_missing']:
                                print(f"    • {prereq['code']}: {prereq['title']}")
                        
                        for group in details['group_status']:
                            if not group['satisfied']:
                                print(f"\n  • {group['description']}")
                else:
                    print("\nUsage: can <course> [completed courses...]")
            
            else:
                print("\nI didn't understand that. Type 'help' for available commands.")
            
            print()
    
    finally:
        advisor.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'interactive':
        interactive_chatbot()
    else:
        demo_chatbot()