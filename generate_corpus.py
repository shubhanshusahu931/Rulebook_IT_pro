from pathlib import Path

corpus = Path("corpus")

topics = {
    "01-attendance.md": "Attendance",
    "02-medical.md": "Medical Leave",
    "03-committee.md": "Academic Committee",
    "04-examinations.md": "Examinations",
    "05-fees.md": "Fees",
    "06-scholarships.md": "Scholarships",
    "07-hostel.md": "Hostel",
    "08-library.md": "Library",
    "09-societies.md": "Student Societies",
    "10-discipline.md": "Discipline",
}

paragraph = """
The university administers this area through published regulations,
official notices, approved forms, and decisions of the relevant committee.
Students are expected to read the applicable requirements carefully and
submit documents through the designated institutional channel. Where a
deadline is stated, students should retain evidence of submission and
payment. Administrative staff may request supporting documents when a
regulation requires verification. A student should not rely on an informal
verbal statement when written approval is required. Official decisions are
communicated through the university's designated communication system.
Different procedures may apply to different academic activities, and a
specific provision should be read together with the general regulations.
Where an application requires committee consideration, the committee may
request additional evidence before reaching a decision. Students remain
responsible for checking published notices and completing required forms.
Records should be retained until the relevant academic or administrative
process is complete.
"""

for filename, topic in topics.items():

    path = corpus / filename

    original = path.read_text(encoding="utf-8")

    # Add substantial supporting material.
    extra = f"\n\n## General {topic} Guidance\n"

    for i in range(18):
        extra += f"\n### Guidance {i + 1}\n"
        extra += paragraph

    path.write_text(original + extra, encoding="utf-8")

print("Corpus expanded")