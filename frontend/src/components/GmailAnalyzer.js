import React, { useState, useEffect } from 'react';
import axios from 'axios';

function DomainChecker({ email }) {
  const [domainData, setDomainData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (email) {
      checkDomain(email);
    }
  }, [email]);

  const checkDomain = async (emailAddress) => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`http://localhost:8000/check-domain/${encodeURIComponent(emailAddress)}`);
      setDomainData(response.data);
    } catch (err) {
      console.error("Failed to check domain", err);
      setError("Failed to check domain information");
    } finally {
      setLoading(false);
    }
  };

  if (!email) return null;

  return (
    <div className="domain-checker">
      <h4>🌐 Domain Verification</h4>
      {loading ? (
        <div className="processing-container">
          <p>Checking domain...</p>
          <div className="loading-bar">
            <div className="loading-progress"></div>
          </div>
        </div>
      ) : error ? (
        <div className="error-message">
          {error}
          <button onClick={() => checkDomain(email)} className="retry-button">
            Retry
          </button>
        </div>
      ) : domainData ? (
        <div className={`domain-status ${domainData.status === 'Legit email' ? 'domain-legit' : 'domain-disposable'}`}>
          <p>
            <strong>Email:</strong> {domainData.email}
          </p>
          <p>
            <strong>Domain:</strong> {domainData.domain}
          </p>
          <p>
            <strong>Status:</strong> 
            <span className={domainData.status === 'Legit email' ? 'status-legit' : 'status-disposable'}>
              {domainData.status === 'Legit email' ? '✅ Legitimate Domain' : '❌ Disposable Email Domain'}
            </span>
          </p>
          {domainData.status !== 'Legit email' && (
            <div className="domain-warning">
              <p>⚠️ This email comes from a disposable email service. Exercise caution when interacting with this sender.</p>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

export default DomainChecker;

