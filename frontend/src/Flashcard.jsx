function Flashcard({ card }) {
  if (!card) {
    return <p>Loading...</p>;
  }
  // basic flashcard model
  return (
    <div className="card flashcard-card">
      <h2>Flashcard #{card.flashcard_id}</h2>
      <p><em>Prompt: {card.english_prompt}</em></p>
    </div>
  );
}

export default Flashcard;
