import sys, json
d = json.load(sys.stdin)
jobs = d.get("jobs", [])
for j in jobs:
    print("Job:", j["name"])
    print("Status:", j["status"])
    print("Conclusion:", j.get("conclusion"))
    for s in j.get("steps", []):
        print("  {}: {}".format(s["name"], s.get("conclusion", "")))
