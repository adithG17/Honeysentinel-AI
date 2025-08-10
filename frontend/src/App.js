import React, { useState } from "react";
import GmailReader from "./components/GmailReader";
import MessageAnalyzer from "./components/MessageAnalyzer";
import EmailAnalyzer from "./components/EmailAnalyzer";

import "./App.css";

function App() {
  const [active, setActive] = useState("gmail");

  const renderContent = () => {
    switch (active) {
      case "gmail":
        return <GmailReader />;
      case "message":
        return <MessageAnalyzer />;
      case "email":
        return <EmailAnalyzer />;
      case "image":
      default:
        return null;
    }
  };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <h2>📡 HoneyBadger 🛡️</h2>
        <ul>
          <li onClick={() => setActive("gmail")}>📬 Gmail Analyzer</li>
          <li onClick={() => setActive("message")}>💬 Message Analyzer</li>
          <li onClick={() => setActive("email")}>📧 Email Analyzer</li>
          <li onClick={() => setActive("image")}>🖼️ Image Analyzer</li>
          <li onClick={() => setActive("audio")}>🔊 Audio Analyzer</li>
          <li onClick={() => setActive("video")}>📹 Video Analyzer</li>
        </ul>
      </aside>
      <main className="content">{renderContent()}</main>
    </div>
  );
}

export default App;
