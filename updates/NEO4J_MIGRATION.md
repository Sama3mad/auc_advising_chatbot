# Neo4j Migration for Course Relationships

## Overview
This document describes the migration from MongoDB to Neo4j for course relationship queries (prerequisites, corequisites, equivalencies).

## Changes Made

### 1. Configuration (`config/settings.py`)
- Added Neo4j connection credentials:
  - `NEO4J_URI`
  - `NEO4J_USERNAME`
  - `NEO4J_PASSWORD`

### 2. Knowledge Base (`support/knowledge_base.py`)

#### Added Neo4j Connection
- Added `neo4j_driver` to the `KnowledgeBase` class
- Both MongoDB and Neo4j connections are maintained:
  - MongoDB: Used for course data retrieval (course details, descriptions, etc.)
  - Neo4j: Used for relationship queries (prerequisites, corequisites, equivalencies)

#### Replaced Functions (Now Using Neo4j)

1. **`get_prerequisite_courses(course_code)`**
   - **Old**: Queried MongoDB `prerequisite_courses` field
   - **New**: Queries Neo4j `REQUIRES` relationships and `RequirementGroup` nodes
   - Returns list of prerequisite course master IDs

2. **`get_corequisites(course_code)`**
   - **Old**: Queried MongoDB `relationships.corequisites` field
   - **New**: Queries Neo4j `COREQUISITE` relationships (bidirectional)
   - Returns list of corequisite course master IDs

3. **`get_equivalencies(course_code)`**
   - **Old**: Queried MongoDB `relationships.equivalencies` field
   - **New**: Queries Neo4j `EQUIVALENT` relationships (bidirectional)
   - Returns list of equivalent course master IDs

4. **`find_courses_requiring(course_master_id)`**
   - **Old**: Queried MongoDB `relationships.is_prerequisite_for` field
   - **New**: Queries Neo4j reverse `REQUIRES` relationships
   - Returns list of courses that require the given course as a prerequisite

#### Functions Still Using MongoDB

- **`get_prerequisite_ast(course_code)`**: Still uses MongoDB because the AST structure is not stored in Neo4j
- All other course retrieval functions (get_course_by_code, search functions, etc.) still use MongoDB

#### Commented Out Functions
All old MongoDB-based relationship functions have been commented out (not deleted) for easy rollback if needed. They are marked with:
```python
# ============ COMMENTED OUT: MONGODB-BASED RELATIONSHIP METHODS ============
```

## Benefits

1. **Better Performance**: Neo4j is optimized for graph queries and relationship traversal
2. **More Accurate**: Relationships are explicitly modeled as graph edges
3. **Easier Queries**: Complex relationship queries (like finding prerequisite chains) are simpler in Neo4j
4. **Scalability**: Graph database is better suited for relationship-heavy queries

## Rollback

If you need to revert to MongoDB-based implementations:
1. Uncomment the MongoDB-based functions in `support/knowledge_base.py`
2. Comment out the Neo4j-based implementations
3. Remove the Neo4j connection initialization

## Testing

The following tools automatically use the new Neo4j implementations:
- `tools/course_tools.py`: Uses `get_corequisites()`, `get_equivalencies()`, `find_courses_requiring()`
- `tools/prerequisite_tools.py`: Uses `get_prerequisite_courses()` and `get_prerequisite_ast()`

All existing code should work without modification since the function signatures remain the same.

