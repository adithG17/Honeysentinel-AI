import React, { useEffect, useState } from "react";
import axios from "axios";

function GmailAnalyzer() {
  const [emails, setEmails] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    axios
      .get("http://localhost:8000/analyze/gmail")
      .then((res) => {
        setEmails(res.data.emails || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError("Failed to fetch Gmail messages.");
        setLoading(false);
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

  // For PDFs - use object tag with fallback
  if (mime === 'application/pdf') {
    return (
      <li key={index} style={{ marginBottom: "15px", padding: "10px", border: "1px solid #e0e0e0", borderRadius: "4px" }}>
        <strong>{att.filename}</strong> ({mime}, {Math.round(att.size / 1024)} KB)
        <div style={{ margin: "10px 0", height: "500px" }}>
          <object
            data={base64Url}
            type="application/pdf"
            width="100%"
            height="100%"
            style={{ border: "1px solid #ccc" }}
          >
            <p>Your browser doesn't support PDF preview. <a href={base64Url} download={att.filename}>Download instead</a></p>
          </object>
        </div>
        <a
          href={base64Url}
          download={att.filename}
          style={{
            color: "#0066cc",
            textDecoration: "none",
            display: "inline-block",
            marginTop: "10px"
          }}
        >
          ⬇️ Download PDF
        </a>
      </li>
    );
  }

  // For images
  if (mime.startsWith("image/")) {
    return (
      <li key={index} style={{ marginBottom: "15px", padding: "10px", border: "1px solid #e0e0e0", borderRadius: "4px" }}>
        <strong>{att.filename}</strong> ({mime})
        <div style={{ margin: "10px 0" }}>
          <img
            src={base64Url}
            alt={att.filename}
            style={{
              maxWidth: "100%",
              maxHeight: "300px",
              display: "block",
              marginBottom: "10px",
              border: "1px solid #ccc",
            }}
          />
        </div>
        <a href={base64Url} download={att.filename} style={{ color: "#0066cc", textDecoration: "none" }}>
          ⬇️ Download
        </a>
      </li>
    );
  }

  // For text files
  if (mime.startsWith("text/")) {
    return (
      <li key={index} style={{ marginBottom: "15px", padding: "10px", border: "1px solid #e0e0e0", borderRadius: "4px" }}>
        <strong>{att.filename}</strong> ({mime})
        <pre
          style={{
            background: "#f9f9f9",
            padding: "10px",
            maxHeight: "200px",
            overflowY: "auto",
            whiteSpace: "pre-wrap",
          }}
        >
          {atob(att.data_base64)}
        </pre>
        <a href={base64Url} download={att.filename} style={{ color: "#0066cc", textDecoration: "none" }}>
          ⬇️ Download
        </a>
      </li>
    );
  }

  // For unsupported file types
  return (
    <li key={index} style={{ marginBottom: "15px", padding: "10px", border: "1px solid #e0e0e0", borderRadius: "4px" }}>
      <strong>{att.filename}</strong> ({mime})
      <p>Unsupported file type for preview.</p>
      <a href={base64Url} download={att.filename} style={{ color: "#0066cc", textDecoration: "none" }}>
        ⬇️ Download
      </a>
    </li>
  );
};

  const currentEmail = emails[currentIndex];

  // Styling objects
  const styles = {
    container: {
      maxWidth: "1200px",
      margin: "0 auto",
      padding: "20px",
      fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
    },
    header: {
      color: "#fff",
      borderBottom: "2px solid #eee",
      paddingBottom: "10px",
      marginBottom: "20px"
    },
    emailMeta: {
      backgroundColor: "#272727",
      color: "#fff",
      padding: "15px",
      borderRadius: "5px",
      marginBottom: "20px",
      lineHeight: "1.6"
    },
    contentBox: {
      border: "1px solid #929292",
      borderRadius: "5px",
      padding: "20px",
      marginBottom: "20px",
      backgroundColor: "#272727"
    },
    authenticityBox: {
      backgroundColor: "#272727",
      color: "#fff",
      padding: "15px",
      borderRadius: "5px",
      marginBottom: "20px"
    },
    statusWarning: {
      color: "#ffcc00",
      fontWeight: "bold"
    },
    statusVerified: {
      color: "#4CAF50",
      fontWeight: "bold"
    },
    navButtons: {
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      gap: "20px",
      margin: "20px 0"
    },
    button: {
      padding: "8px 16px",
      backgroundColor: "#0066cc",
      color: "white",
      border: "none",
      borderRadius: "4px",
      cursor: "pointer"
    },
    buttonDisabled: {
      opacity: 0.5,
      cursor: "not-allowed"
    }
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.header}>📧 Gmail Analyzer</h1>
      
      {error && <p style={{ color: "red" }}>{error}</p>}
      
      {loading ? (
        <p>Loading emails...</p>
      ) : emails.length === 0 ? (
        <p>No emails found</p>
      ) : (
        <div>
          {/* Email Metadata */}
          <div style={styles.emailMeta}>
            <p><strong>From:</strong> {currentEmail?.metadata?.from}</p>
            <p><strong>To:</strong> {currentEmail?.metadata?.to}</p>
            <p><strong>Subject:</strong> {currentEmail?.metadata?.subject}</p>
            <p><strong>Date:</strong> {currentEmail?.metadata?.date}</p>
          </div>

          {/* Email Content */}
          <div style={styles.contentBox}>
            <h3 style={{ marginTop: 0 }}>📨 Email Content</h3>
            {currentEmail?.body_html ? (
              <div 
                dangerouslySetInnerHTML={{ __html: currentEmail.body_html }}
                style={{
                  maxHeight: "500px",
                  overflowY: "auto",
                  padding: "15px",
                  border: "1px solid #929292",
                  backgroundColor: "#272727"
                }}
              />
            ) : currentEmail?.body_text ? (
              <pre style={{
                whiteSpace: "pre-wrap",
                fontFamily: "inherit",
                padding: "15px",
                backgroundColor: "#272727",
                border: "1px solid #929292",
                maxHeight: "500px",
                overflowY: "auto"
              }}>
                {currentEmail.body_text}
              </pre>
            ) : (
              <p style={{ fontStyle: "italic" }}>No email content available</p>
            )}
          </div>

          {/* Sender Authenticity */}
          {currentEmail?.authenticity && (
            <div style={styles.authenticityBox}>
              <h3 style={{ marginTop: 0 }}>🔍 Sender Authenticity Check</h3>
              <p><strong>Domain:</strong> {currentEmail.authenticity.domain}</p>
              
              <div style={{ marginTop: "15px" }}>
                <strong>SPF Records:</strong>
                <ul style={{ marginTop: "5px", marginLeft: "20px" }}>
                  {(currentEmail.authenticity.SPF || []).map((record, i) => (
                    <li key={`spf-${i}`} style={{ wordBreak: "break-word", marginBottom: "5px" }}>
                      <code>{record}</code>
                    </li>
                  ))}
                </ul>
              </div>

              <div style={{ marginTop: "15px" }}>
                <strong>DKIM Records:</strong>
                <ul style={{ marginTop: "5px", marginLeft: "20px" }}>
                  {(currentEmail.authenticity.DKIM || []).map((record, i) => (
                    <li key={`dkim-${i}`} style={{ wordBreak: "break-word", marginBottom: "5px" }}>
                      <code>{record}</code>
                    </li>
                  ))}
                </ul>
              </div>

              <div style={{ marginTop: "15px" }}>
                <strong>DMARC Records:</strong>
                <ul style={{ marginTop: "5px", marginLeft: "20px" }}>
                  {(currentEmail.authenticity.DMARC || []).map((record, i) => (
                    <li key={`dmarc-${i}`} style={{ wordBreak: "break-word", marginBottom: "5px" }}>
                      <code>{record}</code>
                    </li>
                  ))}
                </ul>
              </div>

              <div style={{ marginTop: "15px", padding: "10px", backgroundColor: "#333" }}>
                <strong>Overall Status:</strong>{" "}
                {(currentEmail.authenticity.DKIM && currentEmail.authenticity.DKIM[0] === "No record found") ? (
                  <span style={styles.statusWarning}>⚠️ Warning (DKIM missing)</span>
                ) : (
                  <span style={styles.statusVerified}>✅ Verified</span>
                )}
              </div>
            </div>
          )}

          {/* Attachments */}
          {currentEmail?.attachments && currentEmail.attachments.length > 0 && (
            <div style={styles.contentBox}>
              <h3 style={{ marginTop: 0 }}>📎 Attachments ({currentEmail.attachments.length})</h3>
              <ul style={{ listStyle: "none", padding: 0 }}>
                {currentEmail.attachments.map((att, index) => renderAttachment(att, index))}
              </ul>
            </div>
          )}

          {/* Navigation */}
          <div style={styles.navButtons}>
            <button 
              onClick={handlePrev} 
              disabled={currentIndex === 0}
              style={{ ...styles.button, ...(currentIndex === 0 ? styles.buttonDisabled : {}) }}
            >
              Previous
            </button>
            <span>Email {currentIndex + 1} of {emails.length}</span>
            <button 
              onClick={handleNext} 
              disabled={currentIndex === emails.length - 1}
              style={{ ...styles.button, ...(currentIndex === emails.length - 1 ? styles.buttonDisabled : {}) }}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default GmailAnalyzer;