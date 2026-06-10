import sys, json
d = json.load(sys.stdin)
jobs = d.get("jobs", [])
for j in jobs:
    print("Job:", j["name"])
    print("Status:", j["status"])
    print("Conclusion:", j.get("conclusion"))
    print("Steps:")
    for s in j.get("steps", []):
        print(f"  {s['name']}: {s.get('status')} -> {s.get('conclusion', '')}")
    print()
