# Problem:
Writing is a critical but underdeveloped skill in second-language learning. While learners can easily consume spoken and written content online, producing correct written language is significantly harder because it requires active recall and detailed feedback. Most beginner and intermediate learners lack access to native speakers or large communities that can correct their writing consistently. Existing platforms such as Duolingo and Rosetta Stone are costly for dedicated users and provide limited to no feedback on written mistakes. As a result, learners frequently repeat errors without understanding why they are wrong. There is a clear gap for an accessible tool that provides targeted, explanatory feedback on written language production.


# My solution
1. The user is presented with an English sentence prompt.
2. The user writes a German translation (1–2 sentences).
3. The system evaluates the response for:
   - Meaning equivalence with the target sentence
   - Grammar errors
4. The system returns:
   - Whether the intended meaning was conveyed
   - Grammar explanations in English
   - A corrected German sentence
5. The user proceeds to the next prompt.
## Scope

| In Scope                              | Out of Scope              |
|--------------------------------------|---------------------------|
| Fixed prompt dataset (50–100 prompts) | User accounts             |
| Rule-based grammar error detection    | Spaced repetition         |
| AI-generated explanations             | Adaptive difficulty       |
| Web interface                         | Audio / speech            |
| Public deployment                    | Points or gamification    |


## Assesed Grammar
## Targeted Grammar Concepts

The system evaluates a fixed set of German grammar concepts that are both common sources of learner error:

1. Perfekt auxiliary verbs (sein vs. haben)
2. Verb position in main clauses (V2)
3. Verb position in subordinate clauses (verb-final)
4. Capitalization of nouns
5. Accusative vs. dative case after common prepositions

## Prompt Dataset
Each prompt is designed to test a single grammatical concept and has one canonical German reference answer. Prompts are fixed rather than generated dynamically to ensure consistency, control evaluation difficulty, and reduce ambiguity.

Each prompt follows this schema:

```json
{
  "id": 27,
  "english_prompt": "She stayed at home because she was sick.",
  "target_german": "Sie ist zu Hause geblieben, weil sie krank war.",
  "grammar_focus": "Verb_Subordinate"
}
```

## Success Criteria

The project is considered complete when all of the following are true:

1. The application is publicly deployed and accessible.
2. A user can complete at least 10 prompts end-to-end.
3. Grammar errors are detected and accompanied by clear English explanations.
