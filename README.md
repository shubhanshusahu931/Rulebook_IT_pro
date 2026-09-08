# The Rulebook That Argues With Itself

A citation-first question-answering system for university regulations.

## Features

- FastAPI backend
- POST `/ask` endpoint
- HTML web interface
- Citation for every answer
- Section references
- Similarity scores
- Conflict detection
- NOT_COVERED detection
- 27,000+ word rulebook corpus
- Markdown, CSV and PDF documents
- 3 intentional contradictions
- 25 out-of-corpus test questions

## Response Types

### ANSWERED
The corpus contains supporting information.

### NOT_COVERED
The rulebook does not contain enough information.
The system does not guess.

### CONFLICT
Two or more rulebook sections provide contradictory information.

## Run

```bash
pip install -r requirements.txt
python -m uvicorn app:app --reload