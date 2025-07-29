import React, { useState } from "react";

function EmailAnalyzer() {
  const [content, setContent] = useState("");
  const [result, setResult] = useState(null);

  const analyze = async () => {
    const res = await fetch("/analyze/email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    const data = await res.json();
    setResult(data);
  };

  return (
    <div>
      <h2>Email Analyzer</h2>
      <textarea
        rows={5}
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Paste email content..."
      />
      <button onClick={analyze}>Analyze</button>
      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </div>
  );
}

export default EmailAnalyzer;
