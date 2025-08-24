import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { w3cwebsocket as W3CWebSocket } from "websocket";

function GmailAnalyzer() {
  const [emails, setEmails] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [requestId, setRequestId] = useState(null);
  const [wsClient, setWsClient] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");

  // Generate a unique request ID for cache busting
  const generateRequestId = () => {
    return Math.random().toString(36).substring(2, 15) + 
           Math.random().toString(36).substring(2, 15);
  };

  // WebSocket connection management
  useEffect(() => {
    const client = new W3CWebSocket('ws://localhost:8000/ws/emails');
    
    client.onopen = () => {
      console.log('WebSocket Client Connected');
      setConnectionStatus("connected");
    };
    
    client.onmessage = (message) => {
      try {
        const data = JSON.parse(message.data);
        if (data.type === "email_update") {
          // Update the specific email in our state
          setEmails(prevEmails => {
            const newEmails = [...prevEmails];
            if (newEmails[data.email_id]) {
              newEmails[data.email_id] = {
                ...newEmails[data.email_id],
                ...data.data
              };
            }
            return newEmails;
          });
        }
      } catch (error) {
        console.error('Error processing WebSocket message:', error);
      }
    };
    
    client.onclose = () => {
      console.log('WebSocket Client Disconnected');
      setConnectionStatus("disconnected");
    };
    
    client.onerror = (error) => {
      console.error('WebSocket Client Error:', error);
      setConnectionStatus("error");
    };
    
    setWsClient(client);
    
    return () => {
      client.close();
    };
  }, []);

  // Helper functions for DNS validation display
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
    // Determine status based on type and status
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
      return <div style={{ padding: '15px', backgroundColor: '#333', borderRadius: '5px', marginBottom: '20px' }}>
        <h4 style={{ margin: '0 0 10px 0', color: '#FF6B6B' }}>❌ Security Summary Not Available</h4>
      </div>;
    }

    return (
      <div style={{ 
        padding: '15px', 
        backgroundColor: '#333', 
        borderRadius: '5px',
        marginBottom: '20px',
        border: `2px solid ${getStatusColor(authenticity.overall_status || 'untrustworthy')}`
      }}>
        <h4 style={{ margin: '0 0 10px 0' }}>
          {getStatusIcon(authenticity.overall_status || 'untrustworthy')} Overall Security Status: 
          <span style={{ color: getStatusColor(authenticity.overall_status || 'untrustworthy'), marginLeft: '8px' }}>
            {(authenticity.overall_status || 'untrustworthy').replace(/_/g, ' ').toUpperCase()}
          </span>
        </h4>
        {authenticity.last_updated && (
          <p style={{ fontSize: '12px', color: '#aaa', margin: 0 }}>
            Last updated: {new Date(authenticity.last_updated * 1000).toLocaleTimeString()}
          </p>
        )}
        {authenticity.request_id && (
          <p style={{ fontSize: '10px', color: '#777', margin: '5px 0 0 0' }}>
            Request ID: {authenticity.request_id}
          </p>
        )}
      </div>
    );
  };

  const renderDNSRecord = (type, title, authenticity) => {
    if (!authenticity || !authenticity[type]) {
      return (
        <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#2a2a2a', borderRadius: '5px' }}>
          <h5 style={{ margin: '0 0 10px 0', color: '#F44336' }}>
            ❌ {title}: Data Not Available
          </h5>
        </div>
      );
    }
    
    const data = authenticity[type];
    const statusConfig = getDNSStatusConfig(type, data.status);
    
    // Check if we have any valid content to show
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
      <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#2a2a2a', borderRadius: '5px' }}>
        <h5 style={{ margin: '0 0 10px 0', color: statusConfig.color }}>
          {statusConfig.icon} {title}: {statusConfig.statusText}
        </h5>
        <p>{description}</p>
        <div style={{ 
          padding: '10px', 
          backgroundColor: '#1a1a1a', 
          borderRadius: '3px',
          maxHeight: '150px',
          overflowY: 'auto'
        }}>
          {hasContent ? (
            data.records.map((record, index) => (
              <div key={index} style={{ 
                fontFamily: 'monospace', 
                fontSize: '12px',
                marginBottom: '5px',
                wordBreak: 'break-all'
              }}>
                {record}
              </div>
            ))
          ) : (
            <div style={{ color: '#999', fontStyle: 'italic' }}>
              No record details available
            </div>
          )}
        </div>
      </div>
    );
  };

  const fetchEmails = useCallback(async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    
    const newRequestId = generateRequestId();
    if (forceRefresh) {
      setRequestId(newRequestId);
    }
    
    try {
      const response = await axios.get(
        `http://localhost:8000/analyze/gmail?t=${Date.now()}&rid=${forceRefresh ? newRequestId : requestId}`
      );
      
      setEmails(response.data.gmail_messages || []);
      setLastUpdated(Date.now());
      if (forceRefresh) {
        setCurrentIndex(0);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to fetch Gmail messages.");
    } finally {
      setLoading(false);
    }
  }, [requestId]);

  useEffect(() => {
    fetchEmails(true); // Force refresh on initial load
  }, [fetchEmails]);

  const handlePrev = () => {
    if (currentIndex > 0) setCurrentIndex(currentIndex - 1);
  };

  const handleNext = () => {
    if (currentIndex < emails.length - 1) setCurrentIndex(currentIndex + 1);
  };

  const handleOpenLink = (url) => {
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const handleRefresh = () => {
    fetchEmails(true);
  };

  const handleSoftRefresh = () => {
    fetchEmails(false);
  };

  const renderLinks = (links) => {
    if (!links || links.length === 0) {
      return <p>No links found in this email</p>;
    }

    return (
      <div style={{ marginTop: "15px" }}>
        <h4>🔗 Links Found ({links.length})</h4>
        <div
          style={{
            backgroundColor: "#272727",
            padding: "15px",
            borderRadius: "5px",
            border: "1px solid #444",
          }}
        >
          <p style={{ color: "#ffcc00", marginBottom: "15px" }}>
            ⚠️ Warning: Always verify links before opening. External links may be
            unsafe.
          </p>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {links.map((link, index) => (
              <li
                key={index}
                style={{
                  marginBottom: "15px",
                  padding: "15px",
                  border: "1px solid #444",
                  borderRadius: "4px",
                  backgroundColor: "#1a1a1a",
                }}
              >
                <div style={{ wordBreak: "break-all", marginBottom: "8px" }}>
                  <strong>URL:</strong> {link.url}
                </div>
                <div style={{ marginBottom: "8px" }}>
                  <strong>Domain:</strong> {link.domain || "None"}
                </div>
                <div
                  style={{
                    marginBottom: "10px",
                    color: link.is_external ? "#ff6b6b" : "#4CAF50",
                    fontWeight: "bold",
                  }}
                >
                  {link.is_external ? "⚠️ External Link" : "✓ Internal Link"}
                </div>
                <div style={{ marginBottom: "10px" }}>
                  <strong>Security:</strong>{" "}
                  {link.is_external ? "Proceed with caution!" : "Ok"}
                </div>

                {/* Actions */}
                <button
                  onClick={() => handleOpenLink(link.url)}
                  style={{
                    padding: "8px 16px",
                    backgroundColor: "#0066cc",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                    marginRight: "10px",
                  }}
                >
                  Open Link
                </button>
                <button
                  onClick={() => navigator.clipboard.writeText(link.url)}
                  style={{
                    padding: "8px 16px",
                    backgroundColor: "#333",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                  }}
                >
                  Copy Link
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    );
  };

  const currentEmail = emails[currentIndex];

  const styles = {
    container: {
      maxWidth: "1200px",
      margin: "0 auto",
      padding: "20px",
      fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
      backgroundColor: "#1e1e1e",
      color: "#fff",
      minHeight: "100vh"
    },
    header: {
      color: "#fff",
      borderBottom: "2px solid #444",
      paddingBottom: "10px",
      marginBottom: "20px",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      flexWrap: "wrap"
    },
    emailMeta: {
      backgroundColor: "#272727",
      color: "#fff",
      padding: "15px",
      borderRadius: "5px",
      marginBottom: "20px",
      lineHeight: "1.6",
    },
    contentBox: {
      border: "1px solid #444",
      borderRadius: "5px",
      padding: "20px",
      marginBottom: "20px",
      backgroundColor: "#272727",
    },
    authenticityBox: {
      backgroundColor: "#272727",
      color: "#fff",
      padding: "20px",
      borderRadius: "8px",
      marginBottom: "20px",
      border: "1px solid #444"
    },
    statusWarning: { color: "#ffcc00", fontWeight: "bold" },
    statusVerified: { color: "#4CAF50", fontWeight: "bold" },
    navButtons: {
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      gap: "20px",
      margin: "20px 0",
    },
    button: {
      padding: "8px 16px",
      backgroundColor: "#0066cc",
      color: "white",
      border: "none",
      borderRadius: "4px",
      cursor: "pointer",
      margin: "5px"
    },
    buttonDisabled: { opacity: 0.5, cursor: "not-allowed" },
    refreshButton: {
      padding: "8px 16px",
      backgroundColor: "#4CAF50",
      color: "white",
      border: "none",
      borderRadius: "4px",
      cursor: "pointer",
      margin: "5px"
    },
    softRefreshButton: {
      padding: "8px 16px",
      backgroundColor: "#FF9800",
      color: "white",
      border: "none",
      borderRadius: "4px",
      cursor: "pointer",
      margin: "5px"
    },
    connectionStatus: {
      padding: "5px 10px",
      borderRadius: "4px",
      fontSize: "12px",
      marginLeft: "10px"
    }
  };

  const getConnectionStatusColor = () => {
    switch(connectionStatus) {
      case "connected": return "#4CAF50";
      case "disconnected": return "#F44336";
      case "error": return "#FF9800";
      default: return "#9E9E9E";
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1>📧 Gmail Analyzer</h1>
        <div>
          <span style={{ 
            ...styles.connectionStatus, 
            backgroundColor: getConnectionStatusColor() 
          }}>
            WebSocket: {connectionStatus}
          </span>
          <button onClick={handleRefresh} style={styles.refreshButton}>
            🔄 Hard Refresh
          </button>
          <button onClick={handleSoftRefresh} style={styles.softRefreshButton}>
            ↻ Soft Refresh
          </button>
        </div>
      </div>

      {error && (
        <div style={{ color: "red", padding: "10px", backgroundColor: "#300", borderRadius: "5px", marginBottom: "15px" }}>
          {error}
          <button onClick={handleRefresh} style={{ marginLeft: "15px", padding: "5px 10px" }}>
            Retry
          </button>
        </div>
      )}
      
      {lastUpdated && (
        <p style={{ color: "#aaa", fontSize: "14px", marginTop: "-15px", marginBottom: "20px" }}>
          Last updated: {new Date(lastUpdated).toLocaleTimeString()}
          {requestId && (
            <span style={{ marginLeft: "15px", color: "#777" }}>
              Request ID: {requestId}
            </span>
          )}
        </p>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: "40px" }}>
          <p>Loading emails...</p>
          <div style={{ width: "100%", height: "4px", backgroundColor: "#333", margin: "20px auto" }}>
            <div style={{ width: "70%", height: "100%", backgroundColor: "#0066cc", animation: "loading 1.5s infinite" }}></div>
          </div>
        </div>
      ) : emails.length === 0 ? (
        <p>No emails found</p>
      ) : (
        <div>
          {/* Navigation */}
          <div style={styles.navButtons}>
            <button
              onClick={handlePrev}
              disabled={currentIndex === 0}
              style={{
                ...styles.button,
                ...(currentIndex === 0 ? styles.buttonDisabled : {}),
              }}
            >
              Previous
            </button>
            <span>
              Email {currentIndex + 1} of {emails.length}
            </span>
            <button
              onClick={handleNext}
              disabled={currentIndex === emails.length - 1}
              style={{
                ...styles.button,
                ...(currentIndex === emails.length - 1
                  ? styles.buttonDisabled
                  : {}),
              }}
            >
              Next
            </button>
          </div>

          {/* Metadata */}
          <div style={styles.emailMeta}>
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
                  border: "1px solid #444",
                  backgroundColor: "#1a1a1a"
                }}
              />
            ) : currentEmail?.body_text ? (
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  fontFamily: "inherit",
                  padding: "15px",
                  backgroundColor: "#1a1a1a",
                  border: "1px solid #444",
                  maxHeight: "500px",
                  overflowY: "auto"
                }}
              >
                {currentEmail.body_text}
              </pre>
            ) : (
              <p style={{ fontStyle: "italic" }}>No email content available</p>
            )}
          </div>

          {/* Links */}
          <div style={styles.contentBox}>
            {currentEmail?.links && renderLinks(currentEmail.links)}
          </div>

          {/* Authenticity */}
          {currentEmail?.authenticity && (
            <div style={styles.authenticityBox}>
              <h3 style={{ marginTop: 0 }}>🔍 Email Authenticity Check</h3>
              
              {/* Domain and Syntax Validation */}
              <div style={{ marginBottom: '20px' }}>
                <p><strong>Domain:</strong> {currentEmail.authenticity.domain}</p>
                <p>
                  <strong>Email Syntax:</strong> 
                  <span style={{ 
                    color: currentEmail.authenticity.email_syntax ? '#4CAF50' : '#F44336', 
                    marginLeft: '8px' 
                  }}>
                    {currentEmail.authenticity.email_syntax ? '✅ Valid' : '❌ Invalid'}
                  </span>
                </p>
              </div>

              {/* Overall Security Status */}
              {renderSecurityStatus(currentEmail.authenticity)}

              {/* Individual DNS Records */}
              {renderDNSRecord('spf', 'SPF Records', currentEmail.authenticity)}
              {renderDNSRecord('dkim', 'DKIM Records', currentEmail.authenticity)}
              {renderDNSRecord('dmarc', 'DMARC Records', currentEmail.authenticity)}
              {renderDNSRecord('mx', 'MX Records', currentEmail.authenticity)}

              {/* Security Explanation */}
              <div style={{ 
                marginTop: '20px', 
                padding: '15px', 
                backgroundColor: '#2a2a2a', 
                borderRadius: '5px' 
              }}>
                <h5>🔒 Security Explanation:</h5>
                <ul style={{ margin: '10px 0', paddingLeft: '20px' }}>
                  <li><strong>SPF:</strong> Prevents email spoofing</li>
                  <li><strong>DKIM:</strong> Ensures email integrity</li>
                  <li><strong>DMARC:</strong> Policy for handling failed emails</li>
                  <li><strong>MX Records:</strong> Mail server configuration</li>
                </ul>
              </div>
            </div>
          )}

          {/* Navigation */}
          <div style={styles.navButtons}>
            <button
              onClick={handlePrev}
              disabled={currentIndex === 0}
              style={{
                ...styles.button,
                ...(currentIndex === 0 ? styles.buttonDisabled : {}),
              }}
            >
              Previous
            </button>
            <span>
              Email {currentIndex + 1} of {emails.length}
            </span>
            <button
              onClick={handleNext}
              disabled={currentIndex === emails.length - 1}
              style={{
                ...styles.button,
                ...(currentIndex === emails.length - 1
                  ? styles.buttonDisabled
                  : {}),
              }}
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