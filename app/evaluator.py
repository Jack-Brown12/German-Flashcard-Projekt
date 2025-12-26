from dataclasses import dataclass
from enum import Enum
import spacy
from spellchecker import SpellChecker
from typing import Any, Optional
from collections import Counter

nlp = spacy.load("de_core_news_md")
spell = SpellChecker(language='de')

class GrammarErrorType(Enum):
    NOUN_CAPITALIZATION = "noun_capitalization"
    PERFEKT_AUXILIARY = "perfekt_auxiliary"
    MAIN_CLAUSE_V2 = "main_clause_v2"
    SUBORDINATE_VERB_FINAL = "subordinate_verb_final"
    ACCUSATIVE_DATIVE = "accusative_dative_prepositions"
    SPELLING = "spelling"
    INVALID_SENTANCE = "invalid_sentance"


@dataclass
class GrammarResult:
    error_type: GrammarErrorType
    message: str
    details: Optional[Any] = None
    blocking: bool = False

# Standard formatting text for most grammar errors
GRAMMAR_MESSAGES = {
    "noun_capitalization": {
        "ERROR": (
            "In German, nouns must be capitalized."
        )
    },
    "perfekt_auxiliary": {
        "SEIN_ERROR": (
            "This verb forms the Perfekt with 'sein', "
            "but you used 'haben'."
        ),
        "HABEN_ERROR": (
            "This verb forms the Perfekt with 'haben', "
            "but you used 'sein'."
        ),
    },
    "main_clause_v2": {
        "ERROR": (
            "In German main clauses, the conjugated verb "
            "must appear in the second position."
        )
    },
    "subordinate_verb_final": {
        "ERROR": (
            "This sentance has a subordinate clause, so the conjugated verb "
            "must appear at the end. Your word order is incorrect."
        )
    },
    "accusative_dative_prepositions": {
        "ERROR": (
            "German prepositions must match their case."
        )
    }
}

def evaluate_translation(user_german: str, target_german: str, grammar_focus: str) -> dict:
    """Evaluate a German sentence for grammar mistakes and meaning."""

    doc = nlp(user_german)
    target_doc = nlp(target_german)

    results = []

    # 0. Refuse nonsense sentances that don't align with target answer
    if is_invalid_attempt(doc, target_doc):
        return [
            GrammarResult(
                error_type=GrammarErrorType.INVALID_SENTANCE,
                message= f"The correct sentence is: {target_german}",
                blocking=True
            )
        ]


    # 1. Spelling (block early)
    spelling = check_misspelled_words(doc)
    if len(spelling) > 1:
        return spelling[:5]

    results.extend(spelling)

    # 2. Structural grammar
    results.extend(check_main_clause_v2(doc))
    results.extend(check_subordinate_verb_final(doc))

    # 3. Morphology / fine grammar
    results.extend(check_noun_capitalization(doc))
    results.extend(check_perfekt_auxiliary(doc))
    results.extend(check_accusative_dative_prepositions(doc, target_doc))

    # One final check. Stops nonsense words from sneaking by checker.
    if final_word_check(doc, target_doc):
        results.extend([
            GrammarResult(
                error_type=GrammarErrorType.INVALID_SENTANCE,
                message= f"Very close! The correct sentence is: {target_german}",
                blocking=False
            )]
        )

    if not results:
        return [
            GrammarResult(
                error_type=None,
                message="No grammar errors detected. Well done."
            )
        ]

    return results[:5] # Maximum 5 Error Messages at once --> don't overwhelm user

_spell = None

def get_spellchecker():
    global _spell
    if _spell is None:
        from spellchecker import SpellChecker
        _spell = SpellChecker(language="de")
    return _spell


def check_misspelled_words(doc):
    results = []

    spell = get_spellchecker()

    for token in doc:
        if (
            token.is_alpha
            and token.pos_ in {"NOUN", "VERB", "ADJ", "ADV", "PROPN"}
        ):
            lower = token.text.lower()

            if lower in spell.unknown([lower]):
                results.append(
                    GrammarResult(
                        error_type=GrammarErrorType.SPELLING,
                        message=f"'{token.text}' may be misspelled.",
                        details={
                            "token": token.text,
                            "suggestion": spell.correction(lower),
                            "index": token.i
                        },
                        blocking=True
                    )
                )

    return results

CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV", "PROPN"}

def is_invalid_attempt(
    user_doc,
    target_doc,
    min_coverage=0.75,
    max_extra=2,
    max_core_extra=1,
    max_modifier_extra=2
):
    # Collect content lemmas
    user_lemmas = Counter(
        t.lemma_.lower()
        for t in user_doc
        if t.is_alpha 
    )
    # and t.pos_ in CONTENT_POS
    target_lemmas = Counter(
        t.lemma_.lower()
        for t in target_doc
        if t.is_alpha 
    )

    if not target_lemmas:
        return False

    # Coverage
    overlap = sum((user_lemmas & target_lemmas).values())
    coverage = overlap / sum(target_lemmas.values())

    # Extra content words
    extra = sum((user_lemmas - target_lemmas).values())

    # Main verb check (exclude auxiliaries)
    target_verbs = {
        t.lemma_.lower()
        for t in target_doc
        if t.pos_ == "VERB" and t.dep_ not in {"aux", "aux:pass"}
    }

    user_verbs = {
        t.lemma_.lower()
        for t in user_doc
        if t.pos_ == "VERB" and t.dep_ not in {"aux", "aux:pass"}
    }

    if coverage < min_coverage:
        return True

    if extra > max_extra:
        return True

    if target_verbs and not (target_verbs & user_verbs):
        return True
    
    # Extra-word accounting (core vs modifier)
    extra_core = 0
    extra_mod = 0

    for t in user_doc:
        if not t.is_alpha:
            continue

        lemma = t.lemma_.lower()
        if lemma in target_lemmas:
            continue

        if t.pos_ in {"NOUN", "VERB", "PROPN"}:
            extra_core += 1
        elif t.pos_ in {"ADJ", "ADV"}:
            extra_mod += 1

    if extra_core > max_core_extra:
        return True

    if extra_mod > max_modifier_extra:
        return True

    return False

def check_noun_capitalization(doc):
    uncapitalized_nouns = []
    for token in doc:
        if (token.pos_ == 'NOUN' or token.pos_ == 'PROPN') and not token.is_oov:
            if str(token)[0].islower():
                    uncapitalized_nouns.append(str(token))

    if not uncapitalized_nouns:
            return []

    return [
        GrammarResult(
            error_type=GrammarErrorType.NOUN_CAPITALIZATION,
            message=(
                f"{GRAMMAR_MESSAGES['noun_capitalization']['ERROR']} "
                f"Capitalize: {', '.join(uncapitalized_nouns)}"
            ),
            details=uncapitalized_nouns,
            blocking=False
        )
    ]

def check_perfekt_auxiliary(doc):
    error_code = _violates_perfekt_auxiliary(doc)
    if not error_code:
        return []

    return [
        GrammarResult(
            error_type=GrammarErrorType.PERFEKT_AUXILIARY,
            message=GRAMMAR_MESSAGES["perfekt_auxiliary"][error_code],
            details=error_code,
            blocking=False
        )
    ]

def _violates_perfekt_auxiliary(doc):
    
    COMMON_SEIN_VERBS = [
        "sein",
        "werden",
        "bleiben",
        "sterben",
        "passieren",
        "geschehen",
        "gelingen",
        "misslingen",
        "wachsen",
        "verschwinden",

        "gehen",
        "kommen",
        "fahren",
        "laufen",
        "fliegen",
        "reisen",
        "rennen",
        "steigen",
        "fallen",
        "ziehen",
        "wandern",

        "aufstehen",
        "hinsetzen",
        "ankommen",
        "abfahren",
        "aussteigen",
        "einsteigen",
        "zurückkommen",
        "mitkommen",
        "weggehen",

        "einschlafen",
        "aufwachen",
        "erwachen",
        "altern",
        "verwelken"
    ]
    error_code = None
    verb = ''
    aux = ''
    for token in doc:
        if token.tag_ == 'VVPP' or token.tag_ == 'VAPP':
            verb = token.lemma_
        if token.tag_ == 'VAFIN':
            aux = token.lemma_

    if verb and aux:
        if verb in COMMON_SEIN_VERBS and aux != 'sein':
            error_code = 'SEIN_ERROR'
        elif verb not in COMMON_SEIN_VERBS and aux != 'haben':
            error_code = 'HABEN_ERROR'
    
    if not error_code:
            return []

    return error_code

def check_main_clause_v2(doc):
    if not _violates_main_clause_v2(doc):
        return []

    return [
        GrammarResult(
            error_type=GrammarErrorType.MAIN_CLAUSE_V2,
            message=GRAMMAR_MESSAGES["main_clause_v2"]["ERROR"],
            blocking=True
        )
    ]

def _violates_main_clause_v2(doc):
    sent = list(doc)
    common_valid_modifiers = ['nur', 'sehr', 'mit']
    fin = get_finite_verb(sent)
    if not fin:
        return False

    vorfeld = [t for t in sent if t.i < fin.i and not t.is_punct]
    if not vorfeld:
        return False

    # find subject
    subjects = [t for t in fin.children if t.dep_ == "sb"]
    if not subjects:
        return False

    sb = subjects[0]

    # subject not in Vorfeld → fine
    if sb not in vorfeld:
        return False

    # allow full subject NP
    subject_span = [t for t in vorfeld if t.dep_ in {'nk', 'sb'} or t.pos_ in {'DET', 'NOUN'} or t.text.lower() in common_valid_modifiers]

    # if anything before the verb is not part of subject NP → violation
    for t in vorfeld:
        if t not in subject_span:
            return True

    return False

def get_finite_verb(sent):
    for token in sent:
        if (token.pos_ == "VERB" or token.pos_ == "AUX") and "VerbForm=Fin" in token.morph:
            return token
        
def check_subordinate_verb_final(doc):
    if not _violates_subordinate_verb_final(doc):
        return []

    return [
        GrammarResult(
            error_type=GrammarErrorType.SUBORDINATE_VERB_FINAL,
            message=GRAMMAR_MESSAGES["subordinate_verb_final"]["ERROR"],
            blocking=True
        )
    ]

def _violates_subordinate_verb_final(doc):
    sent = list(doc.sents)[0]
    subordinate_verb = None
    for token in sent:
        if token.pos_ == "VERB" and "Fin" in token.morph.get("VerbForm"):
            temp_subtree = list(token.subtree)
            if any(t.pos_ == "SCONJ" for t in temp_subtree):
                subordinate_verb = token
    
    if subordinate_verb:
        subordinate_verb_tree = list(subordinate_verb.subtree)
        return (subordinate_verb_tree[-1] != subordinate_verb)

    return False

def check_accusative_dative_prepositions(user_doc, target_doc):
    results = []

    # Collect DET/PRON tokens
    user_tokens = [t for t in user_doc if t.pos_ in ('DET', 'PRON')]
    target_tokens = [t for t in target_doc if t.pos_ in ('DET', 'PRON')]

    def sig(t):
        return (
            t.lemma_,
            t.pos_,
            tuple(t.morph.get("Case")),
        )

    user_sig = Counter(
        sig(t) for t in user_doc if t.pos_ in ("DET", "PRON")
    )
    target_sig = Counter(
        sig(t) for t in target_doc if t.pos_ in ("DET", "PRON")
    )

    if user_sig == target_sig:
        return []

    for u_token, t_token in zip(user_tokens, target_tokens):
        u_type = u_token.morph.get('PronType')
        t_type = t_token.morph.get('PronType')

        # Only compare tokens of the same pronoun type
        if u_type == t_type:
            u_case = u_token.morph.get('Case')
            t_case = t_token.morph.get('Case')

            if u_case != t_case:
                results.append(
                    GrammarResult(
                    error_type=GrammarErrorType.ACCUSATIVE_DATIVE,
                    message=(
                        f"You used '{u_token.text}', but this verb or "
                        f"preposition requires the {t_case} case. "
                        f"The correct form is '{t_token.text}'."
                    ),
                    details={
                        "user_pronoun": u_token.text,
                        "target_pronoun": t_token.text,
                        "user_case": u_case,
                        "target_case": t_case
                    },
                    blocking=False
                ))

    return results

def final_word_check(user_doc, target_doc, max_mismatch=2):
    user_tokens = [t.text.lower() for t in user_doc if t.is_alpha]
    target_tokens = [t.text.lower() for t in target_doc if t.is_alpha]

    mismatches = sum(1 for u, t in zip(user_tokens, target_tokens) if u != t)
    extra_tokens = abs(len(user_tokens) - len(target_tokens))

    if mismatches + extra_tokens > max_mismatch:
        return True
    return False