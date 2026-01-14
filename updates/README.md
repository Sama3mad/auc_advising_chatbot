# Updates Folder

This folder contains scripts for updating and syncing data to MongoDB.

## Scripts

### `sync_courses_to_mongodb.py`

This script syncs all courses from `courses_master.json` to MongoDB.

**Features:**
- Adds new courses to MongoDB
- Updates existing courses if they've changed
- Adds department_code and department_name to each course
- Verifies that all courses from JSON are in MongoDB
- Shows statistics before and after sync

**Usage:**
```bash
python updates/sync_courses_to_mongodb.py
```

**What it does:**
1. Connects to MongoDB using credentials from `config/settings.py`
2. Reads all courses from `data/course/courses_master.json`
3. For each course:
   - Adds `department_code` and `department_name` fields
   - Uses upsert (update if exists, insert if new) based on `course_master_id`
4. Verifies that all courses are successfully synced
5. Shows statistics about the sync operation

**Output:**
- Shows which courses were added, updated, or skipped
- Displays statistics by department
- Verifies that all courses are in MongoDB

**Note:** The script uses `course_master_id` as the unique identifier. If a course with the same `course_master_id` already exists, it will be updated. Otherwise, it will be inserted as a new document.

