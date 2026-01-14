# test_foundation.py
"""
Test script to verify that the foundation files work correctly
Run this after creating the folder structure and files
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        from config import settings
        print("✓ config.settings imported successfully")
    except Exception as e:
        print(f"✗ Failed to import config.settings: {e}")
        return False
    
    try:
        from support.context_manager import ContextManager
        print("✓ ContextManager imported successfully")
    except Exception as e:
        print(f"✗ Failed to import ContextManager: {e}")
        return False
    
    try:
        from support.knowledge_base import KnowledgeBase
        print("✓ KnowledgeBase imported successfully")
    except Exception as e:
        print(f"✗ Failed to import KnowledgeBase: {e}")
        return False
    
    try:
        from support.response_synthesizer import ResponseSynthesizer
        print("✓ ResponseSynthesizer imported successfully")
    except Exception as e:
        print(f"✗ Failed to import ResponseSynthesizer: {e}")
        return False
    
    return True


def test_context_manager():
    """Test ContextManager functionality"""
    print("\n" + "="*50)
    print("Testing ContextManager...")
    print("="*50)
    
    from support.context_manager import ContextManager
    
    ctx = ContextManager()
    
    # Test student info
    ctx.set_major("CS")
    ctx.set_catalog_year(2023)
    ctx.set_completed_courses(["CSCE 1001", "MATH 1501"])
    
    print(f"Major: {ctx.get_major()}")
    print(f"Catalog Year: {ctx.get_catalog_year()}")
    print(f"Completed Courses: {ctx.get_completed_courses()}")
    
    # Test conversation history
    ctx.add_message("user", "What are the prerequisites for CSCE 3312?")
    ctx.add_message("assistant", "The prerequisites are CSCE 2303")
    
    print(f"Conversation history length: {len(ctx.get_conversation_history())}")
    
    # Test context summary
    print("\nContext Summary:")
    print(ctx.get_context_summary())
    
    print("\n✓ ContextManager tests passed")
    return True


def test_knowledge_base():
    """Test KnowledgeBase database connection"""
    print("\n" + "="*50)
    print("Testing KnowledgeBase...")
    print("="*50)
    
    from support.knowledge_base import KnowledgeBase
    
    try:
        kb = KnowledgeBase()
        print("✓ Connected to MongoDB")
        
        # Test getting a course
        course = kb.get_course_by_code("CSCE 1001")
        if course:
            print(f"✓ Found course: {course.get('course_code')} - {course.get('title')}")
        else:
            print("⚠ Could not find CSCE 1001 (this might be okay if course doesn't exist)")
        
        # Test search
        courses = kb.search_by_department("CSCE", limit=3)
        print(f"✓ Found {len(courses)} CSCE courses")
        
        kb.close()
        print("✓ Database connection closed")
        
        print("\n✓ KnowledgeBase tests passed")
        return True
        
    except Exception as e:
        print(f"✗ KnowledgeBase test failed: {e}")
        return False


def test_response_synthesizer():
    """Test ResponseSynthesizer functionality"""
    print("\n" + "="*50)
    print("Testing ResponseSynthesizer...")
    print("="*50)
    
    from support.response_synthesizer import ResponseSynthesizer
    
    synth = ResponseSynthesizer()
    
    # Test single response
    response = synth.synthesize_single(
        "Course Info Agent",
        "CSCE 3312 requires CSCE 2303 as prerequisite"
    )
    print(f"Single response: {response[:50]}...")
    
    # Test multiple responses
    multi_response = synth.synthesize_multiple([
        {"agent_name": "Course Info Agent", "response": "Prerequisites satisfied"},
        {"agent_name": "Academic Planning Agent", "response": "36 courses remaining"}
    ])
    print(f"Multiple response length: {len(multi_response)} characters")
    
    # Test course formatting
    fake_course = {
        "course_code": "CSCE 1001",
        "title": "Introduction to Computer Science",
        "credits": 3,
        "prerequisite_human_readable": "None"
    }
    formatted = synth.format_course_info(fake_course)
    print(f"\nFormatted course:\n{formatted}")
    
    print("\n✓ ResponseSynthesizer tests passed")
    return True


def main():
    """Run all tests"""
    print("="*50)
    print("FOUNDATION FILES TEST SUITE")
    print("="*50)
    
    results = []
    
    # Test imports
    results.append(("Imports", test_imports()))
    
    if results[0][1]:  # Only continue if imports work
        results.append(("ContextManager", test_context_manager()))
        results.append(("KnowledgeBase", test_knowledge_base()))
        results.append(("ResponseSynthesizer", test_response_synthesizer()))
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Foundation is ready.")
        print("\nNext steps:")
        print("1. Create the tools/ folder and move your tool functions")
        print("2. Create the first agent (course_info_agent.py)")
        print("3. Create a simple main.py to test the agent")
    else:
        print("\n⚠ Some tests failed. Fix the issues before proceeding.")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)