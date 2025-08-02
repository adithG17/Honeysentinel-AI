import React, { useState } from "react";

function EmailAnalyzer() {
  const [file, setFile] = useState(null);
  const [emailData, setEmailData] = useState(null);
  const [error, setError] = useState("");

  const analyze = async () => {
    if (!file) {
      setError("Please choose a file.");
      return;
    }
    setError("");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/analyze/email", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Failed to analyze");

      const data = await res.json();
      setEmailData(data);
    } catch (err) {
      setError("Failed to analyze email.");
      console.error(err);
    }
  };

  return (
    <div>
      <h2>📧 Email Analyzer</h2>
      <p>
        Upload a <code>.eml</code> or <code>.msg</code> file to analyze its
        content and detect honeytrap risks. <br />
        <strong>How to download a .eml file:</strong> Open an email in your
        email app or webmail → More Options → Download (.eml).
      </p>

      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={analyze}>Analyze Email</button>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {emailData && (
        <div style={{ marginTop: "20px" }}>
          <h4>📨 Preview</h4>
          <p>
            <strong>From:</strong> {emailData.from}
            <br />
            <strong>To:</strong> {emailData.to}
            <br />
            <strong>Subject:</strong> {emailData.subject}
            <br />
            <strong>Date:</strong> {emailData.date}
          </p>

          <h4>🧠 Risk Score</h4>
          <pre>{JSON.stringify(emailData.risk_score, null, 2)}</pre>

          <h4>📄 Email Content</h4>
          <div
            style={{ border: "1px solid #ccc", padding: "10px" }}
            dangerouslySetInnerHTML={{ __html: emailData.html }}
          />
        </div>
      )}
    </div>
  );
}

export default EmailAnalyzer;
