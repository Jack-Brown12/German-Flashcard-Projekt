# German Grammar Flashcard System

**Targeted German grammar practice with deterministic feedback**.  
Uses **spaCy + rule-based analysis** to detect and explain learner errors without relying on AI/LLM models. Designed for **structured feedback, reproducible evaluation, and real grammar learning** rather than general translation.

---

# Overview
This project is a German language learning application focused on **explicit grammar practice with deterministic feedback**.  
Instead of relying on large language models or paid API credits, the system uses **rule-based linguistic analysis** built on top of **spaCy’s German NLP pipeline** to detect and explain common learner errors.

The goal isn't total translation (like Google Translate), but **targeted German grammar practice w/ feedback**.

## Demo Video

Check out the project in action:

[![Project Demo](https://img.youtube.com/vi/Y4q5P1zVtzY/0.jpg)](https://youtu.be/Y4q5P1zVtzY)



# Key Features

- **Grammar-focused German flashcards** designed around specific learning objectives
- **Rule-based evaluation engine** covering six common beginner grammar categories (no LLMs used)
- **Deterministic, explainable feedback** for each detected error
- **Error severity classification** with priority-based sorting
- **Structured feedback output** suitable for frontend highlighting and UI control
- **Robust invalid-input detection** to reject nonsensical or structurally broken sentences

### Grammar Checks Implemented

- Accusative vs. dative case
- Verb position (main clause V2)
- Subordinate clause verb-final order
- Noun capitalization
- Perfect tense auxiliary selection (sein vs. haben)
- Spelling errors

Additional validation rejects:
- Sentences with insufficient lexical coverage
- Inputs that break dependency parsing
- Nonsense or invalid token sequences

---

# Tech Stack
### Backend
- Python 3.12
- FastAPI
- spaCy (`de_core_news_md`)
- uv (dependency management)

### Frontend
- React
- Fetch API for backend communication

---

## Evaluation Pipeline

User input is processed through a multi-stage evaluation pipeline:

1. **Invalid attempt detection**
   - Coverage checks
   - Verb presence checks
   - Early rejection of inputs that break spaCy parsing

2. **Spelling analysis**

3. **Structural grammar checks**
   - Main clause verb-second (V2)
   - Subordinate clause verb-final position

4. **Morphological grammar checks**
   - Noun capitalization
   - Perfect tense auxiliary selection

5. **Final consistency checks**
   - Extra or missing words
   - Excessive token mismatches

6. **Result aggregation**
   - Returns up to 5 errors, sorted by severity



## Error Representation

All grammar issues are returned in a **structured, machine-readable format**.  
Example response for a noun capitalization error:

```
"errors": [
    GrammarResult(
        error_type=GrammarErrorType.NOUN_CAPITALIZATION,
        message=GRAMMAR_MESSAGES["noun_capitalization"]["ERROR"],
        spans=[token.i],
        blocking=False,
        details=token.text,
        priority=ERROR_PRIORITY[GrammarErrorType.NOUN_CAPITALIZATION]
    )
]

```
### GrammarResult Structure

- **error_type**  
  Enum representing the grammar rule violated

- **message**  
  Predefined English explanation associated with the rule

- **spans**  
  Token indices used by the frontend for highlighting

- **blocking**  
  Indicates whether evaluation should stop due to structural invalidity  
  (used to trigger a fail state in the UI)

- **priority**  
  Enum used to rank errors from most to least severe

---

## Design Rationale

- **Deterministic rules over probabilistic models**  
  Ensures consistent grading, debuggability, and zero inference cost.

- **spaCy dependency parsing as a backbone**  
  Enables clause structure analysis, verb position checks, and morphological inspection.

- **Structured error output**  
  Decouples evaluation logic from UI rendering and supports scalable frontend features.

---

## Limitations and Challenges

- Grammar coverage is finite and constrained to supported flashcard prompts
- Accusative vs. dative detection is inherently error-prone due to prepositional ambiguity
- spaCy may misclassify:
  - Misspelled words as nouns
  - Finite verbs as infinitives  
  Mitigations are implemented but edge cases remain
- Planned AI-generated feedback was abandoned due to API cost and determinism concerns

---

## Future Work

- Expansion of grammar rule coverage
- User progress tracking and analytics
- Additional flashcard sets organized by grammar concept
- UI enhancements (audio feedback, animations,  mobile support)