import { useState, useEffect, useRef } from "react"
import Flashcard from "./Flashcard.jsx"
import FlashcardNav from "./FlashcardNav.jsx"
import FeedbackModal from "./FeedbackModal.jsx"
import api from "./api"

function App() {
  const [allCards, setAllCards] = useState([]);
  const [totalCards, setTotalCards] = useState(0);
  const [number, setNumber] = useState(1);
  const [card, setCard] = useState(null);
  const [answer, setAnswer] = useState("");
  const [evaluation, setEvaluation] = useState(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const inputRef = useRef(null);

  // Fetchs everything once on load
  useEffect(() => {
    const fetchAllData = async () => {
      try {
        const res = await api.get("/flashcards");
        const cards = res.data;
        setAllCards(cards);
        setTotalCards(cards.length);
        
        // Set the initial card immediately
        if (cards.length > 0) {
          setCard(cards[0]);
        }
      } catch (err) {
        console.error("Failed to fetch cards:", err);
      }
    };
    fetchAllData();
  }, []);

 
  useEffect(() => {
    if (allCards.length > 0) {
      
      setCard(allCards[number - 1]);
      
      setAnswer("");
      setEvaluation(null);
      setIsSubmitted(false);
      setIsSubmitting(false);

      // Focus input
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [number, allCards]);

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

    if (wasCorrect) {
      setNumber((n) => Math.min(n + 1, totalCards));
    }

    requestAnimationFrame(() => inputRef.current?.focus());
  };

  return (
    <div className="app">
      {/* Show card if loaded, otherwise a simple loading state */}
      {card ? (
        <Flashcard card={card} />
      ) : (
        <div className="loading-state">Loading Flashcards...</div>
      )}

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
              // Move to next card on Enter if already submitted
              setNumber((n) => Math.min(n + 1, totalCards));
            } else {
              handleSubmit();
            }
          }
        }}
        placeholder="Type your answer"
      />

      <button
        className="primary-btn"
        disabled={!answer.trim() || !card || isSubmitting || isSubmitted}
        onClick={handleSubmit}
      >
        {isSubmitting ? "Checking..." : "Check"}
      </button>

      {totalCards > 0 && (
        <FlashcardNav
          totalCards={totalCards}
          number={number}
          setNumber={setNumber}
        />
      )}

      {evaluation && (
        <FeedbackModal evaluation={evaluation} onClose={handleCloseFeedback} />
      )}
    </div>
  );
}

export default App;