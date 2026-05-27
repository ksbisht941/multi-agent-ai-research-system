import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageSquare, 
  Send, 
  Plus, 
  Terminal, 
  Settings, 
  Cpu, 
  CheckCircle, 
  XCircle, 
  Search, 
  FileText, 
  TrendingUp, 
  Calculator, 
  Calendar, 
  ChevronDown, 
  ChevronUp, 
  AlertTriangle,
  FileDown,
  BookOpen,
  HelpCircle,
  RefreshCw
} from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function App() {
  // ── State Management ─────────────────────────────────────────────────────
  const [threads, setThreads] = useState([]);
  const [activeThread, setActiveThread] = useState('');
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  
  const [serverOnline, setServerOnline] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [isSending, setIsSending] = useState(false);
  
  // Streaming message buffer
  const [streamingText, setStreamingText] = useState('');
  const [streamingTools, setStreamingTools] = useState([]);
  const [streamingCitations, setStreamingCitations] = useState([]);
  const [streamingPdf, setStreamingPdf] = useState(null);

  // Human-in-the-Loop Interrupt Approval state
  const [approvalRequired, setApprovalRequired] = useState(null);

  const messagesEndRef = useRef(null);

  // ── Effects & Initialization ─────────────────────────────────────────────
  useEffect(() => {
    checkServerStatus();
    fetchThreads();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText, streamingTools]);

  const checkServerStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/status`);
      const data = await res.json();
      setServerOnline(data.status === 'online');
    } catch (e) {
      setServerOnline(false);
    }
  };

  const fetchThreads = async () => {
    try {
      const res = await fetch(`${API_BASE}/threads`);
      const data = await res.json();
      setThreads(data.threads || []);
      if (data.threads && data.threads.length > 0) {
        selectThread(data.threads[0]);
      } else {
        startNewThread();
      }
    } catch (e) {
      console.error("Error loading threads:", e);
    }
  };

  const selectThread = (threadId) => {
    setActiveThread(threadId);
    setMessages([]);
    setStreamingText('');
    setStreamingTools([]);
    setStreamingCitations([]);
    setStreamingPdf(null);
    setApprovalRequired(null);
    
    // In production we could fetch previous messages of the thread.
    // For now we start with a clean UI, since checkpointer persists state backend.
    setMessages([
      {
        id: 'welcome',
        sender: 'assistant',
        text: `Conversation loaded. Ready to assist on thread: \n\`${threadId}\``
      }
    ]);
  };

  const startNewThread = () => {
    const newId = crypto.randomUUID();
    setThreads(prev => [newId, ...prev]);
    selectThread(newId);
  };

  const triggerIndexing = async () => {
    setIndexing(true);
    try {
      const res = await fetch(`${API_BASE}/index`, { method: 'POST' });
      const data = await res.json();
      alert(`[RAG Indexer] ${data.message}`);
      checkServerStatus();
    } catch (e) {
      alert(`[RAG Indexer Error] Failed to index: ${e.message}`);
    } finally {
      setIndexing(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // ── Parse Tool Output Data ───────────────────────────────────────────────
  const extractToolData = (toolOutputStr, toolName) => {
    try {
      // Clean Python representations so they can be JSON parsed
      let cleaned = toolOutputStr
        .replace(/'/g, '"')
        .replace(/True/g, 'true')
        .replace(/False/g, 'false')
        .replace(/None/g, 'null');
      
      // Parse output
      const data = JSON.parse(cleaned);
      return data;
    } catch (e) {
      return null;
    }
  };

  // ── Process SSE Stream completions ─────────────────────────────────────────
  const handleStreamResponse = async (response) => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    let textAccumulator = '';
    let toolsAccumulator = [];
    let citationsAccumulator = [];
    let pdfAccumulator = null;

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue;
          
          const payload = JSON.parse(line.slice(6));
          
          if (payload.event === 'token') {
            textAccumulator += payload.text;
            setStreamingText(textAccumulator);
          } 
          
          else if (payload.event === 'tool_end') {
            const outputText = payload.output;
            let displayName = "Agent Tool";
            let icon = Cpu;
            let displayArgs = "";
            let displayResult = outputText;

            // Intelligently parse tool output to display premium widgets
            if (outputText.includes("calculator")) {
              displayName = "Arithmetic Calculator";
              icon = Calculator;
            } else if (outputText.includes("get_stock_price")) {
              displayName = "Stock Price Checker";
              icon = TrendingUp;
            } else if (outputText.includes("duckduckgo_search")) {
              displayName = "DuckDuckGo Live Search";
              icon = Search;
            } else if (outputText.includes("rag_tool")) {
              displayName = "Melanoma Study Reference Tool";
              icon = BookOpen;
              
              // Extract RAG passages to display in the citations panel
              const parsed = extractToolData(outputText, "rag_tool");
              if (parsed && parsed.rag_tool) {
                const ragData = parsed.rag_tool;
                if (ragData.context && ragData.context.length > 0) {
                  const chunks = ragData.context.map((text, idx) => ({
                    text,
                    page: ragData.metadata[idx]?.page || 'Unknown',
                    source: ragData.metadata[idx]?.source || 'PDF'
                  }));
                  citationsAccumulator = [...citationsAccumulator, ...chunks];
                  setStreamingCitations(citationsAccumulator);
                }
              }
            } else if (outputText.includes("generate_day_plan")) {
              displayName = "Productivity Day Planner";
              icon = Calendar;
            } else if (outputText.includes("generate_schedule_pdf")) {
              displayName = "PDF Schedule Generator";
              icon = FileText;
              
              // Extract PDF file name to show download widget
              const parsed = extractToolData(outputText, "generate_schedule_pdf");
              if (parsed && parsed.generate_schedule_pdf) {
                const pdfData = parsed.generate_schedule_pdf;
                if (pdfData.status === 'success' && pdfData.file_path) {
                  pdfAccumulator = pdfData.file_path;
                  setStreamingPdf(pdfAccumulator);
                }
              }
            }

            toolsAccumulator.push({
              name: displayName,
              icon: icon,
              output: outputText,
              expanded: false
            });
            setStreamingTools([...toolsAccumulator]);
          } 
          
          else if (payload.event === 'interrupt') {
            // Open approval modal and halt processing
            setApprovalRequired({
              tool_name: payload.tool_name,
              query: payload.query
            });
            setIsSending(false);
            return;
          } 
          
          else if (payload.event === 'done') {
            // Finalize streaming
            finalizeStreamedMessage(textAccumulator, toolsAccumulator, citationsAccumulator, pdfAccumulator);
            return;
          }
          
          else if (payload.event === 'error') {
            alert(`Stream Error: ${payload.message}`);
          }
        }
      }
    } catch (e) {
      console.error("Stream reading error:", e);
    } finally {
      setIsSending(false);
    }
  };

  const finalizeStreamedMessage = (text, tools, citations, pdf) => {
    setMessages(prev => [
      ...prev,
      {
        id: crypto.randomUUID(),
        sender: 'assistant',
        text: text || "Tool execution completed.",
        tools: tools,
        citations: citations,
        pdf: pdf
      }
    ]);
    
    // Clear stream buffers
    setStreamingText('');
    setStreamingTools([]);
    setStreamingCitations([]);
    setStreamingPdf(null);
    setIsSending(false);
  };

  // ── Send Message ─────────────────────────────────────────────────────────
  const sendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!inputValue.trim() || isSending) return;

    const userMessage = inputValue;
    setInputValue('');
    setIsSending(true);

    // Append user message immediately
    setMessages(prev => [
      ...prev,
      {
        id: crypto.randomUUID(),
        sender: 'user',
        text: userMessage
      }
    ]);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: activeThread,
          message: userMessage
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await handleStreamResponse(response);

    } catch (err) {
      console.error("Error sending chat message:", err);
      alert("Failed to connect to API server. Make sure the FastAPI server is running.");
      setIsSending(false);
    }
  };

  // ── Resolve Approval Interrupt ───────────────────────────────────────────
  const submitApproval = async (decision) => {
    if (!approvalRequired) return;
    
    setApprovalRequired(null);
    setIsSending(true);

    try {
      const response = await fetch(`${API_BASE}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: activeThread,
          approved: decision
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await handleStreamResponse(response);

    } catch (err) {
      console.error("Error submitting approval:", err);
      setIsSending(false);
    }
  };

  // ── Helper Icon Selector ──
  const getToolIcon = (ToolIcon) => {
    return ToolIcon ? <ToolIcon className="tool-icon" size={16} /> : <Cpu className="tool-icon" size={16} />;
  };

  return (
    <div className="app-container">
      
      {/* ── SIDEBAR PANEL ── */}
      <aside className="sidebar glass-panel">
        <div className="logo-container">
          <Cpu className="logo-icon" size={28} />
          <span className="logo-text">LANGGRAPH WORKSPACE</span>
        </div>

        <div className="server-status">
          <span className={`status-indicator ${serverOnline ? 'online' : 'offline'}`}></span>
          <span>Backend Server: <b>{serverOnline ? 'ONLINE' : 'OFFLINE'}</b></span>
        </div>

        <button className="glow-btn" onClick={startNewThread} style={{ width: '100%', marginBottom: '20px' }}>
          <Plus size={18} />
          New Thread
        </button>

        <div className="thread-list-container">
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'hsl(var(--text-muted))', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Active Threads ({threads.length})
          </span>
          {threads.map((tid) => (
            <div 
              key={tid} 
              className={`thread-item ${activeThread === tid ? 'active' : ''}`}
              onClick={() => selectThread(tid)}
            >
              <MessageSquare size={16} style={{ color: activeThread === tid ? 'hsl(var(--accent-cyan))' : 'hsl(var(--text-secondary))' }} />
              <span className="thread-id-text">{tid}</span>
            </div>
          ))}
        </div>

        <div className="indexing-panel">
          <span className="indexing-title">RAG Data Engine</span>
          <button 
            className="indexing-btn" 
            onClick={triggerIndexing} 
            disabled={indexing || !serverOnline}
          >
            <RefreshCw size={16} className={indexing ? 'animate-spin' : ''} />
            {indexing ? 'Indexing document...' : 'Index Melanoma PDF'}
          </button>
        </div>
      </aside>

      {/* ── MAIN CHAT AREA ── */}
      <main className="chat-area glass-panel">
        <header className="chat-header">
          <div className="active-thread-info">
            <span className="active-thread-title">Assistant Session</span>
            {activeThread && <span className="active-thread-id">{activeThread}</span>}
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <span style={{ fontSize: '0.8rem', color: 'hsl(var(--text-secondary))', background: 'rgba(255,255,255,0.03)', padding: '6px 12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
              Memory limit: <b>1000 tokens</b>
            </span>
          </div>
        </header>

        {/* ── MESSAGES COMPONENT ── */}
        <div className="chat-messages">
          {messages.map((msg) => (
            <div key={msg.id} className={`message-wrapper ${msg.sender}`}>
              <span className="message-sender">{msg.sender === 'user' ? 'You' : 'Agent'}</span>
              <div className="message-bubble">
                <p style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</p>
                
                {/* PDF Download Button */}
                {msg.pdf && (
                  <div>
                    <a 
                      href={`${API_BASE}/pdf/${msg.pdf}`} 
                      className="download-pdf-btn"
                      target="_blank" 
                      rel="noopener noreferrer"
                    >
                      <FileDown size={16} />
                      Download Daily Schedule ({msg.pdf})
                    </a>
                  </div>
                )}

                {/* Citations Panel */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="citation-container">
                    <details className="citation-body">
                      <summary className="citation-header">
                        <BookOpen size={14} />
                        Source Literature Citations ({msg.citations.length})
                      </summary>
                      {msg.citations.map((cite, idx) => (
                        <div key={idx} className="citation-item">
                          <p>"{cite.text}"</p>
                          <div className="citation-meta">
                            <span>Page: {cite.page}</span>
                            <span>Document: {cite.source.split('/').pop()}</span>
                          </div>
                        </div>
                      ))}
                    </details>
                  </div>
                )}
                
                {/* Tool Collapsible Cards */}
                {msg.tools && msg.tools.map((t, idx) => (
                  <div key={idx} className="tool-card">
                    <details>
                      <summary className="tool-header">
                        <div className="tool-title">
                          {getToolIcon(t.icon)}
                          {t.name}
                        </div>
                        <span className="tool-status success">Executed</span>
                      </summary>
                      <div className="tool-body">
                        <pre style={{ whiteSpace: 'pre-wrap' }}>{t.output}</pre>
                      </div>
                    </details>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* Active SSE Streaming message */}
          {(streamingText || streamingTools.length > 0) && (
            <div className="message-wrapper assistant">
              <span className="message-sender">Agent</span>
              <div className="message-bubble">
                {streamingText && (
                  <p style={{ whiteSpace: 'pre-wrap' }}>
                    {streamingText}
                    {isSending && <span className="typing-cursor"></span>}
                  </p>
                )}

                {/* Streaming PDF Download Button */}
                {streamingPdf && (
                  <div>
                    <a 
                      href={`${API_BASE}/pdf/${streamingPdf}`} 
                      className="download-pdf-btn"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <FileDown size={16} />
                      Download Daily Schedule ({streamingPdf})
                    </a>
                  </div>
                )}

                {/* Streaming Citations */}
                {streamingCitations.length > 0 && (
                  <div className="citation-container">
                    <details className="citation-body" open>
                      <summary className="citation-header">
                        <BookOpen size={14} />
                        Source Literature Citations ({streamingCitations.length})
                      </summary>
                      {streamingCitations.map((cite, idx) => (
                        <div key={idx} className="citation-item">
                          <p>"{cite.text}"</p>
                          <div className="citation-meta">
                            <span>Page: {cite.page}</span>
                            <span>Document: {cite.source.split('/').pop()}</span>
                          </div>
                        </div>
                      ))}
                    </details>
                  </div>
                )}

                {/* Streaming Tools Cards */}
                {streamingTools.map((t, idx) => (
                  <div key={idx} className="tool-card">
                    <details>
                      <summary className="tool-header">
                        <div className="tool-title">
                          {getToolIcon(t.icon)}
                          {t.name}
                        </div>
                        <span className="tool-status success">Executed</span>
                      </summary>
                      <div className="tool-body">
                        <pre style={{ whiteSpace: 'pre-wrap' }}>{t.output}</pre>
                      </div>
                    </details>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* ── CHAT INPUT FOOTER ── */}
        <footer className="chat-footer">
          <form className="chat-input-form" onSubmit={sendMessage}>
            <input 
              type="text" 
              className="chat-input"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={isSending ? "Agent is typing..." : "Ask your assistant (e.g., 'Plan my day', 'Search the web for AI', 'Review YOLO melanoma study')"}
              disabled={isSending || !serverOnline}
            />
            <button className="glow-btn" type="submit" disabled={isSending || !inputValue.trim() || !serverOnline}>
              <Send size={16} />
              Send
            </button>
          </form>
        </footer>
      </main>

      {/* ── HUMAN-IN-THE-LOOP APPROVAL MODAL ── */}
      {approvalRequired && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel">
            <div className="modal-header">
              <AlertTriangle className="modal-icon" size={24} />
              <span>Human Approval Required</span>
            </div>
            <p className="modal-description">
              The agent wants to execute a live **DuckDuckGo Web Search** to retrieve external information. 
              Review the search query below and approve or reject this request.
            </p>
            <div className="modal-query-box">
              {approvalRequired.query}
            </div>
            <div className="modal-actions">
              <button className="btn-reject" onClick={() => submitApproval('no')}>
                Reject Search
              </button>
              <button className="btn-approve" onClick={() => submitApproval('yes')}>
                Approve & Execute
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
