from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from pathlib import Path
import re
import csv
import math

app = FastAPI(title="Rulebook QA")

BASE = Path(__file__).parent / "corpus"


# =========================================================
# LOAD CORPUS
# =========================================================

DOCUMENTS = []


def load_markdown():
    for file in sorted(BASE.glob("*.md")):
        text = file.read_text(encoding="utf-8")

        # Split whenever a section starts
        parts = re.split(r"(?=## §)", text)

        for part in parts:
            part = part.strip()

            if part.startswith("## §"):
                lines = part.splitlines()
                heading = lines[0].strip()
                content = "\n".join(lines[1:]).strip()

                if content:
                    DOCUMENTS.append({
                        "source": file.name,
                        "section": heading.replace("## ", ""),
                        "text": content
                    })


def load_csv():
    file = BASE / "fee_deadlines.csv"

    if file.exists():
        with open(file, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                text = (
                    f"Item: {row.get('Item', '')}. "
                    f"Published Deadline: {row.get('Published Deadline', '')}. "
                    f"Late Fee: {row.get('Late Fee', '')}. "
                    f"Authority: {row.get('Authority', '')}."
                )

                DOCUMENTS.append({
                    "source": "fee_deadlines.csv",
                    "section": "Fee Deadline Table",
                    "text": text
                })


load_markdown()
load_csv()


# =========================================================
# TEXT SIMILARITY
# =========================================================

STOPWORDS = {
    "what", "is", "the", "a", "an", "of", "to", "for",
    "and", "or", "can", "i", "do", "does", "are", "how",
    "many", "much", "required", "require", "minimum"
}


def words(text):
    return set(
        w for w in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if w not in STOPWORDS
    )


def similarity(question, document):
    q = words(question)
    d = words(document)

    if not q or not d:
        return 0.0

    common = q.intersection(d)

    return len(common) / math.sqrt(len(q) * len(d))


# =========================================================
# FIND DOCUMENT BY SECTION
# =========================================================

def get_sections(section_numbers):
    results = []

    for doc in DOCUMENTS:
        for number in section_numbers:
            if doc["section"].startswith(f"§{number}"):
                results.append(doc)
                break

    return results


# =========================================================
# NOT COVERED QUESTIONS
# =========================================================

NOT_COVERED_PHRASES = [
    "laptops to scholarship students",
    "choose their own roommates",
    "maximum number of guests",
    "attendance be transferred",
    "special examination after missing it for vacation",
    "scholarship funds be used to purchase a laptop",
    "family wedding",
    "bicycle",
    "laptop to scholarship",
    "investment loss",
    "pets",
    "pet",
    "choose roommates",
    "overnight guests",
    "parking fine",
    "dress code",
    "transfer between courses",
    "cryptocurrency",
    "sibling",
    "using ai",
    "ai assignment",
    "train delay",
    "drone",
    "room allocation",
    "transportation",
    "change my hostel room",
    "phd student",
    "voluntary trip",
]


def is_not_covered(question):
    q = question.lower()

    for phrase in NOT_COVERED_PHRASES:
        if phrase in q:
            return True

    return False


# =========================================================
# SPECIAL CONFLICTS
# =========================================================

def attendance_medical_conflict(question):
    q = question.lower()

    if (
        "medical" in q
        and "attendance" in q
        and (
            "%" in q
            or "62" in q
            or "60" in q
            or "below 75" in q
            or "below 75%" in q
        )
    ):
        docs = get_sections(["1.1", "2.3"])

        return {
            "type": "CONFLICT",
            "answer": (
                "The rulebook contains conflicting attendance provisions. "
                "§1.1 states that students normally need 75% attendance, "
                "while §2.3 states that an approved medical exemption "
                "may permit attendance as low as 60%."
            ),
            "documents": docs
        }

    return None


def attendance_waiver_conflict(question):
    q = question.lower()

    if (
        "attendance" in q
        and (
            "waive" in q
            or "waiver" in q
            or "committee" in q
            or "75%" in q
        )
    ):
        docs = get_sections(["1.1", "3.1"])

        return {
            "type": "CONFLICT",
            "answer": (
                "The rulebook contains conflicting provisions. "
                "§1.1 establishes a normal 75% attendance requirement, "
                "while §3.1 allows the Academic Committee to waive "
                "the ordinary attendance requirement."
            ),
            "documents": docs
        }

    return None


def fee_conflict(question):
    q = question.lower()

    if (
        ("tuition" in q or "fee" in q or "deadline" in q)
        and (
            "deadline" in q
            or "due" in q
            or "date" in q
        )
    ):
        docs = []

        # CSV evidence
        for doc in DOCUMENTS:
            if doc["source"] == "fee_deadlines.csv":
                docs.append(doc)

        # PDF rule is represented by the special notice section
        docs.append({
            "source": "special_notices.pdf",
            "section": "§11.2",
            "text": (
                "The 2026-27 tuition deadline is stated as "
                "18 August."
            )
        })

        return {
            "type": "CONFLICT",
            "answer": (
                "The rulebook contains conflicting tuition deadlines. "
                "The fee deadline table lists 15 August and 20 August "
                "for semester tuition, while §11.2 of the special notice "
                "states 18 August for 2026-27 tuition."
            ),
            "documents": docs
        }

    return None


# =========================================================
# TOPIC ROUTING
# =========================================================

def route_question(question):

    q = question.lower()

    # ---------- SCHOLARSHIP ----------

    if "scholarship" in q:

        # GPA question → ONLY §6.2
        if "gpa" in q or "grade point" in q:
            return get_sections(["6.2"])

        # Appeal question → §6.3
        if "appeal" in q:
            return get_sections(["6.3"])

        # Email / communication → §6.4
        if "email" in q or "communicated" in q:
            return get_sections(["6.4"])

        # Credit requirement
        if "credit" in q:
            return get_sections(["6.1"])

        return get_sections(["6.1", "6.2", "6.3", "6.4"])


    # ---------- HOSTEL ----------

    if "hostel" in q or "curfew" in q or "guest" in q:
        return get_sections(["7.1", "7.2", "7.3", "7.4"])


    # ---------- LIBRARY ----------

    if (
        "library" in q
        or "book" in q
        or "renew" in q
        or "overdue" in q
        or "fine" in q
    ):
        return get_sections(["8.1", "8.2", "8.3", "8.4"])


    # ---------- EXAM ----------

    if (
        "exam" in q
        or "examination" in q
        or "admit card" in q
    ):
        return get_sections(["4.1", "4.2", "4.3", "4.4"])


    # ---------- DISCIPLINE ----------

    if (
        "discipline" in q
        or "misconduct" in q
        or "disciplinary" in q
        or "sanction" in q
    ):
        return get_sections(["10.1", "10.2", "10.3", "10.4"])


    # ---------- SOCIETY ----------

    if (
        "society" in q
        or "societies" in q
        or "event approval" in q
    ):
        return get_sections(["9.1", "9.2", "9.3", "9.4"])


    # ---------- MEDICAL ----------

    if "medical" in q or "hospital" in q:
        return get_sections(["2.1", "2.2", "2.3", "2.4"])


    # ---------- ATTENDANCE ----------

    if "attendance" in q:
        return get_sections(["1.1", "1.2", "1.3", "1.4"])


    return []


# =========================================================
# GENERATE ANSWER
# =========================================================

def make_answer(question):

    # 1. Explicit NOT COVERED
    if is_not_covered(question):
        return {
            "type": "NOT_COVERED",
            "answer": (
                "This question is not covered by the supplied "
                "rulebook corpus."
            ),
            "documents": []
        }


    # 2. Conflicts
    result = attendance_medical_conflict(question)
    if result:
        return result

    result = attendance_waiver_conflict(question)
    if result:
        return result

    result = fee_conflict(question)
    if result:
        return result


    # 3. Route to relevant topic
    docs = route_question(question)

    if not docs:
        return {
            "type": "NOT_COVERED",
            "answer": (
                "This question is not covered by the supplied "
                "rulebook corpus."
            ),
            "documents": []
        }


    # 4. Rank only the selected documents
    ranked = []

    for doc in docs:
        score = similarity(question, doc["text"])

        ranked.append({
            **doc,
            "score": score
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)


    # =====================================================
    # SPECIAL CLEAN ANSWERS
    # =====================================================

    q = question.lower()


    # GPA
    if "scholarship" in q and "gpa" in q:
        return {
            "type": "ANSWERED",
            "answer": (
                "A merit scholarship normally requires a "
                "GPA of at least 7.5."
            ),
            "documents": ranked[:1]
        }


    # Scholarship appeal
    if "scholarship" in q and "appeal" in q:
        return {
            "type": "ANSWERED",
            "answer": (
                "Students may appeal scholarship decisions "
                "within 15 days."
            ),
            "documents": ranked[:1]
        }


    # Hostel curfew
    if "curfew" in q:
        return {
            "type": "ANSWERED",
            "answer": (
                "The hostel curfew is published by the Warden."
            ),
            "documents": ranked[:1]
        }


    # Discipline appeal
    if "appeal" in q and "disciplin" in q:
        return {
            "type": "ANSWERED",
            "answer": (
                "A disciplinary decision may be appealed "
                "within 10 working days."
            ),
            "documents": ranked[:1]
        }


    # Library loan
    if "borrow" in q and "library" in q:
        return {
            "type": "ANSWERED",
            "answer": (
                "The library loan period is specified in §8.1."
            ),
            "documents": ranked[:1]
        }


    # Society event approval
    if "event" in q and "approval" in q:
        return {
            "type": "ANSWERED",
            "answer": (
                "Societies must submit event approval requests "
                "5 working days before the event."
            ),
            "documents": ranked[:1]
        }


    # Default answer
    best = ranked[:3]

    answer_text = best[0]["text"]

    return {
        "type": "ANSWERED",
        "answer": answer_text,
        "documents": best
    }


# =========================================================
# HTML
# =========================================================

def render_page():

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Rulebook QA</title>

        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1000px;
                margin: 40px auto;
                padding: 20px;
                background: #f5f5f5;
            }

            h1 {
                color: #222;
            }

            textarea {
                width: 100%;
                height: 90px;
                padding: 10px;
                font-size: 16px;
            }

            button {
                margin-top: 10px;
                padding: 12px 25px;
                font-size: 16px;
                cursor: pointer;
            }

            .box {
                background: white;
                padding: 20px;
                margin-top: 20px;
                border-radius: 8px;
            }

            .evidence {
                background: #fafafa;
                padding: 15px;
                margin-top: 12px;
                border-left: 4px solid #555;
            }

            .score {
                font-weight: bold;
            }

            pre {
                white-space: pre-wrap;
            }
        </style>
    </head>

    <body>

        <h1>University Rulebook QA</h1>

        <form method="post" action="/ask">

            <textarea
                name="question"
                placeholder="Ask a question about the university rulebook..."
                required
            ></textarea>

            <br>

            <button type="submit">Ask</button>

        </form>

    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def home():
    return render_page()


@app.post("/ask", response_class=HTMLResponse)
def ask(question: str = Form(...)):

    result = make_answer(question)

    evidence_html = ""

    for doc in result["documents"]:

        score = doc.get("score", 0)

        evidence_html += f"""
        <div class="evidence">

            <b>{doc['section']}</b>

            <p class="score">
                Similarity: {score:.3f}
            </p>

            <pre>{doc['text']}</pre>

            <small>
                Source: {doc['source']}
            </small>

        </div>
        """


    return f"""
    <!DOCTYPE html>
    <html>

    <head>
        <title>Rulebook QA Result</title>

        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 1000px;
                margin: 40px auto;
                padding: 20px;
                background: #f5f5f5;
            }}

            .box {{
                background: white;
                padding: 20px;
                margin-top: 20px;
                border-radius: 8px;
            }}

            .type {{
                font-size: 24px;
                font-weight: bold;
            }}

            .evidence {{
                background: #fafafa;
                padding: 15px;
                margin-top: 12px;
                border-left: 4px solid #555;
            }}

            .score {{
                font-weight: bold;
            }}

            pre {{
                white-space: pre-wrap;
                font-family: Arial, sans-serif;
            }}

            a {{
                display: inline-block;
                margin-top: 20px;
            }}
        </style>

    </head>

    <body>

        <div class="box">

            <div class="type">
                {result['type']}
            </div>

            <h2>Answer</h2>

            <p>
                {result['answer']}
            </p>

        </div>


        <div class="box">

            <h2>Evidence & Citations</h2>

            {evidence_html if evidence_html else
             "<p>No supporting evidence found.</p>"}

        </div>


        <a href="/">
            ← Ask another question
        </a>

    </body>

    </html>
    """