# main.py
"""
AUC Advising Chatbot - Main Entry Point
Simple version with Course Info Agent only (for testing)
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from support.context_manager import ContextManager
from support.knowledge_base import KnowledgeBase
from agents.course_info_agent import CourseInfoAgent


def print_welcome():
    """Print welcome message"""
    print("=" * 60)
    print("AUC ADVISING CHATBOT - Course Info Agent (Test Version)")
    print("=" * 60)
    print("\nFeatures:")
    print("✓ Course details and information")
    print("✓ Prerequisites checking (understands AND/OR logic)")
    print("✓ Course search by department or keyword")
    print("✓ Prerequisite chain analysis")
    print("\nCommands:")
    print("• 'quit' or 'exit' - Exit the chatbot")
    print("• 'clear' - Clear conversation history")
    print("• 'info' - Set your student information")
    print("• 'context' - View current context")
    print("\nType 'quit', 'exit', or 'bye' to end.")
    print("=" * 60)
    print()


def handle_special_commands(user_input: str, context_manager: ContextManager) -> bool:
    """
    Handle special commands like 'clear', 'info', 'context'
    
    Args:
        user_input: User's input
        context_manager: Context manager instance
        
    Returns:
        True if command was handled, False otherwise
    """
    user_input_lower = user_input.lower().strip()
    
    if user_input_lower == "clear":
        context_manager.clear()
        print("\n✓ Conversation history cleared.\n")
        return True
    
    elif user_input_lower == "context":
        print("\n" + "="*50)
        print("CURRENT CONTEXT")
        print("="*50)
        summary = context_manager.get_context_summary()
        print(summary)
        print("="*50)
        print()
        return True
    
    elif user_input_lower == "info":
        print("\n" + "="*50)
        print("SET STUDENT INFORMATION")
        print("="*50)
        
        major = input("Major (e.g., CS, CE) [press Enter to skip]: ").strip()
        if major:
            context_manager.set_major(major)
        
        catalog_year = input("Catalog Year (e.g., 2023) [press Enter to skip]: ").strip()
        if catalog_year:
            try:
                context_manager.set_catalog_year(int(catalog_year))
            except ValueError:
                print("Invalid year, skipping...")
        
        completed = input("Completed Courses (comma-separated, e.g., CSCE 1001, MATH 1501) [press Enter to skip]: ").strip()
        if completed:
            courses = [c.strip() for c in completed.split(",")]
            context_manager.set_completed_courses(courses)
        
        print("\n✓ Student information updated.")
        print("\nCurrent context:")
        print(context_manager.get_context_summary())
        print("="*50)
        print()
        return True
    
    return False


def main():
    """Main chatbot loop"""
    print_welcome()
    
    # Initialize components
    print("Initializing...")
    context_manager = ContextManager()
    knowledge_base = KnowledgeBase()
    course_agent = CourseInfoAgent(context_manager, knowledge_base)
    print("✓ Ready!\n")
    
    # Main conversation loop
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            # Skip empty input
            if not user_input:
                continue
            
            # Check for exit commands
            if user_input.lower() in ["quit", "exit", "bye"]:
                print("\nGoodbye! Have a great day!")
                break
            
            # Check for special commands
            if handle_special_commands(user_input, context_manager):
                continue
            
            # Add to conversation history
            context_manager.add_message("user", user_input)
            
            # Process with agent
            print("\nAdvisor: ", end="", flush=True)
            response = course_agent.process(user_input)
            print(response)
            print()
            
            # Add response to history
            context_manager.add_message("assistant", response)
            
        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Goodbye!")
            break
        except Exception as e:
            print(f"\n✗ Error: {e}")
            print("Please try again or type 'quit' to exit.\n")
    
    # Cleanup
    knowledge_base.close()
    print("\nThank you for using AUC Advising Chatbot!")


if __name__ == "__main__":
    main()