import React, { useEffect, useState } from "react";
import axios from "axios";

function GmailAnalyzer() {
  const [emails, setEmails] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios
      .get("http://localhost:8000/analyze/gmail")
      .then((res) => {
        setEmails(res.data.emails || []);
      })
      .catch((err) => {
        console.error(err);
        setError("Failed to fetch Gmail messages.");
      });
  }, []);

  const handlePrev = () => {
    if (currentIndex > 0) setCurrentIndex(currentIndex - 1);
  };

  const handleNext = () => {
    if (currentIndex < emails.length - 1) setCurrentIndex(currentIndex + 1);
  };

  const renderAttachment = (att, index) => {
    const mime = att.mime_type;
    const base64Url = `data:${mime};base64,${att.data_base64}`;

    return (
      <li key={index}>
        <strong>{att.filename}</strong> ({mime})
        <div style={{ margin: "10px 0" }}>
          {mime === "application/pdf" ? (
            <iframe
              src={base64Url}
              title={att.filename}
              width="100%"
              height="400px"
              style={{ border: "1px solid #ccc" }}
            />
          ) : mime.startsWith("image/") ? (
            <img
              src={base64Url}
              alt={att.filename}
              style={{
                maxWidth: "300px",
                display: "block",
                marginBottom: "10px",
                border: "1px solid #ccc",
              }}
            />
          ) : mime.startsWith("text/") ? (
            <pre
              style={{
                background: "#f9f9f9",
                padding: "10px",
                maxHeight: "200px",
                overflowY: "auto",
              }}
            >
              {atob(att.data_base64)}
            </pre>
          ) : (
            <p>Unsupported file type for preview.</p>
          )}
        </div>
        <a href={base64Url} download={att.filename}>
          ⬇️ Download
        </a>
      </li>
    );
  };

  const currentEmail = emails[currentIndex];

  return (
    <div>
      <h2>📧 Gmail Analyzer</h2>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {emails.length === 0 ? (
        <p>Loading emails...</p>
      ) : (
        <div>
          <p>
            <strong>From:</strong> {currentEmail.metadata?.from}
            <br />
            <strong>To:</strong> {currentEmail.metadata?.to}
            <br />
            <strong>Subject:</strong> {currentEmail.metadata?.subject}
            <br />
            <strong>Date:</strong> {currentEmail.metadata?.date}
          </p>

          <div style={{ border: "1px solid #ddd", padding: "10px", marginBottom: "20px" }}>
            {typeof currentEmail.body === "string" ? (
              <div dangerouslySetInnerHTML={{ __html: currentEmail.body }} />
            ) : (
              <pre style={{ fontStyle: "italic" }}>
                {currentEmail.body ? JSON.stringify(currentEmail.body, null, 2) : "No content"}
              </pre>
            )}
          </div>

          {currentEmail.attachments && currentEmail.attachments.length > 0 && (
            <>
              <h3>📎 Attachments</h3>
              <ul>{currentEmail.attachments.map(renderAttachment)}</ul>
            </>
          )}

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <button onClick={handlePrev} disabled={currentIndex === 0}>
              &lt;
            </button>
            <span>
              {currentIndex + 1} of {emails.length}
            </span>
            <button onClick={handleNext} disabled={currentIndex === emails.length - 1}>
              &gt;
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default GmailAnalyzer;
