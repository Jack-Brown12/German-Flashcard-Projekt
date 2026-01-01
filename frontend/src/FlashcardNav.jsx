import { useState } from "react"

function FlashcardNav({ totalCards, number, setNumber }) {
  const [inputValue, setInputValue] = useState("")

  const commitValue = () => {
    const value = Number(inputValue)
    if (value >= 1 && value <= totalCards) {
      setNumber(value)
    }
    setInputValue("")
  }

  return (
  <div className="flashcard-nav-wrapper">
    <div className="flashcard-nav">
      <button onClick={() => setNumber(n => (n === 1 ? totalCards : n - 1))}>
        Previous
      </button>

      <input
        type="text"
        inputMode="numeric"
        placeholder={`1–${totalCards}`}
        value={inputValue}
        //Filters input, accepts only digits
        onChange={e => {
          if (/^\d*$/.test(e.target.value)) {
            setInputValue(e.target.value)
          }
        }}
        onKeyDown={e => {
          if (e.key === "Enter") {
            e.preventDefault()
            commitValue()
          }
        }}
        onBlur={commitValue}
      />

      <button onClick={() => setNumber(n => (n === totalCards ? 1 : n + 1))}>
        Next
      </button>
    </div>
  </div>
)
}

export default FlashcardNav
