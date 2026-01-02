import json
from pathlib import Path


from fastapi.middleware.cors import CORSMiddleware

from app.src.evaluator import evaluate_translation

from enum import Enum
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field  

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",   # Vite default
        "http://127.0.0.1:5174",
        "https://german-flashcard-projekt.vercel.app" # Deployment
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GrammarFocus(Enum):
    PERFEKT_AUXILIARY = "perfekt_auxiliary_sein_vs_haben"
    MAIN_CLAUSE_V2 = "verb_position_main_clause_v2"
    SUBORDINATE_VERB_FINAL = "verb_position_subordinate_clause"
    NOUN_CAPITALIZATION= "noun_capitalization"
    ACCUSATIVE_DATIVE_PREPOSITIONS = "accusative_vs_dative_prepositions"

class FlashcardBase(BaseModel):
    english_prompt : str = Field(..., min_length=10, max_length=256, description='English text for flashcard')
    target_german : str = Field(..., description='Ideal german translation of flashcard')
    grammar_focus : GrammarFocus = Field(..., description='Grammar concept flashcard targets')

class FlashcardCreate(FlashcardBase):
    pass

class Flashcard(FlashcardBase):
    flashcard_id : int = Field(..., description='Unique identifier of the flashcard')

class FlashcardUpdate(BaseModel):
    english_prompt : Optional[str] = Field(None, min_length=10, max_length=256, description='English text for flashcard')
    target_german : Optional[str] = Field(None,description='Ideal german translation of flashcard')
    grammar_focus : Optional[GrammarFocus] = Field(None, description='Grammar concept flashcard targets')

DATA_PATH = Path(__file__).parent / "flashcards.json"
def load_flashcards():
    with open(DATA_PATH, "r") as f:
        raw = json.load(f)
        return [Flashcard(**fc) for fc in raw]

all_flashcards = load_flashcards()

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get('/flashcards/{flashcard_id}', response_model=Flashcard)
def get_flashcard(flashcard_id : int):
    for flashcard in all_flashcards:
        if flashcard.flashcard_id == flashcard_id:
            return flashcard
    raise HTTPException(status_code=404, detail='Flashcard not found')

@app.get('/flashcards', response_model=List[Flashcard])
def get_list_flashcards(first_n: int = None):
    if first_n:
        return all_flashcards[:first_n]
    else:
        return all_flashcards

@app.get('/cards', response_model=int)
def get_num_flashcards():
    return len(all_flashcards)


@app.post('/flashcards', response_model=Flashcard)
def create_flashcard(flashcard : FlashcardCreate):
    new_flashcard_id = max([fc.flashcard_id for fc in all_flashcards]) + 1
    new_flashcard = Flashcard(
        flashcard_id=new_flashcard_id,
        english_prompt=flashcard.english_prompt,
        target_german=flashcard.target_german,
        grammar_focus=flashcard.grammar_focus
    )

    all_flashcards.append(new_flashcard)

    return new_flashcard

@app.post('/flashcards/{flashcard_id}', response_model=Flashcard)
def update_flashcard(flashcard_id : int, updated_flashcard : FlashcardUpdate):
    for flashcard in all_flashcards:
        if flashcard.flashcard_id == flashcard_id:
            if updated_flashcard.english_prompt is not None:
                flashcard.english_prompt = updated_flashcard.english_prompt
            if updated_flashcard.target_german is not None:
                flashcard.target_german = updated_flashcard.target_german
            if updated_flashcard.grammar_focus is not None:
                flashcard.grammar_focus = updated_flashcard.grammar_focus
            return flashcard

    raise HTTPException(status_code=404, detail='Flashcard not found')

@app.delete('/flashcards/{flashcard_id}', response_model=Flashcard)
def delete_flashcard(flashcard_id : int):
    for index, flashcard in enumerate(all_flashcards):
        if flashcard.flashcard_id == flashcard_id:
            return all_flashcards.pop(index)
        
    raise HTTPException(status_code=404, detail='Flashcard not found')

class UserResponse(BaseModel):
    user_german : str = Field(..., max_length=100, description='User answer to flashcard')
    flashcard_id : int = Field(..., description='current flashcard')

@app.post('/evaluate', response_model=dict)
def get_user_response(response: UserResponse):
    for fc in all_flashcards:
        if fc.flashcard_id == response.flashcard_id:
            analysis = evaluate_translation(
                user_german= response.user_german,
                target_german=fc.target_german,
            )   
            return analysis
     
    raise HTTPException(status_code=404, detail='Flashcard not found')