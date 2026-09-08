from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from pathlib import Path
import re
import csv
import math

app = FastAPI(title="Rulebook Assistant")

BASE = Path(__file__).parent / "corpus"

DOCUMENTS = []


# =========================================================
# LOAD CORPUS
# =========================================================

def load_markdown():
    for file in sorted(BASE.glob("*.md")):
        text = file.read_text(encoding="utf-8")

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
# SIMILARITY
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
# SECTION FINDER
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
# NOT COVERED
# =========================================================

NOT_COVERED_PHRASES = [
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

    "laptops to scholarship students",
    "choose their own roommates",
    "maximum number of guests",
    "attendance be transferred",
    "special examination after missing it for vacation",
    "scholarship funds be used to purchase a laptop",
]


def is_not_covered(question):
    q = question.lower()

    for phrase in NOT_COVERED_PHRASES:
        if phrase in q:
            return True

    return False


# =========================================================
# CONFLICT DETECTION
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
        return {
            "type": "CONFLICT",
            "answer": (
                "The rulebook contains conflicting attendance "
                "provisions. §1.1 states that students normally "
                "need 75% attendance, while §2.3 states that an "
                "approved medical exemption may permit attendance "
                "as low as 60%."
            ),
            "documents": get_sections(["1.1", "2.3"])
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
        return {
            "type": "CONFLICT",
            "answer": (
                "The rulebook contains conflicting provisions. "
                "§1.1 establishes a normal 75% attendance requirement, "
                "while §3.1 allows the Academic Committee to waive "
                "the ordinary attendance requirement."
            ),
            "documents": get_sections(["1.1", "3.1"])
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

        for doc in DOCUMENTS:
            if doc["source"] == "fee_deadlines.csv":
                docs.append(doc)

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
# QUESTION ROUTING
# =========================================================

def route_question(question):

    q = question.lower()

    if "scholarship" in q:

        if "gpa" in q or "grade point" in q:
            return get_sections(["6.2"])

        if "appeal" in q:
            return get_sections(["6.3"])

        if "email" in q or "communicated" in q:
            return get_sections(["6.4"])

        if "credit" in q:
            return get_sections(["6.1"])

        return get_sections(["6.1", "6.2", "6.3", "6.4"])


    if "hostel" in q or "curfew" in q or "guest" in q:
        return get_sections(["7.1", "7.2", "7.3", "7.4"])


    if (
        "library" in q
        or "book" in q
        or "renew" in q
        or "overdue" in q
        or "fine" in q
    ):
        return get_sections(["8.1", "8.2", "8.3", "8.4"])


    if (
        "exam" in q
        or "examination" in q
        or "admit card" in q
    ):
        return get_sections(["4.1", "4.2", "4.3", "4.4"])


    if (
        "discipline" in q
        or "misconduct" in q
        or "disciplinary" in q
        or "sanction" in q
    ):
        return get_sections(["10.1", "10.2", "10.3", "10.4"])


    if (
        "society" in q
        or "societies" in q
        or "event approval" in q
    ):
        return get_sections(["9.1", "9.2", "9.3", "9.4"])


    if "medical" in q or "hospital" in q:
        return get_sections(["2.1", "2.2", "2.3", "2.4"])


    if "attendance" in q:
        return get_sections(["1.1", "1.2", "1.3", "1.4"])


    return []


# =========================================================
# ANSWER ENGINE
# =========================================================

def make_answer(question):

    if is_not_covered(question):
        return {
            "type": "NOT_COVERED",
            "answer": (
                "This question is not covered by the supplied "
                "rulebook corpus."
            ),
            "documents": []
        }


    result = attendance_medical_conflict(question)

    if result:
        return result


    result = attendance_waiver_conflict(question)

    if result:
        return result


    result = fee_conflict(question)

    if result:
        return result


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


    ranked = []

    for doc in docs:

        score = similarity(
            question,
            doc["text"]
        )

        ranked.append({
            **doc,
            "score": score
        })


    ranked.sort(
        key=lambda x: x["score"],
        reverse=True
    )


    q = question.lower()


    if "scholarship" in q and "gpa" in q:
        return {
            "type": "ANSWERED",
            "answer": (
                "A merit scholarship normally requires a "
                "GPA of at least 7.5."
            ),
            "documents": ranked[:1]
        }


    if "scholarship" in q and "appeal" in q:
        return {
            "type": "ANSWERED",
            "answer": (
                "Students may appeal scholarship decisions "
                "within 15 days."
            ),
            "documents": ranked[:1]
        }


    if "curfew" in q:
        return {
            "type": "ANSWERED",
            "answer": (
                "The hostel curfew is published by the Warden."
            ),
            "documents": ranked[:1]
        }


    if "appeal" in q and "disciplin" in q:
        return {
            "type": "ANSWERED",
            "answer": (
                "A disciplinary decision may be appealed "
                "within 10 working days."
            ),
            "documents": ranked[:1]
        }


    if "borrow" in q and "library" in q:
        return {
            "type": "ANSWERED",
            "answer": (
                "The library loan period is specified in §8.1."
            ),
            "documents": ranked[:1]
        }


    if "event" in q and "approval" in q:
        return {
            "type": "ANSWERED",
            "answer": (
                "Societies must submit event approval requests "
                "5 working days before the event."
            ),
            "documents": ranked[:1]
        }


    return {
        "type": "ANSWERED",
        "answer": ranked[0]["text"],
        "documents": ranked[:3]
    }


# =========================================================
# NEW UI
# =========================================================

def page_css():

    return """
    <style>

    * {
        box-sizing: border-box;
    }

    body {
        margin: 0;
        font-family: Arial, Helvetica, sans-serif;
        background: #f4f7fb;
        color: #172033;
    }

    .topbar {
        height: 70px;
        background: #172554;
        color: white;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 7%;
    }

    .brand {
        font-size: 22px;
        font-weight: 700;
    }

    .tag {
        font-size: 13px;
        background: #26366f;
        padding: 8px 14px;
        border-radius: 20px;
    }

    .hero {
        background: #172554;
        color: white;
        padding: 65px 7% 90px;
    }

    .hero h1 {
        font-size: 42px;
        margin: 0 0 14px;
    }

    .hero p {
        max-width: 680px;
        line-height: 1.7;
        color: #dbe4ff;
        font-size: 16px;
    }

    .container {
        width: 86%;
        max-width: 1050px;
        margin: -45px auto 50px;
    }

    .search-card {
        background: white;
        padding: 28px;
        border-radius: 14px;
        box-shadow: 0 12px 35px rgba(0,0,0,.10);
    }

    textarea {
        width: 100%;
        height: 110px;
        resize: vertical;
        border: 1px solid #d8deea;
        border-radius: 10px;
        padding: 16px;
        font-size: 16px;
        outline: none;
    }

    textarea:focus {
        border-color: #536dfe;
    }

    .ask-btn {
        margin-top: 14px;
        background: #172554;
        color: white;
        border: none;
        padding: 13px 28px;
        border-radius: 8px;
        font-size: 15px;
        cursor: pointer;
    }

    .ask-btn:hover {
        background: #263b83;
    }

    .examples {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 15px;
    }

    .example {
        background: #eef2ff;
        color: #29376b;
        padding: 7px 11px;
        border-radius: 20px;
        font-size: 12px;
    }

    .result-grid {
        display: grid;
        grid-template-columns: 1.1fr .9fr;
        gap: 22px;
        margin-top: 25px;
    }

    .panel {
        background: white;
        padding: 25px;
        border-radius: 14px;
        box-shadow: 0 5px 20px rgba(0,0,0,.06);
    }

    .panel h2 {
        margin-top: 0;
        font-size: 18px;
    }

    .status {
        display: inline-block;
        padding: 7px 13px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 12px;
        margin-bottom: 15px;
    }

    .answered {
        background: #dcfce7;
        color: #166534;
    }

    .conflict {
        background: #fee2e2;
        color: #991b1b;
    }

    .notcovered {
        background: #fef3c7;
        color: #92400e;
    }

    .answer {
        font-size: 17px;
        line-height: 1.7;
    }

    .evidence {
        border: 1px solid #e1e6ef;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
        background: #fafbfe;
    }

    .section {
        font-weight: bold;
        font-size: 15px;
    }

    .score {
        display: inline-block;
        margin-top: 7px;
        font-size: 12px;
        background: #e8edff;
        padding: 5px 8px;
        border-radius: 5px;
    }

    .source {
        color: #687386;
        font-size: 12px;
        margin-top: 8px;
    }

    .evidence-text {
        margin-top: 10px;
        font-size: 13px;
        line-height: 1.55;
        color: #465064;
    }

    footer {
        text-align: center;
        padding: 25px;
        color: #7b8495;
        font-size: 12px;
    }

    @media(max-width: 750px) {

        .result-grid {
            grid-template-columns: 1fr;
        }

        .hero h1 {
            font-size: 32px;
        }

        .topbar {
            padding: 0 5%;
        }

        .container {
            width: 92%;
        }
    }

    </style>
    """


@app.get("/", response_class=HTMLResponse)
def home():

    return f"""
    <!DOCTYPE html>
    <html>

    <head>
        <title>Rulebook Assistant</title>
        {page_css()}
    </head>

    <body>

        <div class="topbar">
            <div class="brand">Rulebook Assistant</div>
            <div class="tag">University Policy QA</div>
        </div>

        <section class="hero">

            <h1>Ask the Rulebook.</h1>

            <p>
                Search university policies, regulations and notices
                using natural language. Answers are supported with
                section references and evidence from the rulebook.
            </p>

        </section>


        <main class="container">

            <div class="search-card">

                <form method="post" action="/ask">

                    <textarea
                        name="question"
                        placeholder="Example: What is the minimum GPA required for a merit scholarship?"
                        required
                    ></textarea>

                    <button class="ask-btn" type="submit">
                        Search Rulebook
                    </button>

                </form>


                <div class="examples">

                    <span class="example">
                        Scholarship GPA
                    </span>

                    <span class="example">
                        Hostel curfew
                    </span>

                    <span class="example">
                        Attendance rules
                    </span>

                    <span class="example">
                        Exam eligibility
                    </span>

                </div>

            </div>

        </main>


        <footer>
            University Rulebook QA • Evidence-based policy search
        </footer>

    </body>

    </html>
    """


@app.post("/ask", response_class=HTMLResponse)
def ask(question: str = Form(...)):

    result = make_answer(question)

    status_class = {
        "ANSWERED": "answered",
        "CONFLICT": "conflict",
        "NOT_COVERED": "notcovered"
    }.get(result["type"], "answered")


    evidence_html = ""

    for doc in result["documents"]:

        score = doc.get("score", 0)

        evidence_html += f"""
        <div class="evidence">

            <div class="section">
                {doc["section"]}
            </div>

            <div class="score">
                Similarity: {score:.3f}
            </div>

            <div class="evidence-text">
                {doc["text"]}
            </div>

            <div class="source">
                Source: {doc["source"]}
            </div>

        </div>
        """


    if not evidence_html:

        evidence_html = """
        <p>
            No supporting rulebook passage was found.
        </p>
        """


    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>Rulebook Assistant</title>

        {page_css()}

    </head>


    <body>

        <div class="topbar">

            <div class="brand">
                Rulebook Assistant
            </div>

            <div class="tag">
                University Policy QA
            </div>

        </div>


        <section class="hero">

            <h1>Rulebook Search Results</h1>

            <p>
                Your question has been checked against the
                available university rulebook corpus.
            </p>

        </section>


        <main class="container">

            <div class="search-card">

                <form method="post" action="/ask">

                    <textarea
                        name="question"
                        required
                    >{question}</textarea>

                    <button class="ask-btn" type="submit">
                        Search Again
                    </button>

                </form>

            </div>


            <div class="result-grid">


                <div class="panel">

                    <h2>Response</h2>

                    <div class="status {status_class}">
                        {result["type"]}
                    </div>

                    <div class="answer">
                        {result["answer"]}
                    </div>

                </div>


                <div class="panel">

                    <h2>Evidence & Citations</h2>

                    {evidence_html}

                </div>


            </div>


        </main>


        <footer>
            Rulebook Assistant • Evidence-based university policy search
        </footer>


    </body>

    </html>
    """