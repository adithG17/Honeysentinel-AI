import React, { useState } from "react";

function MessageAnalyzer() {
  const [message, setMessage] = useState("");
  const [result, setResult] = useState(null);

  const analyze = async () => {
const res = await fetch("http://127.0.0.1:8000/analyze/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    setResult(data);
  };

  return (
    <div>
      <h2>Message Analyzer</h2>
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type a message..."
      />
      <button onClick={analyze}>Analyze</button>
      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </div>
  );
}

export default MessageAnalyzer;
