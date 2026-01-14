# Neo4j Course Database Import

This directory contains scripts to import and verify course data from `courses_master.json` into Neo4j.

## Scripts

### 1. `import_courses_complete.py`
Complete import script that:
- Clears the existing database
- Creates all course nodes with their properties
- Creates all prerequisite relationships (from AST, lists, and is_prerequisite_for)
- Creates all corequisite relationships
- Creates all equivalency relationships
- Creates program structures (CS and CE)
- Links core courses to programs
- Verifies the import

**Usage:**
```bash
cd auc_neo4j_project
python import_courses_complete.py
```

### 2. `verify_relationships.py`
Verification script that checks if all relationships from `courses_master.json` exist in Neo4j without modifying the database.

**Usage:**
```bash
cd auc_neo4j_project
python verify_relationships.py
```

## What Gets Imported

### Course Properties
- Course code (e.g., "CSCE 1001")
- Course master ID (e.g., "COURSE:CSCE_1001")
- Title
- Description
- Credits
- Level (undergrad/graduate)
- When offered (Fall, Spring, etc.)
- Prerequisite human-readable text
- Department code

### Relationships

1. **REQUIRES** (Prerequisites)
   - Created from `prerequisite_ast` (handles AND/OR logic)
   - Created from `prerequisite_courses` list
   - Created from `is_prerequisite_for` (reverse relationships)

2. **COREQUISITE** (Bidirectional)
   - Created from `relationships.corequisites`
   - Also from AST CONCURRENT operations

3. **EQUIVALENT** (Bidirectional)
   - Created from `relationships.equivalencies`

4. **BELONGS_TO**
   - Links courses to their departments

5. **HAS_REQUIREMENT**
   - Links courses to RequirementGroup nodes (for complex AND/OR prerequisites)

## Database Structure

```
(Department)-[:BELONGS_TO]-(Course)
(Course)-[:REQUIRES]->(Course)
(Course)-[:COREQUISITE]-(Course)
(Course)-[:EQUIVALENT]-(Course)
(Course)-[:HAS_REQUIREMENT]->(RequirementGroup)
(RequirementGroup)-[:REQUIRES|OPTION]->(Course)
(Program)-[:REQUIRES]->(Course)
```

## Notes

- The script automatically converts `COURSE:XXX_YYYY` format to `XXX YYYY` format
- All relationships are verified after import
- The database is cleared before each import (all existing data is deleted)
- Corequisite and equivalency relationships are bidirectional

