import React, { useState, useEffect } from 'react';
import axios from 'axios';

function DomainChecker({ email }) {
  const [domainData, setDomainData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showWhois, setShowWhois] = useState(false);

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

  const renderWhoisInfo = () => {
    if (!domainData?.whois_info) return null;

    const whoisData = domainData.whois_info;

    if (!whoisData.success) {
      return (
        <div className="whois-error">
          <p><strong>WHOIS Lookup:</strong> Failed - {whoisData.error}</p>
        </div>
      );
    }

    const data = whoisData.data;
    return (
      <div className="whois-details">
        <h5>🌐 WHOIS Information</h5>
        
        {data.registrar && (
          <p><strong>Registrar:</strong> {data.registrar}</p>
        )}
        
        {data.creation_date && (
          <p><strong>Registered:</strong> {data.creation_date}</p>
        )}
        
        {domainData.domain_age_years && (
          <p>
            <strong>Domain Age:</strong> 
            <span className={domainData.domain_age_years > 1 ? 'domain-old' : 'domain-new'}>
              {domainData.domain_age_years} years ({domainData.domain_age_analysis})
            </span>
          </p>
        )}
        
        {data.expiration_date && (
          <p><strong>Expires:</strong> {data.expiration_date}</p>
        )}
        
        {data.name_servers && data.name_servers.length > 0 && (
          <p><strong>Name Servers:</strong> {data.name_servers.slice(0, 2).join(', ')}</p>
        )}
        
        {data.status && (
          <p><strong>Status:</strong> {Array.isArray(data.status) ? data.status.join(', ') : data.status}</p>
        )}
        
        {data.country && (
          <p><strong>Country:</strong> {data.country}</p>
        )}
        
        {data.org && (
          <p><strong>Organization:</strong> {data.org}</p>
        )}
      </div>
    );
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
            <strong>Email:</strong> <span className="domain-info">{domainData.email}</span>
          </p>
          <p>
            <strong>Domain:</strong> <span className="domain-info">{domainData.domain}</span>
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

          {/* WHOIS Toggle Button */}
          <button 
            onClick={() => setShowWhois(!showWhois)} 
            className="whois-toggle-button"
          >
            {showWhois ? '▲ Hide WHOIS Details' : '▼ Show WHOIS Details'}
          </button>

          {/* WHOIS Information */}
          {showWhois && renderWhoisInfo()}
        </div>
      ) : null}
    </div>
  );
}

export default DomainChecker;