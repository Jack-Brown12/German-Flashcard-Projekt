import { useState, useEffect, useRef } from "react"
import Flashcard from "./Flashcard.jsx"
import FlashcardNav from "./FlashcardNav.jsx"
import FeedbackModal from "./FeedbackModal.jsx"
import api from "./api"

function App() {
  const [totalCards, setTotalCards] = useState(0);
  const [number, setNumber] = useState(1);
  const [card, setCard] = useState(null);
  const [answer, setAnswer] = useState("");
  const [evaluation, setEvaluation] = useState(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const inputRef = useRef(null);

  // Fetch total cards on mount
  useEffect(() => {
    const fetchTotalCards = async () => {
      try {
        const res = await api.get("/flashcards"); // assuming returns array
        setTotalCards(res.data.length);
      } catch (err) {
        console.error("Failed to fetch total cards:", err);
      }
    };
    fetchTotalCards();
  }, []);

  // Fetch current flashcard whenever `number` changes
  useEffect(() => {
    const loadCard = async () => {
      setAnswer("");
      setEvaluation(null);
      setIsSubmitted(false);
      setIsSubmitting(false);

      try {
        const res = await api.get(`/flashcards/${number}`);
        setCard(res.data);

        // focus input after card loads
        requestAnimationFrame(() => inputRef.current?.focus());
      } catch (err) {
        console.error("Failed to fetch card:", err);
      }
    };
    if (totalCards > 0) {
      loadCard();
    }
  }, [number, totalCards]);

  const handleSubmit = async () => {
    if (!answer.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const res = await api.post("/evaluate", {
        user_german: answer,
        flashcard_id: number,
      });

      setEvaluation(res.data);
      setIsSubmitted(true);
    } catch (err) {
      console.error("Evaluation failed:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCloseFeedback = () => {
    const wasCorrect = evaluation?.meaning_conveyed;
    setEvaluation(null);
    setIsSubmitted(false);

    // increment flashcard number, but don't exceed totalCards
    if (wasCorrect) {
      setNumber((n) => Math.min(n + 1, totalCards));
    }

    // refocus input
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  return (
    <div className="app">
      {card && <Flashcard card={card} />}

      {/* User text bar */}
      <input
        ref={inputRef}
        className="answer-input"
        type="text"
        value={answer}
        disabled={isSubmitted}
        onChange={(e) => setAnswer(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            if (isSubmitted) {
              setNumber((n) => Math.min(n + 1, totalCards));
            } else {
              handleSubmit();
            }
          }
        }}
        placeholder="Type your answer"
      />

      {/* Submit button */}
      <button
        className="primary-btn"
        disabled={!answer.trim() || !card || isSubmitting || isSubmitted}
        onClick={handleSubmit}
      >
        {isSubmitting ? "Checking..." : "Check"}
      </button>

      {/* Flashcard search box */}
      {totalCards > 0 && (
        <FlashcardNav
          totalCards={totalCards}
          number={number}
          setNumber={setNumber}
        />
      )}

      {/* This is feedback display sourced from backend */}
      {evaluation && (
        <FeedbackModal evaluation={evaluation} onClose={handleCloseFeedback} />
      )}
    </div>
  );
}

export default App;
