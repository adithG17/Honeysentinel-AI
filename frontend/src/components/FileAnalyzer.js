import React, { useState } from "react";

function FileAnalyzer({ type }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);

  const analyze = async () => {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`/analyze/${type}`, {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    setResult(data);
  };

  return (
    <div>
      <h2>{type.charAt(0).toUpperCase() + type.slice(1)} Analyzer</h2>
      <input
        type="file"
        accept={`${type}/*`}
        onChange={(e) => setFile(e.target.files[0])}
      />
      <button onClick={analyze} disabled={!file}>
        Analyze
      </button>
      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </div>
  );
}

export default FileAnalyzer;
