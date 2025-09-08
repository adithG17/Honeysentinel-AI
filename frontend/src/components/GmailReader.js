import React, { useEffect, useState } from "react";
import axios from "axios";
import "./GmailReader.css";
import DomainChecker from "./GmailAnalyzer"; 

function GmailAnalyzer() {
  const [emails, setEmails] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authenticityData, setAuthenticityData] = useState({});
  const [processingStatus, setProcessingStatus] = useState({});
  const [feedbackSelections, setFeedbackSelections] = useState({});

  useEffect(() => {
    loadEmails();
  }, []);
  
  // Reset feedback selections when current email changes
  useEffect(() => {
    setFeedbackSelections({});
  }, [currentIndex]);

  const loadEmails = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get(`http://localhost:8000/analyze/gmail?max_results=10`);
      setEmails(response.data.gmail_messages || []);
      
      const initialStatus = {};
      response.data.gmail_messages.forEach(email => {
        initialStatus[email.id] = "pending";
      });
      setProcessingStatus(initialStatus);
      
      if (response.data.gmail_messages && response.data.gmail_messages.length > 0) {
        fetchAuthenticityData(response.data.gmail_messages[0].id);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to load emails.");
    } finally {
      setLoading(false);
    }
  };



  const fetchAuthenticityData = async (emailId) => {
    if (authenticityData[emailId] || processingStatus[emailId] === "processing") {
      return;
    }
    
    setProcessingStatus(prev => ({ ...prev, [emailId]: "processing" }));
    
    try {
      const response = await axios.get(`http://localhost:8000/analyze/gmail/${emailId}/authenticity`);
      
      if (response.data.status === "processing") {
        setTimeout(() => fetchAuthenticityData(emailId), 1000);
      } else {
        setAuthenticityData(prev => ({ ...prev, [emailId]: response.data }));
        setProcessingStatus(prev => ({ ...prev, [emailId]: "completed" }));
      }
    } catch (err) {
      console.error("Failed to fetch authenticity data", err);
      setProcessingStatus(prev => ({ ...prev, [emailId]: "error" }));
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      const newIndex = currentIndex - 1;
      setCurrentIndex(newIndex);
      
      const emailId = emails[newIndex]?.id;
      if (emailId && !authenticityData[emailId] && processingStatus[emailId] !== "processing") {
        fetchAuthenticityData(emailId);
      }
    }
  };

  const handleNext = () => {
    if (currentIndex < emails.length - 1) {
      const newIndex = currentIndex + 1;
      setCurrentIndex(newIndex);
      
      const emailId = emails[newIndex]?.id;
      if (emailId && !authenticityData[emailId] && processingStatus[emailId] !== "processing") {
        fetchAuthenticityData(emailId);
      }
    }
  };

  const handleOpenLink = (url) => {
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const handleRefresh = () => {
    loadEmails();
  };
  
  // Handle feedback for links
  const handleFeedback = async (url, feedback) => {
    try {
      const response = await fetch("http://localhost:8000/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, label: feedback }),
      });

      if (!response.ok) {
        throw new Error("Failed to send feedback");
      }
      
      // Update the feedback selection state
      setFeedbackSelections(prev => ({
        ...prev,
        [url]: feedback
      }));
      
      alert(`Feedback sent: ${feedback}`);
    } catch (error) {
      console.error("Error sending feedback:", error);
    }
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'highly_trustworthy': return '#4CAF50';
      case 'moderately_trustworthy': return '#FF9800';
      case 'untrustworthy': return '#F44336';
      default: return '#9E9E9E';
    }
  };

  const getStatusIcon = (status) => {
    switch(status) {
      case 'highly_trustworthy': return '✅';
      case 'moderately_trustworthy': return '⚠️';
      case 'untrustworthy': return '❌';
      default: return '❓';
    }
  };

  const getDNSStatusConfig = (type, status) => {
    switch(type) {
      case 'spf':
        if (status === 'configured') {
          return { icon: '✅', color: '#4CAF50', statusText: 'Configured' };
        } else if (status === 'error') {
          return { icon: '❌', color: '#F44336', statusText: 'Error' };
        } else {
          return { icon: '❌', color: '#F44336', statusText: 'Not Configured' };
        }
      
      case 'dkim':
        if (status === 'pass') {
          return { icon: '✅', color: '#4CAF50', statusText: 'Pass' };
        } else if (status === 'fail') {
          return { icon: '❌', color: '#F44336', statusText: 'Fail' };
        } else if (status === 'error') {
          return { icon: '❌', color: '#F44336', statusText: 'Error' };
        } else {
          return { icon: '❌', color: '#F44336', statusText: 'Not Configured' };
        }
      
      case 'dmarc':
        if (status === 'reject') {
          return { icon: '✅', color: '#4CAF50', statusText: 'Reject Policy' };
        } else if (status === 'quarantine') {
          return { icon: '⚠️', color: '#FF9800', statusText: 'Quarantine Policy' };
        } else if (status === 'none') {
          return { icon: '❌', color: '#F44336', statusText: 'None Policy' };
        } else if (status === 'error') {
          return { icon: '❌', color: '#F44336', statusText: 'Error' };
        } else {
          return { icon: '❌', color: '#F44336', statusText: 'Not Configured' };
        }
      
      case 'mx':
        if (status === 'configured') {
          return { icon: '✅', color: '#4CAF50', statusText: 'Configured' };
        } else if (status === 'error') {
          return { icon: '❌', color: '#F44336', statusText: 'Error' };
        } else {
          return { icon: '❌', color: '#F44336', statusText: 'Not Configured' };
        }
      
      default:
        return { icon: '❓', color: '#9E9E9E', statusText: 'Unknown' };
    }
  };

  const renderSecurityStatus = (authenticity) => {
    if (!authenticity) {
      return (
        <div className="security-status">
          <h4>❌ Security Summary Not Available</h4>
        </div>
      );
    }

    return (
      <div 
        className="security-status"
        style={{ borderColor: getStatusColor(authenticity.overall_status || 'untrustworthy') }}
      >
        <h4>
          {getStatusIcon(authenticity.overall_status || 'untrustworthy')} Overall Security Status: 
          <span style={{ color: getStatusColor(authenticity.overall_status || 'untrustworthy') }}>
            {(authenticity.overall_status || 'untrustworthy').replace(/_/g, ' ').toUpperCase()}
          </span>
        </h4>
        {authenticity.last_updated && (
          <p className="last-updated">
            Last updated: {new Date(authenticity.last_updated * 1000).toLocaleTimeString()}
          </p>
        )}
        {authenticity.request_id && (
          <p className="request-id">
            Request ID: {authenticity.request_id}
          </p>
        )}
      </div>
    );
  };

  const renderDNSRecord = (type, title, authenticity) => {
    if (!authenticity || !authenticity[type]) {
      return (
        <div className="dns-record">
          <h5>❌ {title}: Data Not Available</h5>
        </div>
      );
    }
    
    const data = authenticity[type];
    const statusConfig = getDNSStatusConfig(type, data.status);
    
    const hasContent = data.records && data.records.length > 0 && 
                      !data.records[0].includes("error") &&
                      !data.records[0].includes("No record");

    let description = "";
    switch(type) {
      case 'spf':
        description = "Sender Policy Framework helps prevent email spoofing.";
        break;
      case 'dkim':
        description = "DomainKeys Identified Mail ensures email integrity.";
        break;
      case 'dmarc':
        if (data.status === 'reject') {
          description = "DMARC reject policy blocks unauthorized emails.";
        } else if (data.status === 'quarantine') {
          description = "DMARC quarantine policy sends unauthorized emails to spam.";
        } else if (data.status === 'none') {
          description = "DMARC none policy only monitors but takes no action.";
        } else {
          description = "Domain-based Message Authentication, Reporting & Conformance.";
        }
        break;
      case 'mx':
        description = "Mail Exchange records specify mail servers for the domain.";
        break;
      default:
        description = "DNS record information.";
    }

    return (
      <div className="dns-record">
        <h5 style={{ color: statusConfig.color }}>
          {statusConfig.icon} {title}: {statusConfig.statusText}
        </h5>
        <p>{description}</p>
        <div className="dns-record-content">
          {hasContent ? (
            data.records.map((record, index) => (
              <div key={index} className="dns-record-item">
                {record}
              </div>
            ))
          ) : (
            <div className="no-record">
              No record details available
            </div>
          )}
        </div>
      </div>
    );
  };

const renderLinks = (links) => {
  if (!links || links.length === 0) {
    return <p>No links found in this email</p>;
  }

  return (
    <div className="links-container">
      <h4>🔗 Links Found ({links.length})</h4>
      <div className="links-warning-box">
        <p>⚠️ Warning: Always verify links before opening. External links may be unsafe.</p>
        <ul>
          {links.map((link, index) => {
            let scanStatusColor = "#666";
            let scanStatusIcon = "❓";
            let scanStatusText = "Unknown";

            if (link.scan_status === "safe") {
              scanStatusColor = "#4CAF50";
              scanStatusIcon = "✅";
              scanStatusText = "Safe";
            } else if (link.scan_status === "unsafe") {
              scanStatusColor = "#F44336";
              scanStatusIcon = "❌";
              scanStatusText = "Unsafe";
            } else if (link.scan_status === "error") {
              scanStatusColor = "#FF9800";
              scanStatusIcon = "⚠️";
              scanStatusText = "Scan Error";
            }

            return (
              <li key={index} className="link-item">
                <div className="link-url">
                  <strong>URL:</strong> {link.url}
                </div>
                <div className="link-domain">
                  <strong>Domain:</strong> {link.domain || "None"}
                </div>
                <div className={link.is_external ? "link-external" : "link-internal"}>
                  {link.is_external ? "⚠️ External Link" : "✓ Internal Link"}
                </div>

                <div className="link-scan-status" style={{ color: scanStatusColor }}>
                  <strong>{scanStatusIcon} Scan Status:</strong> {scanStatusText}
                </div>

                {link.scan_details && link.scan_details.length > 0 && (
                  <div className="link-scan-details">
                    <strong>Scan Details:</strong>
                    <ul>
                      {link.scan_details.map((detail, detailIndex) => (
                        <li key={detailIndex}>{detail}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <button
                  onClick={() => handleOpenLink(link.url)}
                  className="link-button open-button"
                  disabled={link.scan_status === "unsafe"}
                >
                  {link.scan_status === "unsafe" ? "Unsafe Link" : "Open Link"}
                </button>
                <button
                  onClick={() => navigator.clipboard.writeText(link.url)}
                  className="link-button copy-button"
                >
                  Copy Link
                </button>

                <div className="link-feedback">
                  <label>Feedback: </label>
                  <select
                    value={feedbackSelections[link.url] || ""}
                    onChange={(e) => handleFeedback(link.url, e.target.value)}
                  >
                    <option value="">Select</option>
                    <option value="safe">Safe</option>
                    <option value="marketing">Marketing</option>
                    <option value="phishing">Phishing</option>
                    <option value="scam">Scam</option>
                  </select>

                  {feedbackSelections[link.url] && (
                    <span className="feedback-confirmation">
                      ✓ Saved as {feedbackSelections[link.url]}
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
};


  
  // Function to create a safe HTML document for the iframe
  const createSafeEmailDocument = (htmlContent) => {
    // Basic sanitization - you might want to use a library like DOMPurify for production
    const cleanHtml = htmlContent
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
      .replace(/on\w+="[^"]*"/g, '')
      .replace(/on\w+='[^']*'/g, '')
      .replace(/on\w+=\w+\(\)/g, '');
    
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <base target="_blank">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
          body { 
            font-family: Arial, sans-serif; 
            padding: 15px; 
            line-height: 1.5;
            color: #333;
            background-color: #fff;
            margin: 0;
            max-width: 100%;
            overflow-wrap: break-word;
          }
          img { max-width: 100%; height: auto; }
          a { color: #0066cc; }
          table { max-width: 100%; border-collapse: collapse; }
          * { max-width: 100%; }
        </style>
      </head>
      <body>
        ${cleanHtml}
      </body>
      </html>
    `;
  };

  const currentEmail = emails[currentIndex];
  const currentEmailId = currentEmail?.id;
  const currentAuthenticity = currentEmailId ? authenticityData[currentEmailId] : null;
  const isProcessing = currentEmailId ? processingStatus[currentEmailId] === "processing" : false;

  return (
    <div className="gmail-analyzer-container">
      <div className="gmail-analyzer-header">
        <h1>📧 Gmail Analyzer</h1>
        <div>
          <button onClick={handleRefresh} className="refresh-button">
            🔄 Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={handleRefresh} className="retry-button">
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className="loading-container">
          <p>Loading emails...</p>
          <div className="loading-bar">
            <div className="loading-progress"></div>
          </div>
        </div>
      ) : emails.length === 0 ? (
        <p>No emails found</p>
      ) : (
        <div>
          <div className="nav-buttons">
            <button
              onClick={handlePrev}
              disabled={currentIndex === 0}
              className={currentIndex === 0 ? "nav-button disabled" : "nav-button"}
            >
              Previous
            </button>
            <span>
              Email {currentIndex + 1} of {emails.length}
            </span>
            <button
              onClick={handleNext}
              disabled={currentIndex === emails.length - 1}
              className={currentIndex === emails.length - 1 ? "nav-button disabled" : "nav-button"}
            >
              Next
            </button>
          </div>

          <div className="email-meta">
            <p>
              <strong>From:</strong> {currentEmail?.metadata?.from}
            </p>
            <p>
              <strong>To:</strong> {currentEmail?.metadata?.to}
            </p>
            <p>
              <strong>Subject:</strong> {currentEmail?.metadata?.subject}
            </p>
            <p>
              <strong>Date:</strong> {currentEmail?.metadata?.date}
            </p>
          </div>

          <div className="content-box">
            <h3>📨 Email Content</h3>
            {currentEmail?.body_html ? (
              <div className="email-iframe-container">
                <div className="iframe-warning">
                  Email content isolated in iframe to prevent CSS conflicts
                </div>
                <iframe
                  srcDoc={createSafeEmailDocument(currentEmail.body_html)}
                  className="email-iframe"
                  title="Email content"
                  sandbox="allow-same-origin"
                />
              </div>
            ) : currentEmail?.body_text ? (
              <pre className="email-content-text">
                {currentEmail.body_text}
              </pre>
            ) : (
              <p className="no-content">No email content available</p>
            )}
          </div>

          <div className="content-box">
            {currentEmail?.links && renderLinks(currentEmail.links)}
          </div>

          <div className="authenticity-box">
            <h3>🔍 Email Authenticity Check</h3>
            
            {isProcessing ? (
              <div className="processing-container">
                <p>Checking authenticity...</p>
                <div className="loading-bar">
                  <div className="loading-progress"></div>
                </div>
              </div>
            ) : currentAuthenticity ? (
              <>
                <div className="domain-syntax">
                  <p><strong>Domain:</strong> {currentAuthenticity.domain}</p>
                  <p>
                    <strong>Email Syntax:</strong> 
                    <span className={currentAuthenticity.email_syntax ? "syntax-valid" : "syntax-invalid"}>
                      {currentAuthenticity.email_syntax ? '✅ Valid' : '❌ Invalid'}
                    </span>
                  </p>
                </div>

                <DomainChecker email={currentEmail?.metadata?.from} />

                {renderSecurityStatus(currentAuthenticity)}

                {renderDNSRecord('spf', 'SPF Records', currentAuthenticity)}
                {renderDNSRecord('dkim', 'DKIM Records', currentAuthenticity)}
                {renderDNSRecord('dmarc', 'DMARC Records', currentAuthenticity)}
                {renderDNSRecord('mx', 'MX Records', currentAuthenticity)}

                <div className="security-explanation">
                  <h5>🔒 Security Explanation:</h5>
                  <ul>
                    <li><strong>SPF:</strong> Prevents email spoofing</li>
                    <li><strong>DKIM:</strong> Ensures email integrity</li>
                    <li><strong>DMARC:</strong> Policy for handling failed emails</li>
                    <li><strong>MX Records:</strong> Mail server configuration</li>
                  </ul>
                </div>
              </>
            ) : (
              <div className="no-authenticity-data">
                <h4>❌ Authenticity Data Not Available</h4>
                <button onClick={() => fetchAuthenticityData(currentEmailId)} className="check-authenticity-button">
                  Check Authenticity
                </button>
              </div>
            )}
          </div>

          <div className="nav-buttons">
            <button
              onClick={handlePrev}
              disabled={currentIndex === 0}
              className={currentIndex === 0 ? "nav-button disabled" : "nav-button"}
            >
              Previous
            </button>
            <span>
              Email {currentIndex + 1} of {emails.length}
            </span>
            <button
              onClick={handleNext}
              disabled={currentIndex === emails.length - 1}
              className={currentIndex === emails.length - 1 ? "nav-button disabled" : "nav-button"}
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