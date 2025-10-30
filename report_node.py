# new_folder/report_node.py
import json


def report_node(state):
    report = {
        "bucket": state["bucket"],
        "total_size": state["size"],
        "object_count": state["count"],
        "storage_classes": state["classes"],
        "lifecycle_rules": state["rules"],
    }
    print(json.dumps(report, indent=2))  # Or save to file/CSV
    return {"report": report, **state}
