import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [previewKey, setPreviewKey] = useState(Date.now()); // Unique key for iframe reload
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    setMessages(prev => [...prev, { type: 'user', content: input }]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post('http://localhost:5000/api/process', { prompt: input });
      const { response: assistantResponse, status } = response.data;
      setMessages(prev => [
        ...prev,
        { type: 'assistant', content: assistantResponse },
        ...(status ? [{ type: 'system', content: status }] : [])
      ]);
      // Update preview key if a file was changed
      if (status && (status.includes('Updated') || status.includes('Created') || status.includes('Appended'))) {
        setPreviewKey(Date.now()); // Forces iframe reload
      }
    } catch (error) {
      console.error('API Error:', error.message, error.response?.status, error.response?.data);
      setMessages(prev => [...prev, { type: 'system', content: `Error: Could not process request. ${error.message}` }]);
    }

    setIsLoading(false);
  };

  return (
    <div className="app">
      <div className="chat-container">
        <header className="header">
          <h1 className="header-title">AI Assistant</h1>
        </header>

        <div className="main-content">
          <div className="messages">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`message ${message.type === 'user' ? 'user-message' : message.type === 'system' ? 'system-message' : 'assistant-message'}`}
              >
                <div className="message-content">
                  {message.content}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="loading">
                <span>AI is thinking...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="preview">
            <h2>Live Preview</h2>
            <iframe
              src={`http://localhost:5000/files/index.html?t=${previewKey}`}
              title="Live Preview"
              className="preview-iframe"
            />
          </div>
        </div>

        <form onSubmit={handleSubmit} className="input-form">
          <div className="input-wrapper">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              className="input-field"
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="send-button"
            >
              <span>Send</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default App;