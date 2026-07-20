import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { jsPDF } from 'jspdf';
import ResultCompareStudio from './ResultCompareStudio';

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

  // Navigation tab state
  const [activeTab, setActiveTab] = useState('extractor'); // extractor, compare, or report

  // Report Generator state
  const [reportForm, setReportForm] = useState({
    excel_path: '',
    compare_path: '',
    college_name: 'Rajiv Gandhi Proudyogiki Vishwavidyalaya',
    department: 'Department of Information Technology',
    semester: '',
    program: 'B.Tech.',
    job_id: '',
    max_student_pages: 100
  });
  const [reportStatus, setReportStatus] = useState('idle'); // idle, generating, done, error
  const [reportPath, setReportPath] = useState(null);
  const [reportError, setReportError] = useState(null);
  const [reportLogs, setReportLogs] = useState([]);

  // Terminal scroll reference
  const terminalEndRef = useRef(null);

  // File Upload refs & state for Report Generator
  const reportFileInputRef = useRef(null);
  const reportCompareInputRef = useRef(null);
  const [uploadingFile, setUploadingFile] = useState(null); // null, 'excel', or 'compare'

  const handleReportFileUpload = async (file, type) => {
    setUploadingFile(type);
    setReportLogs(l => [...l, `[INFO] Uploading file: ${file.name}...`]);
    try {
      const res = await fetch(`${API_BASE}/report/upload?filename=${encodeURIComponent(file.name)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/octet-stream' },
        body: file
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');
      
      setReportForm(f => ({
        ...f,
        [type === 'excel' ? 'excel_path' : 'compare_path']: data.excel_path
      }));
      setReportLogs(l => [...l, `[OK] File uploaded successfully: ${data.excel_path}`]);
    } catch (err) {
      setReportLogs(l => [...l, `[ERR] Upload failed: ${err.message}`]);
    } finally {
      setUploadingFile(null);
    }
  };

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
      program,
      headless: true
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

        {/* Navigation Tabs */}
        <div style={{ display: 'flex', gap: '4px', background: 'rgba(255,255,255,0.02)', padding: '4px', borderRadius: '8px', border: '1px solid var(--card-border)' }}>
          <button 
            className="tab-btn" 
            style={{
              background: activeTab === 'extractor' ? 'var(--primary-gradient)' : 'transparent',
              color: activeTab === 'extractor' ? '#FFFFFF' : 'var(--text-muted)',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '700',
              fontSize: '12px'
            }}
            onClick={() => setActiveTab('extractor')}
          >
            Result Extractor
          </button>
          <button 
            className="tab-btn" 
            style={{
              background: activeTab === 'compare' ? 'var(--primary-gradient)' : 'transparent',
              color: activeTab === 'compare' ? '#FFFFFF' : 'var(--text-muted)',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '700',
              fontSize: '12px'
            }}
            onClick={() => setActiveTab('compare')}
          >
            Result Compare Studio
          </button>
          <button
            className="tab-btn"
            style={{
              background: activeTab === 'report' ? 'linear-gradient(135deg, #059669, #0CA5A5)' : 'transparent',
              color: activeTab === 'report' ? '#FFFFFF' : 'var(--text-muted)',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '700',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
            onClick={() => setActiveTab('report')}
          >
            <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
            AI Report Generator
          </button>
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
      {activeTab === 'report' && (
        <motion.div
          key="report"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -16 }}
          transition={{ duration: 0.35 }}
          style={{ padding: '28px 32px', maxWidth: '960px', margin: '0 auto', width: '100%' }}
        >
          {/* Page Title */}
          <div style={{ marginBottom: '28px' }}>
            <h1 style={{ fontSize: '26px', fontWeight: '900', color: 'var(--text-main)', margin: 0, display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ background: 'linear-gradient(135deg, #059669, #0CA5A5)', borderRadius: '10px', padding: '8px 10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <svg width="20" height="20" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                </svg>
              </span>
              AI Report Generator
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '13.5px', marginTop: '6px', marginLeft: '52px' }}>
              Generate a professional 40–50 page PDF report with charts, AI insights, and recommendations from scraped Excel data.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', alignItems: 'start' }}>

            {/* LEFT: Configuration Form */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: '800', color: 'var(--text-main)', marginBottom: '20px', textTransform: 'uppercase', letterSpacing: '0.08em', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <svg width="14" height="14" fill="none" stroke="#059669" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                  <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
                </svg>
                Report Configuration
              </h3>

              {/* Drag & Drop Main Excel */}
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '7px' }}>
                  Result Excel File <span style={{ color: '#EF4444' }}>*</span>
                </label>
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={async (e) => {
                    e.preventDefault();
                    if (reportStatus === 'generating' || uploadingFile) return;
                    const file = e.dataTransfer.files[0];
                    if (file) await handleReportFileUpload(file, 'excel');
                  }}
                  onClick={() => {
                    if (reportStatus !== 'generating' && !uploadingFile) reportFileInputRef.current.click();
                  }}
                  style={{
                    border: '2px dashed var(--card-border)',
                    borderRadius: '12px',
                    padding: '24px 16px',
                    textAlign: 'center',
                    cursor: reportStatus === 'generating' || uploadingFile ? 'not-allowed' : 'pointer',
                    background: 'rgba(255,255,255,0.01)',
                    transition: 'var(--transition-smooth)',
                    borderColor: reportForm.excel_path ? 'var(--success)' : 'var(--card-border)',
                  }}
                  onMouseEnter={(e) => {
                    if (reportStatus !== 'generating' && !uploadingFile) e.currentTarget.style.borderColor = 'var(--primary)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = reportForm.excel_path ? 'var(--success)' : 'var(--card-border)';
                  }}
                >
                  <input
                    type="file"
                    ref={reportFileInputRef}
                    style={{ display: 'none' }}
                    accept=".xlsx,.xls"
                    onChange={async (e) => {
                      const file = e.target.files[0];
                      if (file) await handleReportFileUpload(file, 'excel');
                    }}
                  />
                  {uploadingFile === 'excel' ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '18px', animation: 'spin 1s linear infinite', display: 'inline-block' }}>⏳</span>
                      <p style={{ fontWeight: '700', fontSize: '12px', color: 'var(--primary)' }}>Uploading Excel file...</p>
                    </div>
                  ) : reportForm.excel_path ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                      <span style={{ fontSize: '22px' }}>🟢</span>
                      <p style={{ fontWeight: '800', fontSize: '13px', color: 'var(--success)' }}>Excel Loaded Successfully</p>
                      <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{reportForm.excel_path.split('/').pop() || reportForm.excel_path.split('\\').pop()}</p>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                      <span style={{ fontSize: '22px', opacity: 0.7 }}>📊</span>
                      <p style={{ fontWeight: '800', fontSize: '13px', color: 'var(--text-main)' }}>Drag & Drop Excel here or Click</p>
                      <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Only .xlsx / .xls files supported</p>
                    </div>
                  )}
                </div>

                <input
                  type="text"
                  value={reportForm.excel_path}
                  onChange={e => setReportForm(f => ({ ...f, excel_path: e.target.value }))}
                  placeholder="Or type Excel path (e.g. data/RGPV_Result_xxxx.xlsx)"
                  disabled={reportStatus === 'generating'}
                  style={{ width: '100%', boxSizing: 'border-box', marginTop: '8px', fontSize: '12.5px' }}
                />

                {jobState.excel_file_path && (
                  <button
                    type="button"
                    onClick={() => setReportForm(f => ({ ...f, excel_path: jobState.excel_file_path }))}
                    style={{ background: 'rgba(5,150,105,0.1)', border: '1px solid rgba(5,150,105,0.25)', color: '#059669', padding: '4px 10px', borderRadius: '6px', fontSize: '11px', cursor: 'pointer', marginTop: '6px', fontWeight: '700' }}
                  >
                    Use last scrape: {jobState.excel_file_path.split('/').pop() || jobState.excel_file_path.split('\\').pop()}
                  </button>
                )}
              </div>

              {/* Drag & Drop Compare Excel */}
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '7px' }}>
                  Previous Excel (Comparison) <span style={{ color: 'var(--text-muted)', fontWeight: '400' }}>optional</span>
                </label>
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={async (e) => {
                    e.preventDefault();
                    if (reportStatus === 'generating' || uploadingFile) return;
                    const file = e.dataTransfer.files[0];
                    if (file) await handleReportFileUpload(file, 'compare');
                  }}
                  onClick={() => {
                    if (reportStatus !== 'generating' && !uploadingFile) reportCompareInputRef.current.click();
                  }}
                  style={{
                    border: '2px dashed var(--card-border)',
                    borderRadius: '12px',
                    padding: '16px 12px',
                    textAlign: 'center',
                    cursor: reportStatus === 'generating' || uploadingFile ? 'not-allowed' : 'pointer',
                    background: 'rgba(255,255,255,0.01)',
                    transition: 'var(--transition-smooth)',
                    borderColor: reportForm.compare_path ? 'var(--info)' : 'var(--card-border)',
                  }}
                  onMouseEnter={(e) => {
                    if (reportStatus !== 'generating' && !uploadingFile) e.currentTarget.style.borderColor = 'var(--primary)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = reportForm.compare_path ? 'var(--info)' : 'var(--card-border)';
                  }}
                >
                  <input
                    type="file"
                    ref={reportCompareInputRef}
                    style={{ display: 'none' }}
                    accept=".xlsx,.xls"
                    onChange={async (e) => {
                      const file = e.target.files[0];
                      if (file) await handleReportFileUpload(file, 'compare');
                    }}
                  />
                  {uploadingFile === 'compare' ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                      <p style={{ fontWeight: '700', fontSize: '11.5px', color: 'var(--info)' }}>Uploading comparison file...</p>
                    </div>
                  ) : reportForm.compare_path ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                      <p style={{ fontWeight: '800', fontSize: '12px', color: 'var(--info)' }}>Comparison Excel Loaded</p>
                      <p style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>{reportForm.compare_path.split('/').pop() || reportForm.compare_path.split('\\').pop()}</p>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                      <p style={{ fontWeight: '700', fontSize: '12px', color: 'var(--text-muted)' }}>Drag & Drop Comparison Excel here or Click</p>
                    </div>
                  )}
                </div>

                <input
                  type="text"
                  value={reportForm.compare_path}
                  onChange={e => setReportForm(f => ({ ...f, compare_path: e.target.value }))}
                  placeholder="Or type comparison Excel path (optional)"
                  disabled={reportStatus === 'generating'}
                  style={{ width: '100%', boxSizing: 'border-box', marginTop: '8px', fontSize: '12.5px' }}
                />
              </div>

              {/* College Name */}
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '7px' }}>College Name</label>
                <input
                  type="text"
                  value={reportForm.college_name}
                  onChange={e => setReportForm(f => ({ ...f, college_name: e.target.value }))}
                  disabled={reportStatus === 'generating'}
                  style={{ width: '100%', boxSizing: 'border-box' }}
                />
              </div>

              {/* Department */}
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '7px' }}>Department</label>
                <input
                  type="text"
                  value={reportForm.department}
                  onChange={e => setReportForm(f => ({ ...f, department: e.target.value }))}
                  disabled={reportStatus === 'generating'}
                  style={{ width: '100%', boxSizing: 'border-box' }}
                />
              </div>

              {/* Semester + Program row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                <div className="form-group">
                  <label style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '7px' }}>Semester</label>
                  <select
                    value={reportForm.semester}
                    onChange={e => setReportForm(f => ({ ...f, semester: e.target.value }))}
                    disabled={reportStatus === 'generating'}
                  >
                    <option value="">All Semesters</option>
                    {[1,2,3,4,5,6,7,8].map(n => <option key={n} value={String(n)}>Semester {n}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '7px' }}>Program</label>
                  <select
                    value={reportForm.program}
                    onChange={e => setReportForm(f => ({ ...f, program: e.target.value }))}
                    disabled={reportStatus === 'generating'}
                  >
                    <option>B.Tech.</option>
                    <option>B.E.</option>
                    <option>M.Tech.</option>
                    <option>MCA</option>
                    <option>MBA</option>
                    <option>B.Pharmacy</option>
                  </select>
                </div>
              </div>

              {/* Report Size Selector */}
              <div className="form-group" style={{ marginBottom: '24px' }}>
                <label style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '7px' }}>
                  Report Size / Page Length
                </label>
                <select
                  value={reportForm.max_student_pages}
                  onChange={e => setReportForm(f => ({ ...f, max_student_pages: Number(e.target.value) }))}
                  disabled={reportStatus === 'generating'}
                >
                  <option value={10}>Summary (~15 Pages, Top 10 Student Details)</option>
                  <option value={30}>Standard (~25 Pages, Top 30 Student Details)</option>
                  <option value={100}>Detailed (~50 Pages, Top 100 Student Details)</option>
                  <option value={10000}>Comprehensive (40-50+ Pages, All Student Details)</option>
                </select>
              </div>

              {/* Generate Button */}
              <motion.button
                whileHover={{ scale: reportStatus === 'generating' ? 1 : 1.02 }}
                whileTap={{ scale: reportStatus === 'generating' ? 1 : 0.97 }}
                disabled={reportStatus === 'generating' || !reportForm.excel_path.trim()}
                onClick={async () => {
                  setReportStatus('generating');
                  setReportPath(null);
                  setReportError(null);
                  setReportLogs(['[INFO] Sending request to report generator...']);
                  try {
                    const body = {
                      excel_path: reportForm.excel_path.trim(),
                      college_name: reportForm.college_name,
                      department: reportForm.department,
                      semester: reportForm.semester,
                      program: reportForm.program,
                      job_id: reportForm.job_id,
                      max_student_pages: reportForm.max_student_pages
                    };
                    if (reportForm.compare_path.trim()) body.compare_path = reportForm.compare_path.trim();
                    setReportLogs(l => [...l, '[INFO] Loading Excel data and computing analytics...']);
                    const res = await fetch(`${API_BASE}/report/generate`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify(body)
                    });
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || 'Generation failed');
                    setReportLogs(l => [...l, '[OK] Rendering 18 report sections...', '[OK] Building PDF document...', '[OK] Cleanup complete.', `[SUCCESS] Report saved: ${data.report_path}`]);
                    setReportPath(data.report_path);
                    setReportStatus('done');
                  } catch (err) {
                    setReportError(err.message);
                    setReportLogs(l => [...l, `[ERR] ${err.message}`]);
                    setReportStatus('error');
                  }
                }}
                style={{
                  width: '100%',
                  padding: '13px',
                  background: reportStatus === 'generating'
                    ? 'rgba(5,150,105,0.25)'
                    : 'linear-gradient(135deg, #059669, #0CA5A5)',
                  border: 'none',
                  borderRadius: '10px',
                  color: '#fff',
                  fontSize: '14px',
                  fontWeight: '800',
                  cursor: reportStatus === 'generating' || !reportForm.excel_path.trim() ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '10px',
                  opacity: !reportForm.excel_path.trim() ? 0.5 : 1
                }}
              >
                {reportStatus === 'generating' ? (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ animation: 'spin 1s linear infinite' }}>
                      <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                    </svg>
                    Generating Report...
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                    </svg>
                    Generate PDF Report
                  </>
                )}
              </motion.button>
            </div>

            {/* RIGHT: Status + Output */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

              {/* Info cards */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                {[
                  { label: '18 Sections', icon: '📋', desc: 'Cover to AI Recs' },
                  { label: '10 Chart Types', icon: '📊', desc: 'Bar, Pie, Heatmap...' },
                  { label: '40–50 Pages', icon: '📄', desc: 'PDF with bookmarks' }
                ].map(({ label, icon, desc }) => (
                  <div key={label} className="glass-panel" style={{ padding: '16px', textAlign: 'center' }}>
                    <div style={{ fontSize: '22px', marginBottom: '4px' }}>{icon}</div>
                    <div style={{ fontSize: '13px', fontWeight: '800', color: 'var(--text-main)' }}>{label}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{desc}</div>
                  </div>
                ))}
              </div>

              {/* Live terminal log */}
              <div className="glass-panel" style={{ padding: '20px' }}>
                <h3 style={{ fontSize: '12px', fontWeight: '800', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <svg width="12" height="12" fill="none" stroke="#0CA5A5" strokeWidth="2.5" viewBox="0 0 24 24" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
                  </svg>
                  Generation Log
                </h3>
                <div style={{
                  background: '#0a0f1a',
                  borderRadius: '8px',
                  padding: '14px',
                  minHeight: '160px',
                  maxHeight: '220px',
                  overflowY: 'auto',
                  fontFamily: 'monospace',
                  fontSize: '11.5px',
                  lineHeight: '1.7'
                }}>
                  {reportLogs.length === 0 ? (
                    <span style={{ color: '#475569' }}>Waiting for report generation to start...</span>
                  ) : (
                    reportLogs.map((log, i) => {
                      const color = log.startsWith('[ERR]') ? '#EF4444'
                        : log.startsWith('[SUCCESS]') ? '#22C55E'
                        : log.startsWith('[OK]') ? '#38BDF8'
                        : log.startsWith('[WARN]') ? '#F59E0B'
                        : '#94A3B8';
                      return <div key={i} style={{ color }}>{log}</div>;
                    })
                  )}
                </div>
              </div>

              {/* Download Result */}
              <AnimatePresence>
                {reportStatus === 'done' && reportPath && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="glass-panel"
                    style={{ padding: '22px', border: '1px solid rgba(5,150,105,0.35)', background: 'rgba(5,150,105,0.06)' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
                      <div style={{ background: 'rgba(5,150,105,0.2)', borderRadius: '10px', padding: '10px', display: 'flex' }}>
                        <svg width="22" height="22" fill="none" stroke="#059669" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                          <polyline points="22 4 12 14.01 9 11.01"/>
                        </svg>
                      </div>
                      <div>
                        <div style={{ fontWeight: '800', fontSize: '15px', color: '#059669' }}>Report Generated!</div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{reportPath.split('\\').pop() || reportPath.split('/').pop()}</div>
                      </div>
                    </div>
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.97 }}
                      onClick={() => {
                        const filename = reportPath.split('\\').pop() || reportPath.split('/').pop();
                        window.open(`${API_BASE}/report/download?path=${encodeURIComponent(filename)}`, '_blank');
                      }}
                      style={{
                        width: '100%',
                        padding: '12px',
                        background: 'linear-gradient(135deg, #059669, #0CA5A5)',
                        border: 'none',
                        borderRadius: '9px',
                        color: '#fff',
                        fontSize: '13px',
                        fontWeight: '800',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px'
                      }}
                    >
                      <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                      </svg>
                      Download PDF Report
                    </motion.button>
                  </motion.div>
                )}

                {reportStatus === 'error' && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="glass-panel"
                    style={{ padding: '18px', border: '1px solid rgba(239,68,68,0.35)', background: 'rgba(239,68,68,0.06)' }}
                  >
                    <div style={{ color: '#EF4444', fontWeight: '700', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <svg width="16" height="16" fill="none" stroke="#EF4444" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                        <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                      </svg>
                      Generation Failed
                    </div>
                    <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '8px', marginBottom: '0' }}>{reportError}</p>
                    <p style={{ color: 'var(--text-muted)', fontSize: '11px', marginTop: '8px', marginBottom: '0' }}>
                      Make sure the backend has the report router mounted, or the backend /api/report/generate endpoint is reachable.
                      <br/>Alternatively, run the report from the CLI:<br/>
                      <code style={{ color: '#38BDF8', fontSize: '10.5px' }}>venv\Scripts\python.exe -m report_generator.generate_report --input {reportForm.excel_path}</code>
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Section preview list */}
              <div className="glass-panel" style={{ padding: '20px' }}>
                <h3 style={{ fontSize: '12px', fontWeight: '800', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '12px' }}>Report Contents</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                  {[
                    '01. Cover Page', '02. Table of Contents', '03. Executive Summary',
                    '04. Overall Statistics', '05. Branch Analysis', '06. Semester Analysis',
                    '07. Subject Analysis', '08. Topper Analysis', '09. Student Details',
                    '10. Grade Distribution', '11. Pass % Gauge', '12. Backlog Analysis',
                    '13. Heatmaps', '14. Risk Analysis', '15. Improvement Analysis',
                    '16. Comparison Analysis', '17. AI Insights (30–50)', '18. AI Recommendations'
                  ].map((s, i) => (
                    <div key={i} style={{ fontSize: '11px', color: 'var(--text-muted)', padding: '4px 8px', borderRadius: '5px', background: 'rgba(255,255,255,0.03)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ color: '#059669', fontWeight: '700', fontSize: '10px' }}>✓</span> {s}
                    </div>
                  ))}
                </div>
              </div>

            </div>
          </div>
        </motion.div>
      )}

      {activeTab === 'extractor' && (
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
                <option value="B.Pharmacy(PCI)">B.Pharmacy(PCI)</option>
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

          {/* TOPPER CARD */}
          {jobState.records && jobState.records.filter(r => !r.not_found && r.sgpa).length > 0 && (() => {
            const validStudents = jobState.records.filter(r => !r.not_found && r.sgpa);
            const topper = validStudents.reduce((best, cur) => (parseFloat(cur.sgpa) > parseFloat(best.sgpa) ? cur : best), validStudents[0]);
            return (
              <motion.section
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-panel"
                style={{ position: 'relative', overflow: 'hidden', borderLeft: '4px solid var(--primary)' }}
              >
                {/* Ambient glow */}
                <div style={{ position: 'absolute', top: '-30px', right: '-30px', width: '120px', height: '120px', background: 'radial-gradient(circle, rgba(124,58,237,0.12) 0%, transparent 70%)', pointerEvents: 'none' }}></div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '20px', flexWrap: 'wrap' }}>
                  {/* Left: Trophy + Info */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{
                      width: '52px', height: '52px', borderRadius: '14px',
                      background: 'linear-gradient(135deg, rgba(250,204,21,0.2) 0%, rgba(245,158,11,0.15) 100%)',
                      border: '1px solid rgba(250,204,21,0.25)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      boxShadow: '0 4px 16px rgba(250,204,21,0.1)'
                    }}>
                      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#FACC15" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/>
                        <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/>
                        <path d="M4 22h16"/>
                        <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20 7 22"/>
                        <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20 17 22"/>
                        <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>
                      </svg>
                    </div>
                    <div>
                      <p style={{ fontSize: '10px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#FACC15', marginBottom: '4px' }}>🏆 Class Topper</p>
                      <h3 style={{ fontSize: '18px', fontWeight: '850', color: 'var(--title-color)', lineHeight: '1.2' }}>{topper.name}</h3>
                      <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>Enrollment: {topper.enrollment}</p>
                    </div>
                  </div>

                  {/* Right: Stats */}
                  <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
                    <div style={{ textAlign: 'center' }}>
                      <p style={{ fontSize: '9px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)' }}>SGPA</p>
                      <p style={{ fontSize: '22px', fontWeight: '850', color: 'var(--success)', fontFamily: 'var(--font-heading)' }}>{topper.sgpa}</p>
                    </div>
                    <div style={{ width: '1px', height: '36px', background: 'var(--card-border)' }}></div>
                    <div style={{ textAlign: 'center' }}>
                      <p style={{ fontSize: '9px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)' }}>CGPA</p>
                      <p style={{ fontSize: '22px', fontWeight: '850', color: 'var(--title-color)', fontFamily: 'var(--font-heading)' }}>{topper.cgpa || 'N/A'}</p>
                    </div>
                    <div style={{ width: '1px', height: '36px', background: 'var(--card-border)' }}></div>
                    <div style={{ textAlign: 'center' }}>
                      <p style={{ fontSize: '9px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)' }}>Result</p>
                      <span className={`badge ${topper.result === 'PASS' ? 'pass' : topper.result === 'FAIL' ? 'fail' : 'unknown'}`} style={{ marginTop: '4px' }}>{topper.result}</span>
                    </div>
                  </div>
                </div>
              </motion.section>
            );
          })()}

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
      )}

      {activeTab === 'compare' && (
        <ResultCompareStudio />
      )}

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
