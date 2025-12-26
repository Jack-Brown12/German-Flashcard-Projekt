import sys
import types

import pytest

# Stub spacy.load to avoid requiring the German model during import.
import spacy
def _dummy_spacy_load(name):
	# Return a callable that won't be used by our tests (we build FakeDocs manually).
	class DummyNLP:
		def __call__(self, text):
			return None
	return DummyNLP()

spacy.load = _dummy_spacy_load

# Now import the module under test.
from app import evaluator


### --- Helpers: lightweight fake tokens/docs used by tests ---

class MorphFake:
	def __init__(self, mapping=None):
		self._m = mapping or {}

	def __contains__(self, item):
		# Support checks like "VerbForm=Fin" and membership checks
		if '=' in item:
			k, v = item.split('=', 1)
			val = self._m.get(k)
			if isinstance(val, (list, tuple)):
				return v in val
			return val == v
		# fallback: check values
		return item in self._m.values()

	def get(self, key, default=None):
		return self._m.get(key, default)


class TokenFake:
	def __init__(self, text, pos_, dep_='', tag_='', lemma_='', morph=None, i=0, is_oov=False, is_alpha=True, is_punct=False, children=None):
		self.text = text
		self.pos_ = pos_
		self.dep_ = dep_
		self.tag_ = tag_
		self.lemma_ = lemma_
		self.morph = morph or MorphFake({})
		self.i = i
		self.is_oov = is_oov
		self.is_alpha = is_alpha
		self.is_punct = is_punct
		# By default a token's head is itself (root-like). Tests will reassign when needed.
		self.head = self
		self.children = children or []
		self.subtree = [self]

	def __str__(self):
		return self.text

class FakeSent:
	def __init__(self, tokens, start=0, root_idx=0):
		self._tokens = tokens
		self.start = start
		self.root = tokens[root_idx]

	def __iter__(self):
		return iter(self._tokens)


class FakeDoc:
	def __init__(self, tokens, sent_start=0, root_idx=0):
		self._tokens = tokens
		self._sent = FakeSent(tokens, start=sent_start, root_idx=root_idx)

	def __iter__(self):
		return iter(self._tokens)

	@property
	def sents(self):
		return [self._sent]


def link_head(child, head):
	child.head = head


def set_subtree(token, subtree_list):
	token.subtree = subtree_list


### --- Tests ---

def test_check_noun_capitalization_detects_uncapitalized_nouns():
	t1 = TokenFake('Hund', pos_='NOUN', i=0)
	t2 = TokenFake('haus', pos_='NOUN', i=1)
	doc = FakeDoc([t1, t2])

	res = evaluator.check_noun_capitalization(doc)
	# returns a list of GrammarResult; details contains the list of uncapitalized nouns
	assert isinstance(res, list)
	assert len(res) == 1
	assert 'haus' in res[0].details


def test_check_perfekt_auxiliary_detects_wrong_auxiliary_for_sein_verbs():
	# Past participle token
	past = TokenFake('gegangen', pos_='VERB', tag_='VVPP', lemma_='gehen', i=1)
	# Auxiliary 'haben' used incorrectly for a sein-verb
	aux_haben = TokenFake('hat', pos_='AUX', tag_='VAFIN', lemma_='haben', i=0)
	doc_wrong = FakeDoc([aux_haben, past])

	res_wrong = evaluator.check_perfekt_auxiliary(doc_wrong)
	assert isinstance(res_wrong, list)
	assert len(res_wrong) == 1
	assert res_wrong[0].details == 'SEIN_ERROR'

	# Correct auxiliary 'sein' for gehen
	aux_sein = TokenFake('ist', pos_='AUX', tag_='VAFIN', lemma_='sein', i=0)
	doc_correct = FakeDoc([aux_sein, past])
	res_correct = evaluator.check_perfekt_auxiliary(doc_correct)
	# should return empty list when no violation
	assert res_correct == []


def test_check_main_clause_v2_identifies_v2_and_v1_cases():

	# Create subject first, then root that lists the subject as a child
	subj = TokenFake('Er', pos_='PRON', dep_="sb", i=0, children=[])
	root = TokenFake('geht', pos_='VERB', dep_='root', tag_='', lemma_='gehen', morph=MorphFake({'VerbForm': 'Fin'}), i=1, children=[subj])

	# Make subject's head point to root (single constituent before root)
	link_head(subj, root)

	# root.head should be itself
	link_head(root, root)

	doc = FakeDoc([subj, root], sent_start=0, root_idx=1)
	# returns [] when no violation
	assert not evaluator.check_main_clause_v2(doc)

	# If root is not finite V2 doesn't apply. The conjugation is just wrong
	not_finite_root = TokenFake('gehen', pos_='VERB', morph=MorphFake({'VerbForm': 'Inf'}), i=0)
	doc_bad = FakeDoc([not_finite_root], sent_start=0, root_idx=0)
	assert not evaluator.check_main_clause_v2(doc_bad)

	# Final check. The root is not in 2nd position but there is a single constituent before it
	adverb = TokenFake('Gestern', pos_='ADV', i=0)
	subj.i = 1
	root.i = 2
	doc_bad = FakeDoc([adverb, subj, root], sent_start=0, root_idx=2)
	# now should report a violation (non-empty list)
	assert evaluator.check_main_clause_v2(doc_bad)


def test_check_subordinate_verb_final_true_and_false():
	"""Three clearer cases for subordinate verb-final checking:
	1) Proper subordinate clause: verb is last in its subtree -> returns False (no violation)
	2) Violation: subordinate verb is not last in its subtree -> returns True
	3) No subordinate clause present -> returns False
	"""

	# Case 1: proper subordinate clause (verb is last in its subtree)
	sconj = TokenFake('dass', pos_='SCONJ', i=0)
	subj = TokenFake('er', pos_='PRON', i=1)
	verb = TokenFake('kommt', pos_='VERB', i=2, morph=MorphFake({'VerbForm': 'Fin'}))
	set_subtree(verb, [sconj, subj, verb])
	
	doc_proper = FakeDoc(
		[TokenFake('Ich', pos_='PRON', i=0), sconj, subj, verb], 
		sent_start=0, 
		root_idx=3
	)
	# no violation -> empty list
	assert not evaluator.check_subordinate_verb_final(doc_proper)

	# Case 2: subordinate verb appears but is NOT last in its subtree -> violation
	obj = TokenFake('heute', pos_='ADV', i=4)
	# make verb in middle of its subtree
	set_subtree(verb, [sconj, verb, obj])
	
	subject_verb = TokenFake('kenne', pos_='VERB', i=1, morph=MorphFake({'VerbForm': 'Fin'}))

	doc_violation = FakeDoc(
		[TokenFake('Ich', pos_='PRON', i=0), subject_verb, sconj, subj, verb, obj],
		sent_start=0, 
		root_idx=4
	)
	assert evaluator.check_subordinate_verb_final(doc_violation)

	# Case 3: no subordinate conjunction in any verb subtree -> should return False
	linear_verb = TokenFake('läuft', pos_='VERB', i=0, morph=MorphFake({'VerbForm': 'Fin'}))
	set_subtree(linear_verb, [linear_verb])
	doc_no_sub = FakeDoc(
		[TokenFake('Er', pos_='PRON', i=0), linear_verb], 
		sent_start=0, 
		root_idx=1
	)
	assert not evaluator.check_subordinate_verb_final(doc_no_sub)


def test_check_accusative_dative_prepositions_reports_case_mismatches():
	# User uses dative pronoun "ihm", target expects accusative "ihn"
	user_pron = TokenFake('ihm', pos_='PRON', i=0, morph=MorphFake({'PronType': 'Prs', 'Case': 'Dat'}))
	target_pron = TokenFake('ihn', pos_='PRON', i=0, morph=MorphFake({'PronType': 'Prs', 'Case': 'Acc'}))

	user_doc = FakeDoc([user_pron])
	target_doc = FakeDoc([target_pron])

	errs = evaluator.check_accusative_dative_prepositions(user_doc, target_doc)
	assert len(errs) == 1
	err = errs[0]
	# details is a dict with the expected keys
	assert err.details['user_pronoun'] == 'ihm'
	assert err.details['target_pronoun'] == 'ihn'
	assert err.details['user_case'] == 'Dat'
	assert err.details['target_case'] == 'Acc'


## Integration tests (uses Spacy model which significantly slows processing time)


def _get_real_nlp_or_skip():
	"""Try to reload spaCy and load the German model; skip tests if unavailable."""
	import importlib
	import spacy as _spacy

	importlib.reload(_spacy)
	try:
		nlp = _spacy.load("de_core_news_md")
		return nlp
	except Exception:
		pytest.skip("spaCy German model `de_core_news_md` not available; skipping integration test")

def test_integration_check_noun_capitalization():
	nlp = _get_real_nlp_or_skip()
	doc = nlp("Ich spiele videospiele und basketball")
	res = evaluator.check_noun_capitalization(doc)
	assert len(res) == 1
	# details should include the two uncapitalized nouns
	assert 'videospiele' in res[0].details
	assert 'basketball' in res[0].details

def test_integration_perfekt_auxiliary_correct():
	nlp = _get_real_nlp_or_skip()
	doc = nlp("Ich bin gestern nach Hause gegangen.")
	assert evaluator.check_perfekt_auxiliary(doc) == []


def test_integration_perfekt_auxiliary_incorrect():
	nlp = _get_real_nlp_or_skip()
	doc = nlp("Ich habe gestern nach Hause gegangen.")
	res = evaluator.check_perfekt_auxiliary(doc)
	assert len(res) == 1
	assert res[0].details == "SEIN_ERROR"


def test_integration_main_clause_v2():
	nlp = _get_real_nlp_or_skip()
	doc = nlp("Heute ich lerne Deutsch.")
	assert evaluator.check_main_clause_v2(doc)


def test_integration_subordinate_verb_final():
	nlp = _get_real_nlp_or_skip()
	doc = nlp("Ich weiß, dass er morgen kommt.")
	assert not evaluator.check_subordinate_verb_final(doc)


def test_integration_accusative_vs_dative_preposition():
	nlp = _get_real_nlp_or_skip()
	user_doc = nlp("Er legt das Buch auf dem Tisch.")
	target_doc = nlp("Er legt das Buch auf den Tisch.")
	errs = evaluator.check_accusative_dative_prepositions(user_doc, target_doc)
	# We expect at least one case mismatch (dem vs den)
	assert len(errs) >= 1


def test_end_to_end_evaluate_translation_with_real_spacy():
	"""End-to-end: load real spaCy, reload evaluator so it binds the real nlp,
	then run evaluate_translation and confirm we get a Perfekt auxiliary error.
	If the model isn't available, skip the test.
	"""
	import importlib
	_spacy = importlib.reload(spacy)
	try:
		real_nlp = _spacy.load("de_core_news_md")
	except Exception:
		pytest.skip("spaCy German model `de_core_news_md` not available; skipping e2e test")


	# reload the evaluator module so its top-level `nlp` and `spell` are bound to
	# the real spaCy model and real SpellChecker implementation
	import app.evaluator as evaluator_module
	importlib.reload(evaluator_module)

	user = "Ich habe gestern nach Hause gegangen."
	target = "Ich bin gestern nach Hause gegangen."
	res = evaluator_module.evaluate_translation(user, target, grammar_focus='')
	# should return at least one GrammarResult; expect a PERFEKT_AUXILIARY among them
	assert isinstance(res, list)
	assert any(r.error_type == evaluator_module.GrammarErrorType.PERFEKT_AUXILIARY for r in res)

