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
      <ul>
        {emails.length > 0 ? (
          emails.map((email, idx) => (
            <li key={idx} style={{ marginBottom: "10px" }}>
              {email}
            </li>
          ))
        ) : (
          <p>Loading emails...</p>
        )}
      </ul>
    </div>
  );
}

export default GmailReader;
