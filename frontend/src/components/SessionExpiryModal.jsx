import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';

export default function SessionExpiryModal() {
  const { showExpiryModal, refreshAuthToken, logout } = useAuth();

  if (!showExpiryModal) return null;

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="modal-overlay"
        style={{ zIndex: 9999 }}
      >
        <motion.div 
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="modal-content"
          style={{ maxWidth: '420px', padding: '32px 24px', textAlign: 'center' }}
        >
          <div style={{
            width: '56px',
            height: '56px',
            borderRadius: '50%',
            background: 'var(--warning-bg)',
            color: 'var(--warning)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px auto',
            border: '1px solid rgba(245, 158, 11, 0.3)'
          }}>
            <svg width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" />
            </svg>
          </div>

          <h3 style={{ fontSize: '18px', fontWeight: '800', marginBottom: '8px' }}>Session Expiring Soon</h3>
          <p style={{ fontSize: '13.5px', color: 'var(--text-muted)', lineHeight: '1.5', marginBottom: '24px' }}>
            Your login session will expire shortly due to inactivity. Would you like to stay signed in?
          </p>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button 
              className="btn btn-secondary"
              onClick={logout}
              style={{ flex: 1 }}
            >
              Log Out
            </button>

            <button 
              className="btn btn-primary"
              onClick={refreshAuthToken}
              style={{ flex: 1 }}
            >
              Extend Session
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
