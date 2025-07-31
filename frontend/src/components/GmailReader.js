import React, { useEffect, useState } from "react";
import axios from "axios";

function GmailReader() {
  const [emails, setEmails] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios
      .get("http://localhost:8000/analyze/gmail")
      .then((res) => {
        setEmails(res.data.emails);
      })
      .catch((err) => {
        console.error(err);
        setError("Failed to fetch emails.");
      });
  }, []);

  return (
    <div>
      <h2>📬 Latest Gmail Snippets</h2>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {emails.length > 0 ? (
        emails.map((email, idx) => (
          <div
            key={idx}
            dangerouslySetInnerHTML={{ __html: email.html }}
            style={{
              border: "1px solid #ccc",
              margin: "10px 0",
              padding: "10px",
              background: "#fff",
              borderRadius: "6px",
              overflowX: "auto",
            }}
          />
        ))
      ) : (
        <p>Loading emails...</p>
      )}
    </div>
  );
}

export default GmailReader;
