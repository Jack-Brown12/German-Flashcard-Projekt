import { useEffect, useState, useRef } from "react";
import "./FeedbackModal.css";
import AnnotatedSentence from "./AnnotatedSentence.jsx";

function FeedbackModal({ evaluation, onClose }) {
  const [activeErrorIndex, setActiveErrorIndex] = useState(null);
  const hasPlayedSound = useRef(false);

  // Safety check to prevent crashing if evaluation is null
  if (!evaluation) return null;

// Shortcut lets users press enter instead of clicking "continue"
 useEffect(() => {
   const handleKeyDown = (e) => {
     if (e.key === "Enter") {
       e.preventDefault();
       onClose();
     }
   };
   window.addEventListener("keydown", handleKeyDown);
   return () => window.removeEventListener("keydown", handleKeyDown);
 }, [onClose]);


 const encouragements = evaluation.errors.filter((e) => e.type === "near_miss");
 const realErrors = evaluation.errors.filter((e) => e.type !== "near_miss");


 const hasBlocking = realErrors.some((e) => e.blocking);
 const hasErrors = realErrors.length > 0;


 let status = "correct";
 if (hasBlocking) status = "blocking";
 else if (hasErrors) status = "warning";


 const nounCaps = realErrors.filter((e) => e.type === "noun_capitalization");
 const otherErrors = realErrors.filter((e) => e.type !== "noun_capitalization");


  // Nouns are given as separate errors. This groups all nouns into one clickable error
 const groupedErrors = [];
 if (nounCaps.length > 0) {
   groupedErrors.push({
     message: "In German, nouns must be capitalized.",
     spans: nounCaps.flatMap((e) => e.spans || []),
     blocking: nounCaps.some((e) => e.blocking),
   });
 }
 groupedErrors.push(...otherErrors);

// Turns highlights on/off
 const handleErrorClick = (index) => {
   if (status !== "blocking") {
     setActiveErrorIndex((prev) => (prev === index ? null : index));
   }
 };


 const activeSpans =
   activeErrorIndex !== null ? groupedErrors[activeErrorIndex]?.spans ?? [] : [];


 // Initial spacing based on number of errors
 const errorCount = groupedErrors.length + encouragements.length;
 let sheetHeightVh = 25;
 if (errorCount >= 1) sheetHeightVh = 35;
 if (errorCount >= 2) sheetHeightVh = 45;
 if (errorCount >= 4) sheetHeightVh = 55;
 sheetHeightVh = Math.min(sheetHeightVh, 85);


 return (
   <>
     <div className="modal-backdrop" onClick={onClose} />


     <div className={`bottom-sheet ${status}`} style={{ height: `${sheetHeightVh}vh` }}>
       <div className="sheet-handle" />


       <div className="sheet-main-layout">
         <div className="content-left">
           <h2>{evaluation.meaning_conveyed ? "Correct!" : "Needs work"}</h2>


           <div className="correct-sentence">
             <strong>Correct Answer: </strong>
             {evaluation.correct_sentence}
           </div>


           <div className="user-sentence-line">
             <strong>Your sentence: </strong>
             <AnnotatedSentence
               tokens={evaluation.tokens || []}
               highlightedIndices={activeSpans}
               blocking={hasBlocking}
             />
           </div>


          {hasErrors && (
            <>
              <h2>Issues {status !== "blocking" && "(click to toggle highlights)"}</h2>

              <ul style={{ listStyleType: "none", padding: 0, margin: 0 }}>
                {groupedErrors.map((e, i) => {
                  // BLOCKING MODE (No indexed errors)
                  if (status === "blocking") {
                    return (
                      <li key={i} style={{ marginBottom: "6px", lineHeight: "1.4" }}>
                        {e.message}
                      </li>
                    );
                  }

                  // Issues mode (With Bold Numbers)
                  return (
                    <li
                      key={i}
                      onClick={() => handleErrorClick(i)}
                      className={activeErrorIndex === i ? "active-issue" : ""}
                      style={{
                        cursor: "pointer",
                        marginBottom: "8px",
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "10px",
                      }}
                    >
                      <strong style={{ fontWeight: "900", color: "inherit", whiteSpace: "nowrap" }}>
                        [{i + 1}]
                      </strong>
                      <span className="error-text">{e.message}</span>
                    </li>
                  );
                })}
              </ul>
            </>
          )}


          {encouragements.length > 0 && (
            <div style={{ marginTop: "16px" }}>
              <h2>Feedback</h2>

              <ul style={{ listStyleType: "none", padding: 0, margin: 0 }}>
                {encouragements.map((e, i) => (
                  <li
                    key={i}
                    style={{
                      marginBottom: "4px",
                      fontSize: "1rem",
                      lineHeight: "1.4",
                      fontWeight: "500", // Slightly heavier than normal text but not as bold as the title
                    }}
                  >
                    {e.message}
                  </li>
                ))}
              </ul>
            </div>
          )}
         </div>
          {/* continue button */}
          <button className="continue-btn" onClick={onClose}>
            Continue
          </button>
       </div>
     </div>
   </>
 );
}


export default FeedbackModal;
