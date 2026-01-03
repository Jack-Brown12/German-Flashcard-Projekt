from dataclasses import dataclass
from enum import Enum
import spacy
from spellchecker import SpellChecker
from typing import Any, Optional
from collections import Counter
from difflib import SequenceMatcher

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


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
    WORD_OUT_OF_TARGET = "word_out_of_target"
    NEAR_MISS = "near_miss" 

ERROR_PRIORITY = {
    GrammarErrorType.INVALID_SENTANCE: 100,
    GrammarErrorType.WORD_OUT_OF_TARGET: 90,
    GrammarErrorType.SPELLING: 50,
    GrammarErrorType.MAIN_CLAUSE_V2: 40,
    GrammarErrorType.SUBORDINATE_VERB_FINAL: 40,
    GrammarErrorType.ACCUSATIVE_DATIVE: 30,
    GrammarErrorType.PERFEKT_AUXILIARY: 30,
    GrammarErrorType.NOUN_CAPITALIZATION: 20,
    GrammarErrorType.NEAR_MISS: 5,
}



@dataclass
class GrammarResult:
    error_type: GrammarErrorType
    message: str
    spans: Optional[list[int]] = None 
    details: Optional[Any] = None
    blocking: bool = False
    priority: int = 0

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

def normalize_text(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    if text[-1] not in ".!?":
        return text + "."
    return text.strip()

def evaluate_translation(user_german: str, target_german: str) -> dict:
    """Evaluate a German sentence for grammar mistakes and meaning."""
    user_german = normalize_text(user_german)

    doc = nlp(user_german)
    target_doc = nlp(target_german)

    tokens = []
    for t in doc:
        if t.is_punct:
            tokens.append(t.text)  # punctuation stays separate
        else:
            tokens.append(t.text)
    results = []

    def serialize(results):
        return [
            {
                "type": r.error_type.value,
                "message": r.message,
                "spans": r.spans,
                "blocking": r.blocking,
                "details": r.details,
                "priority": r.priority
            }
            for r in results
        ]

    # 1. Spelling (block early) --> Spelling errors on syntactic anchors are fatal. Must stop evaluator.
    spelling, critical = check_misspelled_words(doc, target_doc)

    if critical:
        return {
            "meaning_conveyed": False,
            "correct_sentence": target_german,
            "tokens": [t.text for t in doc],
            "errors": serialize(spelling[:5]),
        }

    # 1.a Refuse nonsense sentences
    if is_invalid_attempt(doc, target_doc):
        return {
            "meaning_conveyed": False,
            "correct_sentence": target_german,
            "tokens": tokens,
            "errors": serialize([
                GrammarResult(
                    error_type=GrammarErrorType.INVALID_SENTANCE,
                    message="Your sentence does not match the target meaning.",
                    spans=None,
                    blocking=True,
                    priority=ERROR_PRIORITY[GrammarErrorType.INVALID_SENTANCE]
                )
            ])
        }

    results.extend(spelling)

    # 2. Structural grammar
    results.extend(check_main_clause_v2(doc))
    results.extend(check_subordinate_verb_final(doc))

    # 3. Morphology / fine grammar
    results.extend(check_noun_capitalization(doc))
    results.extend(check_perfekt_auxiliary(doc))
    results.extend(check_accusative_dative_prepositions(doc, target_doc))

    # 3b. Extra words check --> ignores words that were already flagged as errors
    protected_spans = set()
    for r in results:
        if r.spans:
            protected_spans.update(r.spans)

    results.extend(check_extra_words(doc, target_doc, protected_spans))

    # 4. Final near-miss check --> An encouraging message to reward learners who might be frustrated with near misses
    if final_word_check(doc, target_doc):
        results.append(
            GrammarResult(
                error_type=GrammarErrorType.NEAR_MISS,
                message="Very close! You are a few words off.",
                spans=None,
                blocking=False,
                priority=ERROR_PRIORITY[GrammarErrorType.NEAR_MISS]
            )
        )
    #5 Check for overlapping errors, give precedence to the highest priority error_type
    results = resolve_conflicts(results)


    if not results:
        return {
            "meaning_conveyed": True,
            "correct_sentence": target_german,
            "tokens": tokens,
            "errors": []
        }

    return {
        "meaning_conveyed": False,
        "correct_sentence": target_german,
        "tokens": tokens,
        "errors": serialize(results[:5])
    }


_spell = None

def get_spellchecker():
    global _spell
    if _spell is None:
        from spellchecker import SpellChecker
        _spell = SpellChecker(language="de")
    return _spell

from difflib import SequenceMatcher

def check_misspelled_words(doc, target_doc):
    """
    Check for misspelled words in user input.
    Only flags errors that correspond to words in the target sentence.
    Returns:
      - results: list of GrammarResult
      - critical_hit: True if a subject/root/clausal object/finite verb is misspelled
    """
    results = []
    critical_hit = False
    spell = get_spellchecker()

    # Target words (for nouns, verbs, auxiliaries, etc.)
    target_words = {t.text.lower() for t in target_doc if t.is_alpha}
    # Target lemmas for verbs/auxiliary similarity check
    target_verbs = {t.lemma_.lower() for t in target_doc if t.pos_ in {"VERB", "AUX"}}

    for token in doc:
        if not (token.is_alpha and token.pos_ in {"NOUN", "VERB", "AUX", "ADJ", "ADV", "PROPN"}):
            continue

        lower = token.text.lower()
        is_critical = token.dep_ in {"sb", "ROOT", "oc"} or "VerbForm=Fin" in token.morph

        # Step 1: SpellChecker check, only flag if correction is in target
        suggestion = spell.correction(lower)
        if lower in spell.unknown([lower]) and suggestion and suggestion.lower() in target_words:
            if is_critical:
                critical_hit = True
            results.append(
                GrammarResult(
                    error_type=GrammarErrorType.SPELLING,
                    message=f"'{token.text}' may be misspelled. Did you mean '{suggestion}'?",
                    spans=[token.i],
                    details={"token": token.text, "suggestion": suggestion},
                    blocking=False,
                    priority=ERROR_PRIORITY[GrammarErrorType.SPELLING],
                )
            )
            continue  # Skip similarity check if spellchecker caught it

        # Step 2: Similarity check for verbs/aux only
        if token.pos_ in {"VERB", "AUX"} and token.pos_ in target_verbs:
            token_lemma = token.lemma_.lower()
            # Only flag if token is dissimilar to all target verbs
            if all(SequenceMatcher(None, token_lemma, lemma).ratio() < 0.75 for lemma in target_verbs):
                if is_critical:
                    critical_hit = True
                results.append(
                    GrammarResult(
                        error_type=GrammarErrorType.SPELLING,
                        message=f"'{token.text}' looks like a misspelling of a crucial verb for grammar evaluation.",
                        spans=[token.i],
                        blocking=True,
                        priority=ERROR_PRIORITY[GrammarErrorType.SPELLING],
                    )
                )

    return results, critical_hit


CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV", "PROPN"}

def is_invalid_attempt(
    user_doc,
    target_doc,
    min_coverage=0.60,
    max_extra=2,
    max_core_extra=1,
    max_modifier_extra=2
):
    # Collect content tokens
    user_tokens = Counter(
        t.text.lower()
        for t in user_doc
        if t.is_alpha 
    )
    # and t.pos_ in CONTENT_POS
    target_tokens = Counter(
        t.text.lower()
        for t in target_doc
        if t.is_alpha 
    )

    if not target_tokens:
        return False

    # Coverage
    overlap = sum((user_tokens & target_tokens).values())
    coverage = overlap / sum(target_tokens.values())

    # Extra content words
    extra = sum((user_tokens - target_tokens).values())

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

        text = t.text.lower()
        if text in target_tokens:
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

ALLOWED_EDGE_CASES = {'deutsch', 'englisch'}
def check_noun_capitalization(doc):
    results = []
    for token in doc:
        if ((token.pos_ == 'NOUN' or token.pos_ == 'PROPN') and not token.is_oov) or token.text in ALLOWED_EDGE_CASES:
            if str(token)[0].islower():
                    results.append(
                GrammarResult(
                    error_type=GrammarErrorType.NOUN_CAPITALIZATION,
                    message=GRAMMAR_MESSAGES["noun_capitalization"]["ERROR"],
                    spans=[token.i],
                    blocking=False,
                    details=token.text,
                    priority=ERROR_PRIORITY[GrammarErrorType.NOUN_CAPITALIZATION],
                )
            )
    return results

def check_perfekt_auxiliary(doc):
    error_code, aux_index = _violates_perfekt_auxiliary(doc)
    if not error_code:
        return []

    return [
        GrammarResult(
            error_type=GrammarErrorType.PERFEKT_AUXILIARY,
            message=GRAMMAR_MESSAGES["perfekt_auxiliary"][error_code],
            spans=[aux_index],
            details=error_code,
            blocking=False,
            priority=ERROR_PRIORITY[GrammarErrorType.PERFEKT_AUXILIARY],
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
    aux_index = -1
    verb = ''
    aux = ''
    for token in doc:
        if token.tag_ == 'VVPP' or token.tag_ == 'VAPP':
            verb = token.lemma_
        if token.tag_ == 'VAFIN':
            aux = token.lemma_
            aux_index = token.i

    if verb and aux:
        if verb in COMMON_SEIN_VERBS and aux != 'sein':
            error_code = 'SEIN_ERROR'
        elif verb not in COMMON_SEIN_VERBS and aux != 'haben':
            error_code = 'HABEN_ERROR'
    
    if not error_code:
            return (None, aux_index)

    return (error_code, aux_index)

def check_main_clause_v2(doc):
    if not _violates_main_clause_v2(doc):
        return []

    fin = get_finite_verb(doc)
    if fin:
        wrong_verb = [fin.i]
    else:
        wrong_verb = None

    return [
        GrammarResult(
            error_type=GrammarErrorType.MAIN_CLAUSE_V2,
            message=GRAMMAR_MESSAGES["main_clause_v2"]["ERROR"],
            spans=wrong_verb,
            blocking=False,
            priority=ERROR_PRIORITY[GrammarErrorType.MAIN_CLAUSE_V2],
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
    (passed_test, verb_index) = _violates_subordinate_verb_final(doc)
    if not passed_test:
        return []

    return [
        GrammarResult(
            error_type=GrammarErrorType.SUBORDINATE_VERB_FINAL,
            message=GRAMMAR_MESSAGES["subordinate_verb_final"]["ERROR"],
            blocking=False,
            priority=ERROR_PRIORITY[GrammarErrorType.SUBORDINATE_VERB_FINAL],
            spans=[verb_index]
        )
    ]

def _violates_subordinate_verb_final(doc):
    sent = list(doc.sents)[0]
    verb_index = -1
    subordinate_verb = None
    for token in sent:
         if token.pos_ in ["VERB", "AUX"]:
            temp_children = list(token.children)
            if any(t.pos_ == "SCONJ" for t in temp_children):
                subordinate_verb = token
                verb_index = int(token.i)
    
    if subordinate_verb:
        subordinate_verb_tree = list(subordinate_verb.subtree)
        return ((subordinate_verb_tree[-1] != subordinate_verb), verb_index)

    return (False, verb_index)

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
        u_error_type = u_token.morph.get('Pronerror_type')
        t_error_type = t_token.morph.get('Pronerror_type')

        # Only compare tokens of the same pronoun error_type
        if u_error_type == t_error_type:
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
                    spans=[u_token.i],
                    details={
                        "user_pronoun": u_token.text,
                        "target_pronoun": t_token.text,
                        "user_case": u_case,
                        "target_case": t_case
                    },
                    blocking=False,
                    priority=ERROR_PRIORITY[GrammarErrorType.ACCUSATIVE_DATIVE],
                ))

    return results

def check_extra_words(user_doc, target_doc, protected_spans):
    results = []

    target_words = {
        t.text.lower()
        for t in target_doc
        if t.is_alpha
    }

    for token in user_doc:
        if not token.is_alpha:
            continue

        if token.i in protected_spans:
            continue  # already explained elsewhere

        if token.text.lower() not in target_words:
            results.append(
                GrammarResult(
                    error_type=GrammarErrorType.WORD_OUT_OF_TARGET,
                    message=f"Extra word '{token.text}' not in target sentence",
                    spans=[token.i],
                    priority=90,
                    blocking=False
                )
            )

    return results


def final_word_check(user_doc, target_doc, max_mismatch=1):
    user_tokens = [t.text.lower() for t in user_doc if t.is_alpha]
    target_tokens = [t.text.lower() for t in target_doc if t.is_alpha]

    mismatches = sum(1 for u, t in zip(user_tokens, target_tokens) if u != t)
    extra_tokens = abs(len(user_tokens) - len(target_tokens))

    if mismatches + extra_tokens > max_mismatch:
        return True
    return False

def resolve_conflicts(results):
    best_by_span = {}

    for r in results:
        if not r.spans:
            continue

        for span in r.spans:
            existing = best_by_span.get(span)
            if existing is None or r.priority > existing.priority:
                best_by_span[span] = r

    resolved = []
    seen = set()

    # Add span-based results (deduped)
    for r in best_by_span.values():
        if id(r) not in seen:
            resolved.append(r)
            seen.add(id(r))

    # Add sentence-level results (spans=None)
    for r in results:
        if r.spans is None:
            resolved.append(r)

    return sorted(
        resolved,
        key=lambda r: (-r.priority, r.spans[0] if r.spans else -1)
    )
