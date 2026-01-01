

function LandingPage({ onStart }) {
  return (
   <div className="landing">

  {/* Everything else stays in the flex container */}
  <div className="content-container">

    <div className="flag-bg-strip"></div>

    <div className="title-text">
      <h1>Jack's German Projekt</h1>
    </div>
    

    <div className="landing-card">
      <h1>German Grammar Trainer</h1>
      <p>Practice real sentences. Get precise feedback.</p>
      <button className="start-btn" onClick={onStart}>Start</button>
    </div>
  </div>
</div>
  );
}

export default LandingPage;
