"""
MongoDB Core Rules Sync Script
This script syncs all core rules from data/policies/core_rules.json to MongoDB.
It will add new rules and update existing ones (by _id) in the 'rules' collection.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any

from pymongo import MongoClient

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import MONGODB_URI, DATABASE_NAME, RULES_COLLECTION  # type: ignore


class CoreRulesMongoDBSyncer:
    """Syncs core rules from core_rules.json to MongoDB"""

    def __init__(self) -> None:
        """Initialize MongoDB connection"""
        print("Connecting to MongoDB...")
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DATABASE_NAME]
        self.rules_collection = self.db[RULES_COLLECTION]
        print("[OK] Connected to MongoDB")

    def close(self) -> None:
        """Close MongoDB connection"""
        self.client.close()

    def prepare_rule_document(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare a rule document for MongoDB insertion.

        Ensures required fields exist and normalizes structure.
        """
        doc = rule.copy()

        # Ensure minimal fields
        doc.setdefault("section", "")
        doc.setdefault("rules", [])
        doc.setdefault("applies_to", [])
        doc.setdefault("tags", [])

        return doc

    def sync_rules(self, rules_file: Path) -> Dict[str, int]:
        """
        Sync all rules from JSON file to MongoDB.

        Args:
            rules_file: Path to core_rules.json

        Returns:
            Dictionary with statistics (added, updated, skipped, errors)
        """
        print(f"\nLoading rules from {rules_file}...")
        with open(rules_file, "r", encoding="utf-8") as f:
            rules_data = json.load(f)

        if not isinstance(rules_data, list):
            raise ValueError("core_rules.json must contain a top-level list of rule objects")

        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

        print(f"Found {len(rules_data)} rules\n")
        print("Syncing rules to MongoDB...")

        for rule in rules_data:
            try:
                doc = self.prepare_rule_document(rule)
                rule_id = doc.get("_id")

                if not rule_id:
                    print("  [WARNING] Skipping rule without _id")
                    stats["skipped"] += 1
                    continue

                existing = self.rules_collection.find_one({"_id": rule_id})

                if existing:
                    result = self.rules_collection.update_one({"_id": rule_id}, {"$set": doc})
                    if result.modified_count > 0:
                        stats["updated"] += 1
                        print(f"  [UPDATED] {rule_id} - {doc.get('section', '')}")
                    else:
                        stats["skipped"] += 1
                        print(f"  [NO CHANGE] {rule_id} - {doc.get('section', '')}")
                else:
                    self.rules_collection.insert_one(doc)
                    stats["added"] += 1
                    print(f"  [ADDED] {rule_id} - {doc.get('section', '')}")
            except Exception as e:  # pragma: no cover - defensive
                stats["errors"] += 1
                print(f"  [ERROR] Failed to sync rule {_safe_get(rule, '_id')}: {e}")

        return stats

    def verify_sync(self, rules_file: Path) -> Dict[str, Any]:
        """
        Verify that all rules from JSON are in MongoDB.
        """
        print("\n" + "=" * 60)
        print("VERIFYING CORE RULES SYNC")
        print("=" * 60)

        with open(rules_file, "r", encoding="utf-8") as f:
            rules_data = json.load(f)

        missing_rules = []
        total_in_json = 0

        for rule in rules_data:
            total_in_json += 1
            rule_id = rule.get("_id")
            if not rule_id:
                continue

            existing = self.rules_collection.find_one({"_id": rule_id})
            if not existing:
                missing_rules.append(rule_id)

        total_in_mongo = self.rules_collection.count_documents({})

        print(f"\nTotal rules in JSON: {total_in_json}")
        print(f"Total rules in MongoDB: {total_in_mongo}")
        print(f"Missing rules: {len(missing_rules)}")

        if missing_rules:
            print("\nMissing rule IDs:")
            for rid in missing_rules:
                print(f"  - {rid}")
        else:
            print("\n[SUCCESS] All rules are in MongoDB!")

        return {
            "total_in_json": total_in_json,
            "total_in_mongo": total_in_mongo,
            "missing_count": len(missing_rules),
            "missing_rules": missing_rules,
        }


def _safe_get(d: Dict[str, Any], key: str) -> Any:
    """Helper for safe dict access in error paths."""
    try:
        return d.get(key)
    except Exception:
        return None


def main() -> None:
    """Main entry point for syncing core rules."""
    script_dir = Path(__file__).parent
    rules_file = script_dir.parent / "data" / "policies" / "core_rules.json"

    if not rules_file.exists():
        print(f"[ERROR] Could not find core_rules.json at {rules_file}")
        return

    syncer = CoreRulesMongoDBSyncer()

    try:
        print("\n" + "=" * 60)
        print("MONGODB CORE RULES SYNC")
        print("=" * 60)

        stats = syncer.sync_rules(rules_file)

        print("\n" + "=" * 60)
        print("SYNC RESULTS")
        print("=" * 60)
        print(f"Added: {stats['added']}")
        print(f"Updated: {stats['updated']}")
        print(f"Skipped (no changes): {stats['skipped']}")
        print(f"Errors: {stats['errors']}")
        print("=" * 60)

        syncer.verify_sync(rules_file)

    except Exception as e:  # pragma: no cover - defensive
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()
    finally:
        syncer.close()


if __name__ == "__main__":
    main()


