# 📘 Rulebook Assistant — "The Rulebook That Argues With Itself"

Ye ek **citation-first Question-Answering system** hai jo university ke rules/regulations (attendance, medical leave, fees, scholarships, hostel, library, exams, discipline, societies) ke uper sawal-jawab karta hai — **bina kuch bhi guess kiye**. Har jawab ke sath uska **source section (§)** aur **evidence text** dikhaya jata hai, aur agar rulebook me do jagah conflicting info ho, to system usko silently ignore nahi karta, balki **CONFLICT** bata deta hai.

Ye project **FastAPI** (Python backend) par bana hai aur ek simple **HTML web interface** deta hai jaha user browser me sawal type karke search kar sakta hai.

---

## 🧠 Ye Kaam Kaise Karta Hai (Working)

### 1. Corpus Loading (`corpus/` folder)
App start hote hi `app.py` ke andar do functions chalte hain:

- **`load_markdown()`** — `corpus/*.md` files (jaise `01-attendance.md`, `05-fees.md`, etc.) ko padhta hai. Har file me `## §X.X` se shuru hone wale sections hote hain — inhe alag-alag "documents" (chunks) bana kar memory me store kar liya jata hai (source file, section number, aur text ke sath).
- **`load_csv()`** — `corpus/fee_deadlines.csv` ko padhta hai aur har row ko ek readable sentence bana kar document list me add karta hai (jaise fee item, deadline, late fee, authority).

Ek `special_notices.pdf` bhi corpus me hai jiska ek fact (§11.2 — tuition deadline 18 August) code ke andar hardcoded reference ke roop me use hota hai (fee conflict dikhane ke liye).

### 2. Question Aane Par Kya Hota Hai (`make_answer()` function)
Jab koi question aata hai, to ye order me check hota hai:

1. **NOT_COVERED check** — Agar question kisi predefined "out-of-scope" phrase (jaise "bicycle", "pets", "cryptocurrency", "drone", etc.) se match kare, to seedha bata diya jata hai ki rulebook me ye topic cover nahi hai.
2. **Conflict Detection** — 3 hardcoded conflict-checkers hain:
   - **Attendance vs Medical exemption** (§1.1 vs §2.3)
   - **Attendance vs Committee Waiver** (§1.1 vs §3.1)
   - **Tuition deadline conflict** (fee_deadlines.csv vs special_notices.pdf §11.2)
   
   Agar question in patterns se match kare, to `CONFLICT` type ka response milta hai jisme dono contradicting sections evidence ke roop me dikhaye jate hain.
3. **Topic Routing (`route_question()`)** — Agar upar kuch match na ho, to keyword ke basis par (jaise "scholarship", "hostel", "library", "exam", "discipline", "society", "medical", "attendance") relevant sections dhoonde jate hain.
4. **Similarity Scoring** — Matched sections ko question ke words ke sath ek simple **cosine-jaisi similarity score** (common words ka overlap) se rank kiya jata hai — best matching section sabse upar aata hai.
5. Agar kuch bhi match na ho, to phir se `NOT_COVERED` return hota hai.

### 3. Response Types
| Type | Matlab |
|---|---|
| ✅ **ANSWERED** | Rulebook me is sawal ka jawab maujood hai, evidence ke sath. |
| ⚠️ **CONFLICT** | Rulebook ke do sections ek-dusre se contradict karte hain — system dono dikhata hai, khud decide nahi karta. |
| 🚫 **NOT_COVERED** | Rulebook me is topic ki koi jaankari nahi — system galt jawab guess nahi karta. |

### 4. Web Interface
`app.py` khud hi HTML pages generate karta hai (koi separate templates folder nahi):
- `GET /` → Home page jaha textarea me sawal type karte hain.
- `POST /ask` → Form submit hone par question process hota hai aur result page dikhta hai jisme **Response** (status + answer) aur **Evidence & Citations** (matched sections, similarity score, source file) side-by-side dikhte hain.

---

## 📁 Project Structure

```
RulebookQA/
├── app.py                  # Main FastAPI app (poora logic + UI yahi hai)
├── generate_corpus.py      # Corpus files me extra "filler" content add karta hai (already run ho chuka hai)
├── test_runner.py          # test_set.json ke sawalon par app ko test karta hai
├── test_set.json           # 25 "out-of-corpus" (NOT_COVERED honi chahiye) test questions
├── CONTRADICTIONS.md       # 3 intentional contradictions ki documentation
├── requirements.txt        # Python dependencies
├── corpus/
│   ├── 01-attendance.md
│   ├── 02-medical.md
│   ├── 03-committee.md
│   ├── 04-examinations.md
│   ├── 05-fees.md
│   ├── 06-scholarships.md
│   ├── 07-hostel.md
│   ├── 08-library.md
│   ├── 09-societies.md
│   ├── 10-discipline.md
│   ├── fee_deadlines.csv
│   └── special_notices.pdf
└── README.md
```

---

## ⚙️ Setup & Installation

> **Requirement:** Python 3.9+ installed hona chahiye.

### Step 1 — Dependencies install karo

⚠️ Note: `requirements.txt` filhal khaali hai, isliye manually ye 3 packages install karo:

```bash
pip install fastapi uvicorn python-multipart
```

(Behtar hoga in packages ko `requirements.txt` me bhi likh do, taki future me `pip install -r requirements.txt` seedha kaam kare.)

### Step 2 — Project folder me jao

```bash
cd RulebookQA
```

---

## ▶️ App Kaise Chalayein (Run)

```bash
python -m uvicorn app:app --reload
```

Terminal me kuch aisa output milega:

```
Uvicorn running on http://127.0.0.1:8000
```

Ab apne browser me kholo:

👉 **http://127.0.0.1:8000**

Yaha textarea me apna sawal type karo (jaise *"What is the minimum GPA required for a merit scholarship?"*) aur **Search Rulebook** button dabao.

`--reload` flag ka fayda: code me koi change karoge to server automatically restart ho jayega — development ke liye useful hai.

---

## 🧪 Automated Tests Kaise Chalayein

`test_runner.py` file, `test_set.json` ke 25 "out-of-corpus" sawalon ko app ke through chalati hai aur check karti hai ki har ek ka response **NOT_COVERED** aaya ya nahi (kyunki ye sawal jaan-boojh kar rulebook se bahar ke hain).

```bash
python test_runner.py
```

Output me har question ke against **PASS/FAIL** aur end me total score dikhega:

```
01. PASS - NOT_COVERED
    What happens if I miss an exam because of a family wedding?
...
==============================
PASSED: 25/25
==============================
```

---

## 🔍 Kuch Sample Sawal Try Karne Ke Liye

| Category | Example Question |
|---|---|
| Scholarship | "What is the minimum GPA required for a merit scholarship?" |
| Hostel | "What is the hostel curfew time?" |
| Conflict (Attendance) | "Can medical exemption allow attendance below 75%?" |
| Conflict (Fees) | "What is the tuition fee deadline?" |
| Out of scope | "Are pets allowed inside university hostels?" |

---

## 🛠️ Corpus Ko Regenerate Karna (Optional)

`generate_corpus.py` script har `corpus/*.md` file me extra "General Guidance" paragraphs add karti hai taki corpus size 27,000+ words ho jaye. Ye script pehle se ek baar chal chuki hai. Agar dubara chalana ho (naye corpus files ke sath), to:

```bash
python generate_corpus.py
```

⚠️ **Dhyan rahe:** Ye script existing `.md` files ko overwrite karti hai — dubara chalane se pehले backup lena behtar hoga, warna guidance duplicate ho jayegi.

---

## ⚠️ Intentional Contradictions

Is rulebook me **3 jaan-boojh kar dale gaye contradictions** hain (details ke liye `CONTRADICTIONS.md` dekho):

1. **Attendance vs Medical Exemption** — §1.1 me 75% zaroori, par §2.3 me medical exemption se 60% tak allow.
2. **Attendance vs Committee Waiver** — §1.1 ordinary requirement, §3.1 Academic Committee ise waive kar sakti hai.
3. **Tuition Deadline** — `fee_deadlines.csv` me 15/20 August, par `special_notices.pdf` §11.2 me 18 August.

System ka goal ye dikhana hai ki wo aisi contradictions ko **detect aur transparently report** karta hai, na ki chup-chaap ek answer choose kar leta hai.

---

## 📌 Limitations (Jaanna Zaroori)

- Similarity matching simple **word-overlap based** hai (koi ML/embedding model use nahi hua) — isliye phrasing thoda alag hone par bhi results vary ho sakte hain.
- Kai answers (jaise conflict detection, kuch specific answers) **rule-based/hardcoded** hain, generic AI model nahi hai.
- `special_notices.pdf` ka content directly parse nahi hota — sirf ek fact code me manually likha gaya hai.
- Ye ek demo/learning project hai, real production university system nahi.

---

## 📄 License / Purpose

Ye project ek **demo/evaluation system** hai jo dikhata hai ki ek QA system kaise (a) evidence-based answers de, (b) missing info ko honestly "NOT_COVERED" bole, aur (c) contradictory rules ko flag kare — bina galat confidence ke saath koi ek jawab thop diye.