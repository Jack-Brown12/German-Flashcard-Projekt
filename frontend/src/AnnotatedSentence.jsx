function AnnotatedSentence({ tokens, highlightedIndices = [], blocking = false }) {
  const indicesToHighlight = blocking
    ? tokens.map((_, i) => i)
    : highlightedIndices;

  return (
    <div style={{ lineHeight: "2em" }}>
      {tokens.map((token, idx) => {
        const isHighlighted = indicesToHighlight.includes(idx);
        const isPunctuation = /^[.,!?;:]+$/.test(token);

        return (
          <span
            key={idx}
            style={{
              marginLeft: idx === 0 || isPunctuation ? 0 : "0.25em",
              backgroundColor: isHighlighted
                ? blocking
                  ? "rgba(255, 0, 0, 0.25)" // Red for blocking
                  : "rgba(255, 230, 0, 0.6)" // Yellow for warning
                : "transparent",
              borderRadius: "4px", // smooths out the highlight blocks
              padding: "2px 0"
            }}
          >
            {token}
          </span>
        );
      })}
    </div>
  );
}

export default AnnotatedSentence