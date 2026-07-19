import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { jsPDF } from 'jspdf';

// Determine backend API and WebSocket endpoints dynamically based on the current host/port
const isDev = window.location.port === '5173';
const host = isDev ? '127.0.0.1:8000' : window.location.host;
const API_BASE = `${window.location.protocol}//${host}/api`;
const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${host}/api/ws`;

function App() {
  // Theme state (persisted in local storage)
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'dark';
  });

  // Form parameters state
  const [prefix, setPrefix] = useState('0105IT2410');
  const [start, setStart] = useState('1');
  const [end, setEnd] = useState('2');
  const [pad, setPad] = useState('2');
  const [sem, setSem] = useState('3');
  const [program, setProgram] = useState('B.Tech.');

  // Scrape job state
  const [jobState, setJobState] = useState({
    status: 'idle',
    total: 0,
    processed: 0,
    pass_count: 0,
    fail_count: 0,
    not_found_count: 0,
    error_count: 0,
    current_enrollment: '',
    excel_file_path: null,
    records: [],
    logs: []
  });

  // Selected student record for details modal
  const [selectedRecord, setSelectedRecord] = useState(null);

  // Terminal scroll reference
  const terminalEndRef = useRef(null);

  // Sync theme with body class and localStorage
  useEffect(() => {
    if (theme === 'light') {
      document.body.classList.add('light-theme');
    } else {
      document.body.classList.remove('light-theme');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Safe state merger to prevent crashes from missing fields
  const mergeStatus = (newData) => {
    setJobState(prev => ({
      status: newData.status || 'idle',
      total: newData.total ?? prev.total ?? 0,
      processed: newData.processed ?? prev.processed ?? 0,
      pass_count: newData.pass_count ?? prev.pass_count ?? 0,
      fail_count: newData.fail_count ?? prev.fail_count ?? 0,
      not_found_count: newData.not_found_count ?? prev.not_found_count ?? 0,
      error_count: newData.error_count ?? prev.error_count ?? 0,
      current_enrollment: newData.current_enrollment ?? prev.current_enrollment ?? '',
      excel_file_path: newData.excel_file_path ?? prev.excel_file_path ?? null,
      records: newData.records ?? prev.records ?? [],
      logs: newData.logs ?? prev.logs ?? []
    }));
  };

  // Auto-scroll terminal to bottom when new logs arrive
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [jobState.logs]);

  // Connect to WebSocket and sync status on load
  useEffect(() => {
    let socket;
    
    const connectWebSocket = () => {
      console.log("Connecting to WebSocket:", WS_URL);
      socket = new WebSocket(WS_URL);

      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "status") {
            mergeStatus(msg.data);
          } else if (msg.type === "log") {
            setJobState(prev => {
              const updatedLogs = [...prev.logs, msg.message];
              // Cap logs size at 500
              if (updatedLogs.length > 500) updatedLogs.shift();
              return { ...prev, logs: updatedLogs };
            });
          }
        } catch (e) {
          console.error("Error parsing socket message:", e);
        }
      };

      socket.onclose = (e) => {
        console.log("WebSocket disconnected. Reconnecting in 2 seconds...", e.reason);
        setTimeout(connectWebSocket, 2000);
      };

      socket.onerror = (err) => {
        console.error("WebSocket error:", err);
        socket.close();
      };
    };

    connectWebSocket();

    // Fetch initial status via HTTP
    fetch(`${API_BASE}/scrape/status`)
      .then(res => {
        if (!res.ok) throw new Error("Server not responding");
        return res.json();
      })
      .then(data => {
        if (data && data.status) {
          mergeStatus(data);
        }
      })
      .catch(err => console.error("Initial load fetch failed:", err));

    return () => {
      if (socket) socket.close();
    };
  }, []);

  // Actions
  const handleStart = async (e) => {
    e.preventDefault();
    if (!prefix || !start || !end) {
      alert("Please fill in all required fields.");
      return;
    }

    const payload = {
      prefix,
      start: parseInt(start),
      end: parseInt(end),
      pad: parseInt(pad),
      sem: sem || null,
      program
    };

    try {
      const response = await fetch(`${API_BASE}/scrape/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) {
        alert(data.detail || "Failed to start job");
      } else {
        mergeStatus(data.job);
      }
    } catch (err) {
      alert("Error contacting server: " + err.message);
    }
  };

  const handleCancel = async () => {
    try {
      const response = await fetch(`${API_BASE}/scrape/cancel`, { method: 'POST' });
      const data = await response.json();
      if (!response.ok) {
        alert(data.detail || "Failed to cancel job");
      }
    } catch (err) {
      alert("Error cancelling job: " + err.message);
    }
  };

  const handleDownload = () => {
    if (!jobState.excel_file_path) return;
    const url = `${API_BASE}/scrape/download?path=${encodeURIComponent(jobState.excel_file_path)}`;
    window.open(url, "_blank");
  };

  const downloadStudentPDF = (rec) => {
    const doc = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    });

    // 1. Top brand accent bar
    doc.setFillColor(124, 58, 237);
    doc.rect(0, 0, 210, 8, 'F');

    // 2. University / Official Header
    doc.setFont("helvetica", "bold");
    doc.setFontSize(20);
    doc.setTextColor(15, 23, 42); // slate-900
    doc.text("RAJIV GANDHI PROUDYOGIKI VISHWAVIDYALAYA", 105, 22, { align: "center" });

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(100, 116, 139); // slate-500
    doc.text("State Technological University of Madhya Pradesh", 105, 27, { align: "center" });
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.setTextColor(79, 70, 229); // indigo-600
    doc.text("ACADEMIC GRADE CARD", 105, 34, { align: "center" });

    // Divider Line
    doc.setDrawColor(203, 213, 225); // slate-300
    doc.setLineWidth(0.5);
    doc.line(15, 38, 195, 38);

    // 3. Student Details Section
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.setTextColor(15, 23, 42);
    doc.text("STUDENT PROFILE", 15, 46);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(51, 65, 85); // slate-700
    
    // Details layout
    doc.text(`Student Name :  ${rec.name || 'N/A'}`, 15, 53);
    doc.text(`Enrollment No:  ${rec.enrollment}`, 15, 59);
    doc.text(`Program      :  ${program || 'B.Tech.'}`, 120, 53);
    doc.text(`Semester     :  Semester ${sem || 'N/A'}`, 120, 59);

    doc.line(15, 64, 195, 64);

    // 4. Grades Table Section
    doc.setFont("helvetica", "bold");
    doc.text("SUBJECT-WISE GRADES", 15, 72);

    // Table Header
    doc.setFillColor(241, 245, 249); // slate-100
    doc.rect(15, 76, 180, 8, 'F');
    doc.setFontSize(9);
    doc.setTextColor(71, 85, 105); // slate-600
    doc.text("SUBJECT CODE", 20, 81.5);
    doc.text("GRADE OBTAINED", 150, 81.5);

    // Table Content
    let y = 90;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(15, 23, 42);

    if (rec.subjects && Object.keys(rec.subjects).length > 0) {
      Object.entries(rec.subjects).forEach(([subj, grade], idx) => {
        // Alternating row background for clean readability
        if (idx % 2 === 1) {
          doc.setFillColor(248, 250, 252); // slate-50
          doc.rect(15, y - 5, 180, 8, 'F');
        }
        
        doc.text(subj, 20, y);
        
        // Highlight F/Fail grades in red
        const isFailGrade = ['F', 'FAIL', 'AB', 'ABSENT', 'RL'].includes(grade.trim().toUpperCase());
        if (isFailGrade) {
          doc.setTextColor(239, 68, 68); // red-500
          doc.setFont("helvetica", "bold");
        } else {
          doc.setTextColor(15, 23, 42);
          doc.setFont("helvetica", "normal");
        }
        doc.text(grade, 150, y);
        doc.setTextColor(15, 23, 42);
        doc.setFont("helvetica", "normal");
        y += 8;
      });
    } else {
      doc.text("No subject grade records found.", 20, y);
      y += 8;
    }

    doc.line(15, y - 2, 195, y - 2);
    y += 8;

    // 5. Academic Summary Block
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.text("ACADEMIC PERFORMANCE SUMMARY", 15, y);
    y += 6;

    // Summary Box
    doc.setDrawColor(226, 232, 240); // slate-200
    doc.setFillColor(250, 250, 250);
    doc.rect(15, y - 4, 180, 24, 'FD');

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(51, 65, 85);
    doc.text(`Semester Grade Point Average (SGPA) :  ${rec.sgpa || '—'}`, 20, y + 2);
    doc.text(`Cumulative Grade Point Average (CGPA) :  ${rec.cgpa || '—'}`, 20, y + 8);
    
    // Result Text
    const isPass = rec.result === 'PASS';
    const isFail = rec.result && rec.result.toUpperCase().includes('FAIL');
    
    if (isPass) {
      doc.setTextColor(34, 197, 94); // success green
    } else if (isFail) {
      doc.setTextColor(239, 68, 68); // danger red
    } else {
      doc.setTextColor(245, 158, 11); // warning orange
    }
    
    doc.setFont("helvetica", "bold");
    doc.text(`RESULT STATUS                       :  ${rec.result || 'UNKNOWN'}`, 20, y + 14);

    // 6. Disclaimer Footer
    doc.setFont("helvetica", "italic");
    doc.setFontSize(8);
    doc.setTextColor(148, 163, 184); // slate-400
    doc.text("Disclaimer: This is a computer-generated grade card extracted from the official RGPV portal for immediate reference.", 105, 280, { align: "center" });

    // Save PDF
    doc.save(`RGPV_Result_${rec.enrollment}.pdf`);
  };

  // Derived Analytics Data
  const isRunning = jobState.status === 'running';
  
  // 1. Pass Rate percentage
  const totalGraded = jobState.pass_count + jobState.fail_count;
  const passRate = totalGraded > 0 ? Math.round((jobState.pass_count / totalGraded) * 100) : 0;
  
  // Circle chart stroke offset (377 is the circumference of radius 60 circle)
  const circleOffset = 377 - (377 * passRate) / 100;

  // 2. SGPA Distribution Buckets
  const sgpaRanges = {
    '< 5.0': 0,
    '5.0-6.0': 0,
    '6.0-7.0': 0,
    '7.0-8.0': 0,
    '8.0-9.0': 0,
    '> 9.0': 0,
  };

  if (jobState.records && Array.isArray(jobState.records)) {
    jobState.records.forEach(rec => {
      if (rec.not_found || !rec.sgpa) return;
      const sgpaVal = parseFloat(rec.sgpa);
      if (isNaN(sgpaVal)) return;

      if (sgpaVal < 5.0) sgpaRanges['< 5.0']++;
      else if (sgpaVal < 6.0) sgpaRanges['5.0-6.0']++;
      else if (sgpaVal < 7.0) sgpaRanges['6.0-7.0']++;
      else if (sgpaVal < 8.0) sgpaRanges['7.0-8.0']++;
      else if (sgpaVal < 9.0) sgpaRanges['8.0-9.0']++;
      else sgpaRanges['> 9.0']++;
    });
  }

  const sgpaMax = Math.max(...Object.values(sgpaRanges), 1);

  // 3. Subject Fail metrics
  const subjectStats = {};
  if (jobState.records && Array.isArray(jobState.records)) {
    jobState.records.forEach(rec => {
      if (rec.not_found || !rec.subjects) return;
      Object.entries(rec.subjects).forEach(([subj, grade]) => {
        if (!subjectStats[subj]) {
          subjectStats[subj] = { total: 0, failed: 0 };
        }
        subjectStats[subj].total++;
        if (['F', 'FAIL', 'AB', 'ABSENT', 'RL'].includes(grade.trim().toUpperCase())) {
          subjectStats[subj].failed++;
        }
      });
    });
  }

  // Parse terminal logs colors based on keywords
  const getLogStyle = (log) => {
    const l = log.toLowerCase();
    if (l.includes('guest@resultai') || l.startsWith('$')) {
      return { color: '#22C55E', fontWeight: '600' }; // Green command
    }
    if (l.includes('failed') || l.includes('error') || l.includes('timeout') || l.includes('exception') || l.includes('terminated')) {
      return { color: '#EF4444' }; // Red error
    }
    if (l.includes('warning') || l.includes('alert') || l.includes('action required') || l.includes('please solve')) {
      return { color: '#F59E0B' }; // Orange warning
    }
    if (l.includes('[scraper]') || l.includes('[system]')) {
      return { color: '#38BDF8' }; // Cyan info
    }
    return { color: '#FFFFFF' }; // White logs
  };

  return (
    <div className="app-container">
      {/* Blueprint grid layout lines background */}
      <div className="grid-overlay"></div>

      {/* HEADER */}
      <motion.header 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="app-header"
      >
        <div className="logo-container">
          <motion.div 
            initial={{ scale: 0.8 }} 
            animate={{ scale: 1 }} 
            className="logo-icon"
          >
            R
          </motion.div>
          <span className="logo-text">ResultAI</span>
        </div>
        <div className="header-actions">
          {/* Theme Toggle Button */}
          <button 
            className="theme-toggle-btn"
            onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          >
            {theme === 'dark' ? (
              <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="4"/>
                <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
              </svg>
            ) : (
              <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>
              </svg>
            )}
          </button>

          <div className="status-badge" style={{
            borderColor: isRunning ? 'var(--success)' : 'var(--card-border)',
            background: isRunning ? 'var(--success-bg)' : 'rgba(255,255,255,0.03)',
            color: isRunning ? 'var(--success)' : 'var(--text-muted)'
          }}>
            <span className={`dot ${isRunning ? 'pulse' : ''}`} style={{
              background: isRunning ? 'var(--success)' : 
                         jobState.status === 'completed' ? 'var(--info)' : 
                         jobState.status === 'cancelled' ? 'var(--danger)' : '#64748b'
            }}></span>
            {jobState.status}
          </div>
        </div>
      </motion.header>

      {/* DASHBOARD BODY */}
      <div className="dashboard-grid">
        {/* LEFT COLUMN: SIDEBAR CONTROL PANEL */}
        <motion.aside 
          initial={{ opacity: 0, x: -15 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4 }}
        >
          <h2 className="form-title">Scraper Control Room</h2>
          <form onSubmit={handleStart}>
            <div className="form-group">
              <label htmlFor="prefix">Enrollment Prefix</label>
              <input 
                id="prefix"
                type="text" 
                value={prefix} 
                onChange={(e) => setPrefix(e.target.value.toUpperCase())}
                placeholder="e.g. 0105IT2410"
                disabled={isRunning}
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="start">Start Roll</label>
                <input 
                  id="start"
                  type="number" 
                  value={start} 
                  onChange={(e) => setStart(e.target.value)}
                  min="1"
                  disabled={isRunning}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="end">End Roll</label>
                <input 
                  id="end"
                  type="number" 
                  value={end} 
                  onChange={(e) => setEnd(e.target.value)}
                  min="1"
                  disabled={isRunning}
                  required
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="pad">Padding</label>
                <input 
                  id="pad"
                  type="number" 
                  value={pad} 
                  onChange={(e) => setPad(e.target.value)}
                  min="1"
                  disabled={isRunning}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="sem">Semester</label>
                <select 
                  id="sem"
                  value={sem} 
                  onChange={(e) => setSem(e.target.value)}
                  disabled={isRunning}
                >
                  <option value="">(None - CLI default)</option>
                  <option value="1">Semester 1</option>
                  <option value="2">Semester 2</option>
                  <option value="3">Semester 3</option>
                  <option value="4">Semester 4</option>
                  <option value="5">Semester 5</option>
                  <option value="6">Semester 6</option>
                  <option value="7">Semester 7</option>
                  <option value="8">Semester 8</option>
                </select>
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: '24px' }}>
              <label htmlFor="program">Program Name</label>
              <select 
                id="program"
                value={program} 
                onChange={(e) => setProgram(e.target.value)}
                disabled={isRunning}
              >
                <option value="B.Tech.">B.Tech.</option>
                <option value="B.E.">B.E.</option>
                <option value="B.Pharmacy">B.Pharmacy.</option>
                <option value="M.Tech.">M.Tech.</option>
                <option value="MCA">MCA</option>
                <option value="MBA">MBA</option>
              </select>
            </div>

            {!isRunning ? (
              <motion.button 
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="btn btn-primary" 
                type="submit"
              >
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                Start Extraction
              </motion.button>
            ) : (
              <motion.button 
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="btn btn-danger" 
                type="button" 
                onClick={handleCancel}
              >
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                </svg>
                Cancel Scraping
              </motion.button>
            )}
          </form>

          {/* Auto CAPTCHA status indicator */}
          {isRunning && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                marginTop: '24px', 
                padding: '16px', 
                borderRadius: '12px', 
                background: 'var(--success-bg)',
                border: '1px solid rgba(34, 197, 94, 0.15)',
                fontSize: '12.5px',
                lineHeight: '1.5',
                boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
              }}
            >
              <p style={{ color: 'var(--success)', fontWeight: '800', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 12 18.713l2.188-2.81m-6.375-5.468L12 7.626l4.188 2.809M12 2.25c5.385 0 9.75 4.365 9.75 9.75s-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12 6.615 2.25 12 2.25Z" />
                </svg>
                AUTO CAPTCHA ACTIVE
              </p>
              <p style={{ color: 'var(--text-main)', opacity: 0.85 }}>
                CAPTCHAs are being auto-solved via OCR (ddddocr). The browser window is open for fallback — if auto-solve fails 5 times, you'll be asked to solve manually.
              </p>
            </motion.div>
          )}
        </motion.aside>

        {/* RIGHT COLUMN: MAIN PANEL */}
        <motion.main 
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}
        >
          {/* METRIC COUNTERS (Premium Cards with custom icon colors and borders) */}
          <section className="metrics-row">
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 }}
              className="metric-card" 
              style={{ '--accent-color': 'var(--primary)', '--icon-bg-color': 'rgba(124, 58, 237, 0.15)', '--card-hover-border': 'rgba(124, 58, 237, 0.4)' }}
            >
              <div className="metric-header">
                <span className="metric-label">Processed</span>
                <div className="metric-icon-wrapper">
                  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                    <circle cx="9" cy="7" r="4"/>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                  </svg>
                </div>
              </div>
              <div className="metric-value">
                {jobState.processed} / {jobState.total}
              </div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="metric-card" 
              style={{ '--accent-color': 'var(--success)', '--icon-bg-color': 'rgba(34, 197, 94, 0.15)', '--card-hover-border': 'rgba(34, 197, 94, 0.4)' }}
            >
              <div className="metric-header">
                <span className="metric-label">Passed</span>
                <div className="metric-icon-wrapper">
                  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22 4 12 14.01 9 11.01"/>
                  </svg>
                </div>
              </div>
              <div className="metric-value" style={{ color: 'var(--success)' }}>
                {jobState.pass_count}
              </div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="metric-card" 
              style={{ '--accent-color': 'var(--danger)', '--icon-bg-color': 'rgba(239, 68, 68, 0.15)', '--card-hover-border': 'rgba(239, 68, 68, 0.4)' }}
            >
              <div className="metric-header">
                <span className="metric-label">Failed</span>
                <div className="metric-icon-wrapper">
                  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="15" y1="9" x2="9" y2="15"/>
                    <line x1="9" y1="9" x2="15" y2="15"/>
                  </svg>
                </div>
              </div>
              <div className="metric-value" style={{ color: 'var(--danger)' }}>
                {jobState.fail_count}
              </div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="metric-card" 
              style={{ '--accent-color': '#64748b', '--icon-bg-color': 'rgba(100, 116, 139, 0.15)', '--card-hover-border': 'rgba(100, 116, 139, 0.4)' }}
            >
              <div className="metric-header">
                <span className="metric-label">Not Found</span>
                <div className="metric-icon-wrapper">
                  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                    <circle cx="11" cy="11" r="8"/>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    <line x1="11" y1="8" x2="11" y2="14"/>
                    <line x1="8" y1="11" x2="14" y2="11"/>
                  </svg>
                </div>
              </div>
              <div className="metric-value" style={{ color: '#94A3B8' }}>
                {jobState.not_found_count}
              </div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
              className="metric-card" 
              style={{ '--accent-color': 'var(--warning)', '--icon-bg-color': 'rgba(245, 158, 11, 0.15)', '--card-hover-border': 'rgba(245, 158, 11, 0.4)' }}
            >
              <div className="metric-header">
                <span className="metric-label">Errors</span>
                <div className="metric-icon-wrapper">
                  <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
                    <line x1="12" y1="9" x2="12" y2="13"/>
                    <line x1="12" y1="17" x2="12.01" y2="17"/>
                  </svg>
                </div>
              </div>
              <div className="metric-value" style={{ color: 'var(--warning)' }}>
                {jobState.error_count}
              </div>
            </motion.div>
          </section>

          {/* DUAL COLUMN ANALYTICS (CHARTS) */}
          {jobState.records && jobState.records.length > 0 && (
            <motion.section 
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="analytics-section"
            >
              {/* SGPA BAR CHART */}
              <div className="glass-panel">
                <h3 style={{ fontSize: '15px', fontWeight: '800', marginBottom: '14px' }}>SGPA Distribution</h3>
                <div className="chart-container">
                  {Object.entries(sgpaRanges).map(([range, count]) => {
                    const heightPercent = count > 0 ? (count / sgpaMax) * 80 : 2;
                    
                    // Assign colors to bars based on their ranges for a premium SaaS look
                    let barBg = 'var(--primary-gradient)';
                    if (range.includes('< 5.0')) barBg = 'linear-gradient(to top, #EF4444, #f43f5e)';
                    else if (range.includes('5.0')) barBg = 'linear-gradient(to top, #F59E0B, #fbbf24)';
                    else if (range.includes('6.0')) barBg = 'linear-gradient(to top, #3b82f6, #38bdf8)';
                    else if (range.includes('9.0') || range.includes('>')) barBg = 'linear-gradient(to top, #22C55E, #4ade80)';

                    return (
                      <div className="chart-bar-wrapper" key={range}>
                        <div 
                          className="chart-bar" 
                          style={{ height: `${heightPercent}%`, background: barBg }}
                        >
                          <div className="chart-bar-tooltip">{count} Student{count !== 1 ? 's' : ''}</div>
                        </div>
                        <span className="chart-label">{range}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* CIRCULAR PASS RATE */}
              <div className="glass-panel" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', position: 'relative' }}>
                <div className="circular-progress-container">
                  <svg className="circular-svg" viewBox="0 0 140 140">
                    <defs>
                      <linearGradient id="purple-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#7C3AED" />
                        <stop offset="100%" stopColor="#4F46E5" />
                      </linearGradient>
                    </defs>
                    <circle className="circular-bg" cx="70" cy="70" r="60" />
                    <circle className="circular-fill" cx="70" cy="70" r="60" style={{ strokeDashoffset: circleOffset }} />
                  </svg>
                  <div className="circular-text">
                    <span className="circular-percent">{passRate}%</span>
                    <span className="circular-label">Pass Rate</span>
                  </div>
                </div>
              </div>
            </motion.section>
          )}

          {/* LIVE TERMINAL LOGS (Vercel Style Vibe) */}
          <section className="glass-panel terminal-card">
            <div className="terminal-header">
              <span style={{ fontSize: '14px', fontWeight: '800' }}>Terminal Logger</span>
              <div className="terminal-controls">
                <span className="term-dot red"></span>
                <span className="term-dot yellow"></span>
                <span className="term-dot green"></span>
              </div>
            </div>
            <div className="terminal-viewport">
              {!jobState.logs || jobState.logs.length === 0 ? (
                <div className="terminal-line" style={{ color: 'var(--text-muted)', opacity: 0.65 }}>
                  <span style={{ color: '#22C55E' }}>guest@resultai:~$</span> idle --listen
                  <br />
                  <span style={{ color: 'var(--text-muted)' }}>[System] Ready. Configure scraper inputs and click "Start Extraction" to run.</span>
                </div>
              ) : (
                jobState.logs.map((log, idx) => {
                  const itemStyle = getLogStyle(log);
                  return (
                    <div className="terminal-line" key={idx} style={itemStyle}>
                      <span style={{ color: 'rgba(255,255,255,0.12)', marginRight: '10px', fontSize: '11px', userSelect: 'none' }}>
                        {(idx + 1).toString().padStart(3, '0')}
                      </span>
                      {log}
                    </div>
                  );
                })
              )}
              <div ref={terminalEndRef} />
            </div>
          </section>

          {/* STUDENTS RESULTS GRID */}
          <section className="glass-panel">
            <div className="table-section-header">
              <h3 style={{ fontSize: '16px', fontWeight: '800' }}>Extracted Student Records</h3>
              {jobState.excel_file_path && (
                <motion.button 
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="btn btn-secondary" 
                  onClick={handleDownload} 
                  style={{ width: 'auto', padding: '6px 14px', borderRadius: '6px', fontSize: '13px' }}
                >
                  <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24" style={{ marginRight: '4px' }}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                  Download Excel
                </motion.button>
              )}
            </div>

            {!jobState.records || jobState.records.length === 0 ? (
              <motion.div 
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="empty-state"
                style={{ padding: '60px 40px', gap: '24px' }}
              >
                <div style={{
                  background: 'rgba(124, 58, 237, 0.05)',
                  border: '1px solid rgba(124, 58, 237, 0.15)',
                  width: '74px',
                  height: '74px',
                  borderRadius: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--primary)',
                  boxShadow: '0 8px 24px rgba(124, 58, 237, 0.08)'
                }}>
                  <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 13.5h3.86a2.25 2.25 0 0 1 2.008 1.24l.885 1.77a2.25 2.25 0 0 0 2.007 1.24h1.98a2.25 2.25 0 0 0 2.007-1.24l.885-1.77a2.25 2.25 0 0 1 2.007-1.24h3.86m-18 0h18M2.25 13.5v-6a2.25 2.25 0 0 1 2.25-2.25h15A2.25 2.25 0 0 1 21.75 7.5v6m-19.5 0v6a2.25 2.25 0 0 0 2.25 2.25h15a2.25 2.25 0 0 0 2.25-2.25v-6" />
                  </svg>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <h4 style={{ fontSize: '16px', fontWeight: '800', color: 'var(--title-color)' }}>No Academic Records Loaded</h4>
                  <p style={{ color: 'var(--text-muted)', fontSize: '14px', maxWidth: '360px', margin: '0 auto', lineHeight: '1.6' }}>
                    Configure the enrollment prefix, roll ranges, and program in the control room sidebar, then click "Start Extraction" to pull real-time results from the RGPV portal.
                  </p>
                </div>
              </motion.div>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Enrollment</th>
                      <th>Student Name</th>
                      <th>Result</th>
                      <th>SGPA</th>
                      <th>CGPA</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobState.records.map((rec, idx) => (
                      <tr key={idx}>
                        <td className="subject-code">{rec.enrollment}</td>
                        <td style={{ fontWeight: '500', color: 'var(--title-color)' }}>{rec.not_found ? '—' : rec.name}</td>
                        <td>
                          {rec.not_found ? (
                            <span className="badge not-found">Not Found</span>
                          ) : rec.result === 'PASS' ? (
                            <span className="badge pass">PASS</span>
                          ) : rec.result === 'FAIL' ? (
                            <span className="badge fail">FAIL</span>
                          ) : (
                            <span className="badge unknown">UNKNOWN</span>
                          )}
                        </td>
                        <td style={{ fontWeight: '700' }}>{rec.not_found ? '—' : (rec.sgpa || 'N/A')}</td>
                        <td style={{ fontWeight: '700' }}>{rec.not_found ? '—' : (rec.cgpa || 'N/A')}</td>
                         <td>
                           {!rec.not_found && (
                             <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                               <button 
                                 className="btn btn-secondary" 
                                 onClick={() => setSelectedRecord(rec)}
                                 style={{ padding: '4px 10px', fontSize: '11px', width: 'auto', borderRadius: '6px', whiteSpace: 'nowrap' }}
                               >
                                 View Grades
                               </button>
                               <button 
                                 className="btn btn-primary" 
                                 onClick={() => downloadStudentPDF(rec)}
                                 style={{ padding: '5px 8px', width: 'auto', borderRadius: '6px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: 'var(--primary-gradient)' }}
                                 title="Download PDF"
                               >
                                 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                   <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
                                 </svg>
                               </button>
                             </div>
                           )}
                         </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </motion.main>
      </div>

      {/* STUDENT GRADES DETAIL MODAL (With Framer Motion animate overlays) */}
      <AnimatePresence>
        {selectedRecord && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="modal-overlay" 
            onClick={() => setSelectedRecord(null)}
          >
            <motion.div 
              initial={{ scale: 0.96, opacity: 0, y: 15 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.96, opacity: 0, y: 15 }}
              transition={{ type: 'spring', damping: 25, stiffness: 350 }}
              className="modal-content" 
              onClick={(e) => e.stopPropagation()}
            >
              <div className="modal-header">
                <h3 className="modal-title">Subject-wise Grades</h3>
                <button className="close-btn" onClick={() => setSelectedRecord(null)}>×</button>
              </div>
              <div style={{ marginBottom: '18px', borderBottom: '1px solid var(--card-border)', paddingBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <p style={{ fontSize: '14.5px', fontWeight: '800', color: 'var(--title-color)' }}>{selectedRecord.name}</p>
                  <p style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Enrollment: {selectedRecord.enrollment}</p>
                </div>
                <button 
                  className="btn btn-primary"
                  onClick={() => downloadStudentPDF(selectedRecord)}
                  style={{ padding: '8px 14px', width: 'auto', fontSize: '12px', borderRadius: '8px', display: 'inline-flex', alignItems: 'center' }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px' }}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                  Download PDF
                </button>
              </div>
              <div className="grades-grid">
                <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Subject Code</span>
                <span style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', textAlign: 'right' }}>Grade</span>
                
                {selectedRecord.subjects && Object.entries(selectedRecord.subjects).map(([subj, grade]) => {
                  const isFailGrade = ['F', 'FAIL', 'AB', 'ABSENT', 'RL'].includes(grade.trim().toUpperCase());
                  return (
                    <div className="grade-row" key={subj}>
                      <span className="subject-code" style={{ fontSize: '13px' }}>{subj}</span>
                      <span 
                        className={`subject-grade ${isFailGrade ? 'fail-grade' : ''}`}
                        style={{ textAlign: 'right', fontSize: '12px' }}
                      >
                        {grade}
                      </span>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
