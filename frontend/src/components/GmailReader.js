import React, { useEffect, useState } from "react";

function GmailAnalyzer() {
  const [emails, setEmails] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("http://localhost:8000/analyze/gmail")
      .then((res) => res.json())
      .then((data) => {
        setEmails(data.emails || []);
        setCurrentIndex(0);
      })
      .catch((err) => {
        console.error(err);
        setError("Failed to fetch Gmail messages.");
      });
  }, []);

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : prev));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev < emails.length - 1 ? prev + 1 : prev));
  };

  const currentEmail = emails[currentIndex];

  return (
    <div>
      <h2>📧 Gmail Analyzer</h2>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {emails.length > 0 ? (
        <div>
          <div style={{ marginBottom: "10px" }}>
            <strong>From:</strong> {currentEmail.from} <br />
            <strong>To:</strong> {currentEmail.to} <br />
            <strong>Subject:</strong> {currentEmail.subject} <br />
            <strong>Date:</strong> {currentEmail.date}
          </div>

          {/* ✅ Renders the actual HTML email body */}
          <div
            style={{
              border: "1px solid #ccc",
              padding: "10px",
              borderRadius: "5px",
              background: "#fff",
              overflow: "auto",
              maxHeight: "500px",
              marginBottom: "10px",
            }}
            dangerouslySetInnerHTML={{ __html: currentEmail.html }}
          />

          {/* Email navigation */}
          <div>
            <button onClick={handlePrev} disabled={currentIndex === 0}>
              &lt;
            </button>
            <span style={{ margin: "0 10px" }}>
              {currentIndex + 1} of {emails.length}
            </span>
            <button onClick={handleNext} disabled={currentIndex === emails.length - 1}>
              &gt;
            </button>
          </div>
        </div>
      ) : (
        <p>Loading emails...</p>
      )}
    </div>
  );
}

export default GmailAnalyzer;
