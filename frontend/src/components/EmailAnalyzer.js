import React, { useState } from "react";

export default function EmailAnalyzer() {
  const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";
  const [file, setFile] = useState(null);
  const [data, setData] = useState(null); // parsed response
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (e) => {
    setError("");
    setData(null);
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    setFile(f);
  };

  const handleAnalyze = async () => {
    setError("");
    setData(null);

    if (!file) {
      setError("Please select a .eml or .msg file first.");
      return;
    }

    const name = (file.name || "").toLowerCase();
    if (!name.endsWith(".eml") && !name.endsWith(".msg")) {
      setError("Only .eml and .msg files are supported.");
      return;
    }

    const form = new FormData();
    form.append("file", file);

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/analyze/email`, {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        // try to show useful backend message
        let text;
        try {
          text = await res.text();
        } catch (e) {
          text = `HTTP ${res.status} ${res.statusText}`;
        }
        throw new Error(text || `HTTP ${res.status}`);
      }

      // parse JSON response safely
      let json;
      try {
        json = await res.json();
      } catch (e) {
        throw new Error("Backend returned invalid JSON.");
      }

      // normalize possible response keys
      const html =
        json.html ??
        json.html_body ??
        json.body ??
        json.text ??
        json.text_body ??
        "";
      setData({
        from: json.from ?? json.sender ?? "",
        to: json.to ?? "",
        subject: json.subject ?? "",
        date: json.date ?? "",
        html,
        raw: json,
      });
    } catch (err) {
      console.error("Analyze error:", err);
      setError(String(err.message || err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 16 }}>
      <h2>📧 Email Analyzer</h2>

      <p>
        Upload <code>.eml</code> or <code>.msg</code> files. HTML will be rendered
        below (dangerouslySetInnerHTML).
      </p>

      <input
        type="file"
        accept=".eml,.msg"
        onChange={handleFileChange}
        style={{ marginBottom: 8 }}
      />
      <div>
        <button onClick={handleAnalyze} disabled={loading}>
          {loading ? "Analyzing..." : "Analyze Email"}
        </button>
      </div>

      {error && (
        <div style={{ marginTop: 12, color: "crimson", whiteSpace: "pre-wrap" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {data && (
        <div style={{ marginTop: 16 }}>
          <h4>Metadata</h4>
          <div>
            <strong>From:</strong> {data.from || "—"}
            <br />
            <strong>To:</strong> {data.to || "—"}
            <br />
            <strong>Subject:</strong> {data.subject || "—"}
            <br />
            <strong>Date:</strong> {data.date || "—"}
          </div>

          <h4 style={{ marginTop: 12 }}>Email Body</h4>

          {/* If we have HTML, render it. Otherwise show plain text in a pre tag. */}
          {data.html ? (
            <div
              style={{
                border: "1px solid #ccc",
                padding: 12,
                borderRadius: 6,
                background: "#fff",
                color: "#000",
                marginTop: 8,
              }}
              dangerouslySetInnerHTML={{ __html: data.html }}
            />
          ) : (
            <pre
              style={{
                whiteSpace: "pre-wrap",
                border: "1px solid #ccc",
                padding: 12,
                borderRadius: 6,
                background: "#f7f7f7",
                color: "#000",
                marginTop: 8,
              }}
            >
              (no HTML content)
            </pre>
          )}

          <details style={{ marginTop: 12 }}>
            <summary>Raw backend response (for debugging)</summary>
            <pre style={{ whiteSpace: "pre-wrap" }}>
              {JSON.stringify(data.raw, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}
