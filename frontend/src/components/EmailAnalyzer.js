import React, { useState } from "react";

function EmailAnalyzer() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError("");
    setResult(null);
  };

  const handleAnalyze = async () => {
    if (!file) {
      setError("Please upload a .eml or .msg file first.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/analyze/email", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        setError("Failed to analyze email: " + JSON.stringify(errData));
        return;
      }

      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError("An error occurred while analyzing the email.");
    }
  };

  return (
    <div>
      <h2>📧 Email Analyzer</h2>
      <p>
        Upload a `.eml` or `.msg` file to analyze its content and detect honeytrap risks.
        <br />
        <strong>How to download a .eml file:</strong> Open an email in your email app or webmail → More Options → Download (.eml).
      </p>

      <input type="file" accept=".eml,.msg" onChange={handleFileChange} />
      <br />
      <button onClick={handleAnalyze} style={{ marginTop: "10px" }}>
        Analyze Email
      </button>

      {error && <p style={{ color: "red" }}>{error}</p>}
      {result && (
        <div style={{ marginTop: "10px" }}>
          <strong>Result:</strong>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default EmailAnalyzer;
