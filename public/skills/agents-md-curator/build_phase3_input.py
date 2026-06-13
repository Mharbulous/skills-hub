import json

phase5 = json.load(open('phase5_depth.json'))
by_file = phase5['by_file']

# competitive_placement.py expects: {"managed_files": [...], "by_file": {...}}
# Get the single managed file path from phase 0 output
path = list(by_file.keys())[0]

managed_files_input = {
    "managed_files": [
        {
            "path": path,
            "repo": None,
            "depth": -1,
            "manual_units": 41,
            "managed_budget": 159
        }
    ],
    "by_file": by_file
}

with open('phase3_input.json', 'w') as f:
    json.dump(managed_files_input, f, indent=2)

print("Written phase3_input.json")
print("by_file keys:", list(by_file.keys()))
print("line_ids:", by_file[path])
