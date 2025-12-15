from enum import Enum
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field  

app = FastAPI()

class GrammarFocus(Enum):
    PERFEKT_AUXILIARY = "perfekt_auxiliary_sein_vs_haben"
    MAIN_CLAUSE_V2 = "verb_position_main_clause_v2"
    SUBORDINATE_VERB_FINAL = "verb_position_subordinate_clause"
    NOUN_CappTALIZATION = "noun_capptalization"
    ACCUSATIVE_DATIVE_PREPOSITIONS = "accusative_vs_dative_prepositions"

class FlashcardBase(BaseModel):
    english_prompt : str = Field(..., min_length=10, max_length=256, description='English text for flashcard')
    target_german : str = Field(..., description='Ideal german translation of flashcard')
    grammar_focus : GrammarFocus = Field(default=None, description='Grammar concept flashcard targets')

class FlashcardCreate(FlashcardBase):
    pass

class Flashcard(FlashcardBase):
    flashcard_id : int = Field(..., description='Unique identifier of the flashcard')

class FlashcardUpdate(BaseModel):
    english_prompt : Optional[str] = Field(None, min_length=10, max_length=256, description='English text for flashcard')
    target_german : Optional[str] = Field(None,description='Ideal german translation of flashcard')
    grammar_focus : Optional[GrammarFocus] = Field(None, description='Grammar concept flashcard targets')


all_flashcards = [
    Flashcard(flashcard_id=1, english_prompt="I went home yesterday.", target_german="Ich bin gestern nach Hause gegangen.", grammar_focus=GrammarFocus.PERFEKT_AUXILIARY),
    Flashcard(flashcard_id=2, english_prompt="She has eaten already.", target_german="Sie hat schon gegessen.", grammar_focus=GrammarFocus.PERFEKT_AUXILIARY),
    Flashcard(flashcard_id=3, english_prompt="Today I am learning German.", target_german="Heute lerne ich Deutsch.", grammar_focus=GrammarFocus.MAIN_CLAUSE_V2),
    Flashcard(flashcard_id=4, english_prompt="After work, he goes to the gym.", target_german="Nach der Arbeit geht er ins Fitnessstudio.", grammar_focus=GrammarFocus.MAIN_CLAUSE_V2),
    Flashcard(flashcard_id=5, english_prompt="I know that he is coming tomorrow.", target_german="Ich weiß, dass er morgen kommt.", grammar_focus=GrammarFocus.SUBORDINATE_VERB_FINAL),
    Flashcard(flashcard_id=6, english_prompt="She says that she doesn’t have time.", target_german="Sie sagt, dass sie keine Zeit hat.", grammar_focus=GrammarFocus.SUBORDINATE_VERB_FINAL),
    Flashcard(flashcard_id=7, english_prompt="The dog is sleeping on the couch.", target_german="Der Hund schläft auf der Couch.", grammar_focus=GrammarFocus.NOUN_CappTALIZATION),
    Flashcard(flashcard_id=8, english_prompt="I like the city very much.", target_german="Ich mag die Stadt sehr.", grammar_focus=GrammarFocus.NOUN_CappTALIZATION),
    Flashcard(flashcard_id=9, english_prompt="I am waiting for the bus.", target_german="Ich warte auf den Bus.", grammar_focus=GrammarFocus.ACCUSATIVE_DATIVE_PREPOSITIONS),
    Flashcard(flashcard_id=10, english_prompt="She is helping her friend.", target_german="Sie hilft ihrer Freundin.", grammar_focus=GrammarFocus.ACCUSATIVE_DATIVE_PREPOSITIONS),
]

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