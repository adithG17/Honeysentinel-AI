import React from "react";
import "./App.css";
import MessageAnalyzer from "./components/MessageAnalyzer";
import EmailAnalyzer from "./components/EmailAnalyzer";
import FileAnalyzer from "./components/FileAnalyzer";
import GmailReader from "./components/GmailReader";

function App() {
  return (
    <div className="App">
      <h1>🐝 HoneySentinel AI</h1>
      <GmailReader />
      <MessageAnalyzer />
      <EmailAnalyzer />
      <FileAnalyzer type="image" />
      <FileAnalyzer type="audio" />
      <FileAnalyzer type="video" />
    </div>
  );
}

export default App;
