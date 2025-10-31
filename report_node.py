import json


def report_node(state):
    report = {
        "bucket": state["bucket"],
        "total_size": state["size"],
        "object_count": state["count"],
        "storage_classes": state["classes"],
        "lifecycle_rules": state["rules"],
    }
    print(json.dumps(report, indent=2))  
    return {"report": report, **state}
