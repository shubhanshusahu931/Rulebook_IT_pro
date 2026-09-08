import json
from app import make_answer

with open("test_set.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

passed = 0

for i, question in enumerate(questions, 1):
    result = make_answer(question)

    if result["type"] == "NOT_COVERED":
        status = "PASS"
        passed += 1
    else:
        status = "FAIL"

    print(f"{i:02d}. {status} - {result['type']}")
    print(f"    {question}")

print("\n==============================")
print(f"PASSED: {passed}/{len(questions)}")
print("==============================")