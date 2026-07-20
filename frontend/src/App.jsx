import React, { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { jsPDF } from 'jspdf';

import ResultCompareStudio from './ResultCompareStudio';
import { AuthProvider, useAuth, API_BASE } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import ProfilePage from './pages/ProfilePage';
import SessionExpiryModal from './components/SessionExpiryModal';

const isDev = window.location.port === '5173';
const host = isDev ? '127.0.0.1:8000' : window.location.host;
const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${host}/api/ws`;

function ScrapingTimerWidget({ jobStatus, processedCount }) {
  const [seconds, setSeconds] = useState(0);
  const [isActive, setIsActive] = useState(false);
  const prevStatusRef = useRef(jobStatus);
  const timerRef = useRef(null);

  // Auto start/stop on jobStatus transitions
  useEffect(() => {
    const prevStatus = prevStatusRef.current;
    
    // Status transitioned to 'running' -> Reset and Start
    if (jobStatus === 'running' && prevStatus !== 'running') {
      setSeconds(0);
      setIsActive(true);
    } 
    // Status transitioned from 'running' to non-running -> Stop
    else if (jobStatus !== 'running' && prevStatus === 'running') {
      setIsActive(false);
    }
    
    prevStatusRef.current = jobStatus;
  }, [jobStatus]);

  // Interval timer handler
  useEffect(() => {
    if (isActive) {
      timerRef.current = setInterval(() => {
        setSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isActive]);

  const handleManualStart = (e) => {
    e.stopPropagation();
    setIsActive(true);
  };

  const handleManualStop = (e) => {
    e.stopPropagation();
    setIsActive(false);
  };

  const formatTime = (totalSec) => {
    const hrs = Math.floor(totalSec / 3600);
    const mins = Math.floor((totalSec % 3600) / 60);
    const secs = totalSec % 60;
    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(hrs)} : ${pad(mins)} : ${pad(secs)}`;
  };

  const formatAvgTime = (totalSec, processed) => {
    if (!processed || processed <= 0) return '00:00.0';
    const avgSec = totalSec / processed;
    const mins = Math.floor(avgSec / 60);
    const secs = (avgSec % 60).toFixed(1);
    const pad = (n) => String(n).padStart(2, '0');
    const secParts = secs.split('.');
    const integerSecs = pad(secParts[0]);
    const decimalSecs = secParts[1] || '0';
    return `${pad(mins)}:${integerSecs}.${decimalSecs}`;
  };

  return (
    <div className="metric-card" style={{ '--accent-color': 'var(--primary)' }}>
      <div className="metric-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
        <span className="metric-label">Scraping Time</span>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button
            type="button"
            onClick={handleManualStart}
            disabled={isActive}
            title="Start Timer Manually"
            style={{
              background: isActive ? 'rgba(34, 197, 94, 0.2)' : 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--card-border)',
              color: isActive ? 'var(--success)' : 'var(--text-muted)',
              borderRadius: '6px',
              padding: '2px 7px',
              fontSize: '10px',
              fontWeight: '700',
              cursor: isActive ? 'default' : 'pointer',
              transition: 'all 0.2s'
            }}
          >
            ▶ Start
          </button>
          <button
            type="button"
            onClick={handleManualStop}
            disabled={!isActive}
            title="Stop Timer Manually"
            style={{
              background: !isActive ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--card-border)',
              color: !isActive ? 'var(--danger)' : 'var(--text-muted)',
              borderRadius: '6px',
              padding: '2px 7px',
              fontSize: '10px',
              fontWeight: '700',
              cursor: !isActive ? 'default' : 'pointer',
              transition: 'all 0.2s'
            }}
          >
            ■ Stop
          </button>
        </div>
      </div>

      <div 
        className={`metric-value ${isActive ? 'timer-pulse' : ''}`}
        style={{
          fontFamily: 'monospace',
          fontSize: '20px',
          letterSpacing: '0.5px',
          margin: '6px 0',
          color: isActive ? 'var(--title-color)' : 'var(--text-muted)'
        }}
      >
        {formatTime(seconds)}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '700', marginBottom: '8px' }}>
        {isActive ? (
          <>
            <span 
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: 'var(--success)',
                display: 'inline-block',
                boxShadow: '0 0 8px var(--success)',
                animation: 'pulse 1.2s infinite'
              }}
            />
            <span style={{ color: 'var(--success)' }}>● Running</span>
          </>
        ) : (
          <>
            <span 
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: '#64748b',
                display: 'inline-block'
              }}
            />
            <span style={{ color: '#64748b' }}>■ Stopped</span>
          </>
        )}
      </div>

      {/* AVERAGE TIME PER STUDENT */}
      <div style={{ borderTop: '1px solid var(--card-border)', paddingTop: '6px', width: '100%' }}>
        <span style={{ fontSize: '9px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block' }}>
          Average Time Per Student
        </span>
        <span style={{ fontSize: '11.5px', fontWeight: '800', color: 'var(--primary)', fontFamily: 'monospace', marginTop: '2px', display: 'inline-block' }}>
          {formatAvgTime(seconds, processedCount)} <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', fontWeight: '600' }}>sec/student</span>
        </span>
      </div>
    </div>
  );
}

function MainApp() {
  const { user, loading, isAuthenticated, logout, authFetch } = useAuth();

  // Active view state: 'dashboard', 'studio', 'profile'
  const [currentView, setCurrentView] = useState('dashboard');
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);

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

  // Navigation tab state inside dashboard
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
      const res = await authFetch(`${API_BASE}/report/upload?filename=${encodeURIComponent(file.name)}`, {
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

  // Compute top 3 batch toppers from extracted records in real-time based on CGPA
  const toppers = useMemo(() => {
    if (!jobState.records || jobState.records.length === 0) return [];
    return [...jobState.records]
      .filter(r => !r.not_found && r.name && (r.cgpa || r.sgpa))
      .map(r => ({
        ...r,
        cgpaNum: parseFloat(r.cgpa) || 0,
        sgpaNum: parseFloat(r.sgpa) || 0
      }))
      .sort((a, b) => b.cgpaNum - a.cgpaNum || b.sgpaNum - a.sgpaNum)
      .slice(0, 3);
  }, [jobState.records]);

  const userDropdownRef = useRef(null);

  // Close dropdown on click outside or Escape key press
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userDropdownRef.current && !userDropdownRef.current.contains(event.target)) {
        setUserDropdownOpen(false);
      }
    };

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setUserDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

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
    if (!isAuthenticated) return;

    let socket;
    const connectWebSocket = () => {
      socket = new WebSocket(WS_URL);

      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "status") {
            mergeStatus(msg.data);
          } else if (msg.type === "log") {
            setJobState(prev => {
              const updatedLogs = [...prev.logs, msg.message];
              if (updatedLogs.length > 500) updatedLogs.shift();
              return { ...prev, logs: updatedLogs };
            });
          }
        } catch (e) {
          console.error("Error parsing socket message:", e);
        }
      };

      socket.onclose = () => {
        setTimeout(connectWebSocket, 2000);
      };

      socket.onerror = (err) => {
        socket.close();
      };
    };

    connectWebSocket();

    // Fetch initial status via HTTP
    authFetch(`${API_BASE}/scrape/status`)
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
  }, [isAuthenticated, authFetch]);

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
      const response = await authFetch(`${API_BASE}/scrape/start`, {
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
      const response = await authFetch(`${API_BASE}/scrape/cancel`, { method: 'POST' });
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

    doc.setFillColor(124, 58, 237);
    doc.rect(0, 0, 210, 8, 'F');

    doc.setFont("helvetica", "bold");
    doc.setFontSize(20);
    doc.setTextColor(15, 23, 42);
    doc.text("RAJIV GANDHI PROUDYOGIKI VISHWAVYADHALAYA", 105, 22, { align: "center" });

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(100, 116, 139);
    doc.text("State Technological University of Madhya Pradesh", 105, 27, { align: "center" });
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.setTextColor(79, 70, 229);
    doc.text("ACADEMIC GRADE CARD", 105, 34, { align: "center" });

    doc.setDrawColor(203, 213, 225);
    doc.setLineWidth(0.5);
    doc.line(15, 38, 195, 38);

    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.setTextColor(15, 23, 42);
    doc.text("STUDENT PROFILE", 15, 46);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(51, 65, 85);
    
    doc.text(`Student Name :  ${rec.name || 'N/A'}`, 15, 53);
    doc.text(`Enrollment No:  ${rec.enrollment}`, 15, 59);
    doc.text(`Program      :  ${program || 'B.Tech.'}`, 120, 53);
    doc.text(`Semester     :  Semester ${sem || 'N/A'}`, 120, 59);

    doc.line(15, 64, 195, 64);

    doc.setFont("helvetica", "bold");
    doc.text("SUBJECT-WISE GRADES", 15, 72);

    doc.setFillColor(241, 245, 249);
    doc.rect(15, 76, 180, 8, 'F');
    doc.setFontSize(9);
    doc.setTextColor(71, 85, 105);
    doc.text("SUBJECT CODE", 20, 81.5);
    doc.text("GRADE OBTAINED", 150, 81.5);

    let y = 90;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(15, 23, 42);

    if (rec.subjects && Object.keys(rec.subjects).length > 0) {
      Object.entries(rec.subjects).forEach(([subj, grade], idx) => {
        if (idx % 2 === 1) {
          doc.setFillColor(248, 250, 252);
          doc.rect(15, y - 5, 180, 8, 'F');
        }
        
        doc.text(subj, 20, y);
        const isFailGrade = ['F', 'FAIL', 'AB', 'ABSENT', 'RL'].includes(grade.trim().toUpperCase());
        if (isFailGrade) {
          doc.setTextColor(239, 68, 68);
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

    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.text("ACADEMIC PERFORMANCE SUMMARY", 15, y);
    y += 6;

    doc.setDrawColor(226, 232, 240);
    doc.setFillColor(250, 250, 250);
    doc.rect(15, y - 4, 180, 24, 'FD');

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(51, 65, 85);
    doc.text(`Semester Grade Point Average (SGPA) :  ${rec.sgpa || '—'}`, 20, y + 2);
    doc.text(`Cumulative Grade Point Average (CGPA) :  ${rec.cgpa || '—'}`, 20, y + 8);
    
    const isPass = rec.result === 'PASS';
    const isFail = rec.result && rec.result.toUpperCase().includes('FAIL');
    
    if (isPass) {
      doc.setTextColor(34, 197, 94);
    } else if (isFail) {
      doc.setTextColor(239, 68, 68);
    } else {
      doc.setTextColor(245, 158, 11);
    }
    
    doc.setFont("helvetica", "bold");
    doc.text(`RESULT STATUS                       :  ${rec.result || 'UNKNOWN'}`, 20, y + 14);

    doc.setFont("helvetica", "italic");
    doc.setFontSize(8);
    doc.setTextColor(148, 163, 184);
    doc.text("Disclaimer: Computer generated ResultAI grade card extracted from RGPV portal.", 105, 280, { align: "center" });

    doc.save(`RGPV_Result_${rec.enrollment}.pdf`);
  };

  // Loading Screen
  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-primary)',
        color: '#FFFFFF'
      }}>
        <div style={{
          width: '60px',
          height: '60px',
          borderRadius: '18px',
          background: 'var(--primary-gradient)',
          fontWeight: '900',
          fontSize: '32px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '16px',
          animation: 'pulse 1.5s infinite'
        }}>
          R
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', fontWeight: '600' }}>Initializing ResultAI Authentication...</p>
      </div>
    );
  }

  // Redirect to Login if unauthenticated
  if (!isAuthenticated) {
    return <LoginPage />;
  }

  // Analytics Derived Data
  const isRunning = jobState.status === 'running';
  const totalGraded = jobState.pass_count + jobState.fail_count;
  const passRate = totalGraded > 0 ? Math.round((jobState.pass_count / totalGraded) * 100) : 0;
  const circleOffset = 377 - (377 * passRate) / 100;

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

  const getLogStyle = (log) => {
    const l = log.toLowerCase();
    if (l.includes('guest@resultai') || l.startsWith('$')) {
      return { color: '#22C55E', fontWeight: '600' };
    }
    if (l.includes('failed') || l.includes('error') || l.includes('timeout') || l.includes('exception') || l.includes('terminated')) {
      return { color: '#EF4444' };
    }
    if (l.includes('warning') || l.includes('alert') || l.includes('action required') || l.includes('please solve')) {
      return { color: '#F59E0B' };
    }
    if (l.includes('[scraper]') || l.includes('[system]')) {
      return { color: '#38BDF8' };
    }
    return { color: '#FFFFFF' };
  };

  return (
    <div className="app-container">
      <div className="grid-overlay"></div>

      {/* HEADER WITH USER PROFILE WIDGET */}
      <motion.header 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="app-header"
      >
        <div className="logo-container" onClick={() => setCurrentView('dashboard')} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <img 
            src="/logo.png" 
            alt="ResultAI Logo" 
            onError={(e) => { e.target.src = "/logo.jpg"; }}
            style={{
              height: '38px',
              width: 'auto',
              borderRadius: '8px',
              objectFit: 'contain',
              background: '#FFFFFF',
              padding: '2px',
              boxShadow: '0 4px 14px rgba(124, 58, 237, 0.3)'
            }} 
          />
          <span className="logo-text">ResultAI</span>
        </div>

        {/* Permanent Top Navigation Tabs */}
        <div style={{ display: 'flex', gap: '4px', background: 'rgba(255,255,255,0.02)', padding: '4px', borderRadius: '8px', border: '1px solid var(--card-border)' }}>
          <button 
            className="tab-btn" 
            style={{
              background: (currentView === 'dashboard' && activeTab === 'extractor') ? 'var(--primary-gradient)' : 'transparent',
              color: (currentView === 'dashboard' && activeTab === 'extractor') ? '#FFFFFF' : 'var(--text-muted)',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '700',
              fontSize: '12px'
            }}
            onClick={() => {
              setCurrentView('dashboard');
              setActiveTab('extractor');
            }}
          >
            Result Extractor
          </button>
          <button 
            className="tab-btn" 
            style={{
              background: currentView === 'studio' ? 'var(--primary-gradient)' : 'transparent',
              color: currentView === 'studio' ? '#FFFFFF' : 'var(--text-muted)',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '700',
              fontSize: '12px'
            }}
            onClick={() => setCurrentView('studio')}
          >
            Result Compare Studio
          </button>
          <button
            className="tab-btn"
            style={{
              background: (currentView === 'dashboard' && activeTab === 'report') ? 'var(--primary-gradient)' : 'transparent',
              color: (currentView === 'dashboard' && activeTab === 'report') ? '#FFFFFF' : 'var(--text-muted)',
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
            onClick={() => {
              setCurrentView('dashboard');
              setActiveTab('report');
            }}
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
          <button
            className="tab-btn"
            style={{
              background: currentView === 'profile' ? 'var(--primary-gradient)' : 'transparent',
              color: currentView === 'profile' ? '#FFFFFF' : 'var(--text-muted)',
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
            onClick={() => setCurrentView('profile')}
          >
            <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
            My Profile
          </button>
        </div>

        <div className="header-actions" style={{ position: 'relative' }}>
          {/* Theme Toggle Button */}
          <button 
            className="theme-toggle-btn"
            onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          >
            {theme === 'dark' ? (
              <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="4"/>
                <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
              </svg>
            ) : (
              <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>
              </svg>
            )}
          </button>

          {/* Job Status Badge */}
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

          {/* TOP-RIGHT USER PROFILE AVATAR WIDGET */}
          <div ref={userDropdownRef} style={{ position: 'relative' }}>
            <button
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid var(--card-border)',
                padding: '4px 10px 4px 6px',
                borderRadius: '20px',
                color: 'var(--title-color)',
                cursor: 'pointer'
              }}
            >
              <div style={{
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                background: 'var(--primary-gradient)',
                color: '#FFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: user?.profile_image && user?.profile_image.length <= 4 ? '15px' : '12px',
                fontWeight: '800',
                overflow: 'hidden'
              }}>
                {user?.profile_image && user?.profile_image.startsWith('http') ? (
                  <img src={user.profile_image} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : user?.profile_image || user?.name?.[0]?.toUpperCase() || 'A'}
              </div>
              <span style={{ fontSize: '13px', fontWeight: '700' }}>{user?.name || 'Admin'}</span>
              <svg 
                width="14" 
                height="14" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="2" 
                viewBox="0 0 24 24"
                style={{
                  transform: userDropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s'
                }}
              >
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>

            {/* User Dropdown Menu */}
            <AnimatePresence>
              {userDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 8, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 8, scale: 0.95 }}
                  style={{
                    position: 'absolute',
                    right: 0,
                    top: '42px',
                    width: '210px',
                    background: 'var(--card-bg)',
                    border: '1px solid var(--card-border)',
                    borderRadius: '14px',
                    padding: '8px',
                    boxShadow: '0 12px 36px rgba(0,0,0,0.6)',
                    zIndex: 100,
                    backdropFilter: 'blur(16px)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '8px 10px', borderBottom: '1px solid var(--card-border)', marginBottom: '4px' }}>
                    <div>
                      <p style={{ fontSize: '13px', fontWeight: '800', color: 'var(--title-color)' }}>{user?.name}</p>
                      <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{user?.email}</p>
                    </div>
                    <button 
                      onClick={() => setUserDropdownOpen(false)}
                      title="Close Menu (Esc)"
                      style={{
                        background: 'rgba(255,255,255,0.05)',
                        border: 'none',
                        color: 'var(--text-muted)',
                        cursor: 'pointer',
                        fontSize: '12px',
                        width: '22px',
                        height: '22px',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)'; e.currentTarget.style.color = 'var(--danger)'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = 'var(--text-muted)'; }}
                    >
                      ✕
                    </button>
                  </div>

                  <button
                    onClick={() => { setCurrentView('profile'); setUserDropdownOpen(false); }}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      background: 'none',
                      border: 'none',
                      padding: '8px 10px',
                      color: 'var(--text-main)',
                      fontSize: '13px',
                      cursor: 'pointer',
                      borderRadius: '6px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    👤 My Profile & Security
                  </button>

                  <button
                    onClick={() => { setCurrentView('studio'); setUserDropdownOpen(false); }}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      background: 'none',
                      border: 'none',
                      padding: '8px 10px',
                      color: 'var(--text-main)',
                      fontSize: '13px',
                      cursor: 'pointer',
                      borderRadius: '6px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    📊 Result Compare Studio
                  </button>

                  <button
                    onClick={() => { setCurrentView('dashboard'); setUserDropdownOpen(false); }}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      background: 'none',
                      border: 'none',
                      padding: '8px 10px',
                      color: 'var(--text-main)',
                      fontSize: '13px',
                      cursor: 'pointer',
                      borderRadius: '6px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    ⚡ Scraper Dashboard
                  </button>

                  <div style={{ height: '1px', background: 'var(--card-border)', margin: '4px 0' }}></div>

                  <button
                    onClick={logout}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      background: 'none',
                      border: 'none',
                      padding: '8px 10px',
                      color: 'var(--danger)',
                      fontSize: '13px',
                      cursor: 'pointer',
                      borderRadius: '6px',
                      fontWeight: '700',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    🚪 Sign Out
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.header>

      {/* RENDER CURRENT VIEW */}
      {currentView === 'profile' && (
        <ProfilePage onBackToDashboard={() => setCurrentView('dashboard')} />
      )}

      {currentView === 'studio' && (
        <ResultCompareStudio />
      )}

      {currentView === 'dashboard' && activeTab === 'report' && (
        <motion.div
          key="report"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -16 }}
          transition={{ duration: 0.35 }}
          style={{ padding: '28px 32px', maxWidth: '960px', margin: '0 auto', width: '100%' }}
        >
          {/* AI Report Generator Section */}
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
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: '800', color: 'var(--text-main)', marginBottom: '20px', textTransform: 'uppercase', letterSpacing: '0.08em', display: 'flex', alignItems: 'center', gap: '8px' }}>
                Report Configuration
              </h3>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--text-muted)', display: 'block', marginBottom: '7px' }}>
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
                    borderColor: reportForm.excel_path ? 'var(--success)' : 'var(--card-border)',
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
                    <p style={{ fontWeight: '700', fontSize: '12px', color: 'var(--primary)' }}>Uploading Excel file...</p>
                  ) : reportForm.excel_path ? (
                    <p style={{ fontWeight: '800', fontSize: '13px', color: 'var(--success)' }}>Excel Loaded: {reportForm.excel_path.split('/').pop()}</p>
                  ) : (
                    <p style={{ fontWeight: '800', fontSize: '13px', color: 'var(--text-main)' }}>Drag & Drop Excel here or Click</p>
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
                    Use last scrape: {jobState.excel_file_path.split('/').pop()}
                  </button>
                )}
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--text-muted)', display: 'block', marginBottom: '7px' }}>College Name</label>
                <input
                  type="text"
                  value={reportForm.college_name}
                  onChange={e => setReportForm(f => ({ ...f, college_name: e.target.value }))}
                  disabled={reportStatus === 'generating'}
                  style={{ width: '100%', boxSizing: 'border-box' }}
                />
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '11.5px', fontWeight: '700', color: 'var(--text-muted)', display: 'block', marginBottom: '7px' }}>Department</label>
                <input
                  type="text"
                  value={reportForm.department}
                  onChange={e => setReportForm(f => ({ ...f, department: e.target.value }))}
                  disabled={reportStatus === 'generating'}
                  style={{ width: '100%', boxSizing: 'border-box' }}
                />
              </div>

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
                    const res = await authFetch(`${API_BASE}/report/generate`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify(body)
                    });
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.detail || 'Generation failed');
                    setReportLogs(l => [...l, `[SUCCESS] Report saved: ${data.report_path}`]);
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
                  background: reportStatus === 'generating' ? 'rgba(5,150,105,0.25)' : 'linear-gradient(135deg, #059669, #0CA5A5)',
                  border: 'none',
                  borderRadius: '10px',
                  color: '#fff',
                  fontSize: '14px',
                  fontWeight: '800',
                  cursor: reportStatus === 'generating' || !reportForm.excel_path.trim() ? 'not-allowed' : 'pointer'
                }}
              >
                {reportStatus === 'generating' ? "Generating Report..." : "Generate AI PDF Report"}
              </motion.button>
            </div>

            {/* RIGHT: Live Logs & Download */}
            <div className="glass-panel" style={{ padding: '24px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: '800', color: 'var(--text-main)', marginBottom: '16px' }}>Generator Status</h3>
              {reportLogs.map((l, i) => (
                <div key={i} style={{ fontSize: '12px', color: l.includes('[ERR]') ? '#EF4444' : l.includes('[SUCCESS]') ? '#22C55E' : 'var(--text-main)', marginBottom: '4px' }}>
                  {l}
                </div>
              ))}

              {reportPath && (
                <a
                  href={`${API_BASE}/report/download?path=${encodeURIComponent(reportPath)}`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-primary"
                  style={{ display: 'inline-block', marginTop: '16px', textDecoration: 'none' }}
                >
                  📥 Download Generated PDF Report
                </a>
              )}
            </div>
          </div>
        </motion.div>
      )}

      {currentView === 'dashboard' && activeTab === 'extractor' && (
        <div className="dashboard-grid">
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
                  Cancel Scraping
                </motion.button>
              )}
            </form>
          </motion.aside>

          <motion.main 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}
          >
            {/* METRIC COUNTERS */}
            <section className="metrics-row">
              <ScrapingTimerWidget jobStatus={jobState.status} processedCount={jobState.processed} />
              <div className="metric-card" style={{ '--accent-color': 'var(--primary)' }}>
                <div className="metric-header"><span className="metric-label">Processed</span></div>
                <div className="metric-value">{jobState.processed} / {jobState.total}</div>
              </div>
              <div className="metric-card" style={{ '--accent-color': 'var(--success)' }}>
                <div className="metric-header"><span className="metric-label">Passed</span></div>
                <div className="metric-value" style={{ color: 'var(--success)' }}>{jobState.pass_count}</div>
              </div>
              <div className="metric-card" style={{ '--accent-color': 'var(--danger)' }}>
                <div className="metric-header"><span className="metric-label">Failed</span></div>
                <div className="metric-value" style={{ color: 'var(--danger)' }}>{jobState.fail_count}</div>
              </div>
              <div className="metric-card" style={{ '--accent-color': '#64748b' }}>
                <div className="metric-header"><span className="metric-label">Not Found</span></div>
                <div className="metric-value" style={{ color: '#94A3B8' }}>{jobState.not_found_count}</div>
              </div>
              <div className="metric-card" style={{ '--accent-color': 'var(--warning)' }}>
                <div className="metric-header"><span className="metric-label">Errors</span></div>
                <div className="metric-value" style={{ color: 'var(--warning)' }}>{jobState.error_count}</div>
              </div>
            </section>

            {/* LIVE TERMINAL LOGS */}
            <section className="glass-panel terminal-card">
              <div className="terminal-header">
                <span style={{ fontSize: '14px', fontWeight: '800' }}>Terminal Logger</span>
              </div>
              <div className="terminal-viewport">
                {!jobState.logs || jobState.logs.length === 0 ? (
                  <div className="terminal-line" style={{ color: 'var(--text-muted)' }}>[System] Ready. Configure scraper inputs to begin.</div>
                ) : (
                  jobState.logs.map((log, idx) => (
                    <div className="terminal-line" key={idx} style={getLogStyle(log)}>
                      <span style={{ opacity: 0.3, marginRight: '10px' }}>{(idx + 1).toString().padStart(3, '0')}</span>
                      {log}
                    </div>
                  ))
                )}
                <div ref={terminalEndRef} />
              </div>
            </section>

            {/* REAL-TIME BATCH TOPPERS WIDGET */}
            {toppers.length > 0 && (
              <section className="glass-panel" style={{ background: 'linear-gradient(135deg, rgba(124,58,237,0.06) 0%, rgba(79,70,229,0.03) 100%)', border: '1px solid rgba(124,58,237,0.25)', boxShadow: '0 8px 30px rgba(124,58,237,0.08)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '22px' }}>🏆</span>
                    <div>
                      <h3 style={{ fontSize: '16px', fontWeight: '850', color: 'var(--title-color)', margin: 0 }}>Batch Top Performers (CGPA Rank)</h3>
                      <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '2px 0 0 0' }}>Highest CGPA rank holders calculated from current extracted results</p>
                    </div>
                  </div>
                  <span className="badge pass" style={{ fontSize: '11px', padding: '4px 10px' }}>Real-time Rank Leaderboard</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: toppers.length === 1 ? '1fr' : toppers.length === 2 ? '1fr 1fr' : '1fr 1fr 1fr', gap: '16px' }}>
                  {toppers.map((t, idx) => {
                    const medal = idx === 0 ? "🥇" : idx === 1 ? "🥈" : "🥉";
                    const rankColor = idx === 0 ? "#F59E0B" : idx === 1 ? "#94A3B8" : "#B45309";
                    return (
                      <div key={t.enrollment} style={{
                        background: 'var(--card-bg)',
                        border: `1px solid ${idx === 0 ? 'rgba(245, 158, 11, 0.4)' : 'var(--card-border)'}`,
                        borderRadius: '14px',
                        padding: '14px 16px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '14px',
                        boxShadow: idx === 0 ? '0 6px 20px rgba(245, 158, 11, 0.12)' : 'none'
                      }}>
                        <div style={{ fontSize: '28px', lineHeight: 1 }}>{medal}</div>
                        <div style={{ flex: 1, overflow: 'hidden' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ fontSize: '10px', fontWeight: '900', color: rankColor, background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: '4px', border: `1px solid ${rankColor}40` }}>
                              #{idx + 1} TOPPER
                            </span>
                            {t.result === 'PASS' && <span style={{ fontSize: '10px', color: '#10B981', fontWeight: '750' }}>PASS</span>}
                          </div>
                          <p style={{ fontSize: '13.5px', fontWeight: '800', color: 'var(--title-color)', marginTop: '4px', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', margin: '4px 0 0 0' }}>
                            {t.name}
                          </p>
                          <p style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'monospace', margin: '2px 0 0 0' }}>{t.enrollment}</p>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <p style={{ fontSize: '18px', fontWeight: '900', color: 'var(--primary)', margin: 0 }}>{t.cgpa || t.sgpa}</p>
                          <p style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: '700', margin: 0 }}>CGPA</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* STUDENTS RESULTS GRID */}
            <section className="glass-panel">
              <div className="table-section-header">
                <h3 style={{ fontSize: '16px', fontWeight: '800' }}>Extracted Student Records</h3>
                {jobState.excel_file_path && (
                  <button className="btn btn-secondary" onClick={handleDownload} style={{ width: 'auto', padding: '6px 14px', fontSize: '13px' }}>
                    Download Excel
                  </button>
                )}
              </div>

              {!jobState.records || jobState.records.length === 0 ? (
                <div className="empty-state" style={{ padding: '40px', textAlign: 'center' }}>
                  <p style={{ color: 'var(--text-muted)' }}>No records loaded yet. Click "Start Extraction" to scrape.</p>
                </div>
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
                          <td>{rec.not_found ? '—' : rec.name}</td>
                          <td>
                            {rec.not_found ? <span className="badge not-found">Not Found</span> : rec.result === 'PASS' ? <span className="badge pass">PASS</span> : <span className="badge fail">FAIL</span>}
                          </td>
                          <td style={{ fontWeight: '700' }}>{rec.not_found ? '—' : (rec.sgpa || 'N/A')}</td>
                          <td style={{ fontWeight: '700' }}>{rec.not_found ? '—' : (rec.cgpa || 'N/A')}</td>
                          <td>
                            {!rec.not_found && (
                              <button className="btn btn-secondary" onClick={() => setSelectedRecord(rec)} style={{ padding: '4px 10px', fontSize: '11px', width: 'auto' }}>
                                View Grades
                              </button>
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

      {/* STUDENT GRADES DETAIL MODAL */}
      <AnimatePresence>
        {selectedRecord && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="modal-overlay" onClick={() => setSelectedRecord(null)}>
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="modal-content" onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <div>
                  <h3 style={{ fontSize: '18px', fontWeight: '800' }}>{selectedRecord.name}</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>{selectedRecord.enrollment}</p>
                </div>
                <button className="modal-close" onClick={() => setSelectedRecord(null)}>✕</button>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', margin: '16px 0' }}>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>SGPA</span>
                  <p style={{ fontSize: '20px', fontWeight: '800', color: 'var(--title-color)' }}>{selectedRecord.sgpa || 'N/A'}</p>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '8px' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>CGPA</span>
                  <p style={{ fontSize: '20px', fontWeight: '800', color: 'var(--title-color)' }}>{selectedRecord.cgpa || 'N/A'}</p>
                </div>
              </div>

              <h4 style={{ fontSize: '13px', fontWeight: '800', marginBottom: '8px' }}>Subject Grades</h4>
              <div className="table-wrapper" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                <table>
                  <thead>
                    <tr><th>Subject Code</th><th>Grade</th></tr>
                  </thead>
                  <tbody>
                    {selectedRecord.subjects && Object.entries(selectedRecord.subjects).map(([code, grade], i) => (
                      <tr key={i}>
                        <td className="subject-code">{code}</td>
                        <td style={{ fontWeight: '700', color: ['F', 'FAIL', 'AB'].includes(grade) ? 'var(--danger)' : 'var(--title-color)' }}>{grade}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
                <button className="btn btn-secondary" onClick={() => setSelectedRecord(null)} style={{ flex: 1 }}>Close</button>
                <button className="btn btn-primary" onClick={() => downloadStudentPDF(selectedRecord)} style={{ flex: 1 }}>Download PDF</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <SessionExpiryModal />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
