import React from 'react';

/**
 * Tab switcher between 'Upload Report' (file) and 'Paste Text'.
 */
export default function TabNavigation({ activeTab, onTabChange }) {
  return (
    <div className="tab-nav" role="tablist">
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === 'upload'}
        className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
        onClick={() => onTabChange('upload')}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        Upload Report
      </button>

      <button
        type="button"
        role="tab"
        aria-selected={activeTab === 'paste'}
        className={`tab-btn ${activeTab === 'paste' ? 'active' : ''}`}
        onClick={() => onTabChange('paste')}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
          <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
        </svg>
        Paste Text
      </button>
    </div>
  );
}

