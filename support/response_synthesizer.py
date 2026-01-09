# support/response_synthesizer.py
"""
Response Synthesizer
Combines outputs from multiple agents into one coherent response
Formats responses consistently for the user
"""

from typing import List, Dict, Any, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ResponseSynthesizer:
    """
    Takes outputs from multiple agents and combines them into
    a single, well-formatted response for the user.
    """
    
    def __init__(self):
        pass
    
    def synthesize_single(self, agent_name: str, response: str) -> str:
        """
        Format a single agent response
        
        Args:
            agent_name: Name of the agent
            response: Agent's response
            
        Returns:
            Formatted response
        """
        # For now, just return the response as-is
        # Later can add formatting, emoji, structure, etc.
        return response
    
    def synthesize_multiple(self, agent_responses: List[Dict[str, str]]) -> str:
        """
        Combine multiple agent responses into one coherent answer
        
        Args:
            agent_responses: List of dicts with 'agent_name' and 'response' keys
            
        Example:
            [
                {'agent_name': 'Course Info Agent', 'response': '...'},
                {'agent_name': 'Academic Planning Agent', 'response': '...'}
            ]
            
        Returns:
            Combined and formatted response
        """
        if not agent_responses:
            return "I couldn't find information to answer your question."
        
        if len(agent_responses) == 1:
            return self.synthesize_single(
                agent_responses[0]['agent_name'],
                agent_responses[0]['response']
            )
        
        # Combine multiple responses
        combined = []
        
        for i, agent_resp in enumerate(agent_responses, 1):
            agent_name = agent_resp.get('agent_name', 'Agent')
            response = agent_resp.get('response', '')
            
            # Add section separator
            if i > 1:
                combined.append("\n" + "─" * 50 + "\n")
            
            combined.append(response)
        
        # Add helpful closing
        result = "\n".join(combined)
        result += "\n\nIs there anything else you'd like to know?"
        
        return result
    
    def format_tool_results(self, tool_results: List[str]) -> str:
        """
        Format raw tool results into user-friendly response
        
        Args:
            tool_results: List of tool result strings
            
        Returns:
            Formatted response
        """
        if not tool_results:
            return "I couldn't find the information you're looking for."
        
        # Remove tool names from results if present
        cleaned_results = []
        for result in tool_results:
            # If result starts with [tool_name], remove it
            if result.startswith('[') and ']' in result:
                result = result.split(']', 1)[1].strip()
            cleaned_results.append(result)
        
        return "\n\n".join(cleaned_results)
    
    def add_suggestions(self, response: str, suggestions: List[str]) -> str:
        """
        Add helpful suggestions to a response
        
        Args:
            response: Original response
            suggestions: List of suggestions
            
        Returns:
            Response with suggestions appended
        """
        if not suggestions:
            return response
        
        result = response + "\n\n💡 You might also want to:\n"
        for i, suggestion in enumerate(suggestions, 1):
            result += f"{i}. {suggestion}\n"
        
        return result
    
    def format_error(self, error_message: str) -> str:
        """
        Format an error message for user display
        
        Args:
            error_message: Error message
            
        Returns:
            User-friendly error message
        """
        return f"I encountered an issue: {error_message}\n\nPlease try rephrasing your question or contact support if the problem persists."
    
    def format_course_info(self, course: Dict[str, Any]) -> str:
        """
        Format a course dictionary into readable text
        
        Args:
            course: Course document from database
            
        Returns:
            Formatted course information
        """
        lines = []
        
        lines.append(f"📚 {course.get('course_code', '?')}: {course.get('title', '?')}")
        
        if 'credits' in course:
            lines.append(f"Credits: {course.get('credits')}")
        
        if 'prerequisite_human_readable' in course:
            prereqs = course.get('prerequisite_human_readable', 'None')
            lines.append(f"Prerequisites: {prereqs}")
        
        if 'canonical_description' in course:
            desc = course.get('canonical_description', 'No description available')
            lines.append(f"\nDescription: {desc}")
        
        if 'when_offered' in course:
            lines.append(f"When Offered: {course.get('when_offered', 'Not specified')}")
        
        return "\n".join(lines)
    
    def format_course_list(self, courses: List[Dict[str, Any]], title: Optional[str] = None) -> str:
        """
        Format a list of courses
        
        Args:
            courses: List of course documents
            title: Optional title for the list
            
        Returns:
            Formatted course list
        """
        if not courses:
            return "No courses found."
        
        lines = []
        
        if title:
            lines.append(title)
            lines.append("")
        
        for course in courses:
            code = course.get('course_code', '?')
            title = course.get('title', '?')
            credits = course.get('credits', '?')
            lines.append(f"• {code}: {title} ({credits} credits)")
        
        return "\n".join(lines)
    
    def create_comparison_table(self, items: List[Dict[str, Any]], fields: List[str]) -> str:
        """
        Create a simple text-based comparison table
        
        Args:
            items: List of items to compare
            fields: List of field names to include
            
        Returns:
            Formatted comparison table
        """
        if not items:
            return "No items to compare."
        
        # Calculate column widths
        col_widths = {field: len(field) for field in fields}
        for item in items:
            for field in fields:
                value = str(item.get(field, ''))
                col_widths[field] = max(col_widths[field], len(value))
        
        # Build header
        header = " | ".join(field.ljust(col_widths[field]) for field in fields)
        separator = "-" * len(header)
        
        # Build rows
        rows = []
        for item in items:
            row = " | ".join(str(item.get(field, '')).ljust(col_widths[field]) for field in fields)
            rows.append(row)
        
        return "\n".join([header, separator] + rows)


# Singleton instance
_synthesizer_instance = None

def get_synthesizer() -> ResponseSynthesizer:
    """Get singleton instance of ResponseSynthesizer"""
    global _synthesizer_instance
    if _synthesizer_instance is None:
        _synthesizer_instance = ResponseSynthesizer()
    return _synthesizer_instance