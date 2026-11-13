import React from 'react';
import { Upload, FileText } from 'lucide-react';

/**
 * Modern Segmented Tab Switcher between 'Upload Report' (file) and 'Paste Text'.
 */
export default function TabNavigation({ activeTab, onTabChange }) {
  return (
    <div className="tab-nav-container" role="tablist">
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === 'upload'}
        className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
        onClick={() => onTabChange('upload')}
      >
        <Upload size={17} strokeWidth={2.2} />
        <span>Upload Document</span>
      </button>

      <button
        type="button"
        role="tab"
        aria-selected={activeTab === 'paste'}
        className={`tab-btn ${activeTab === 'paste' ? 'active' : ''}`}
        onClick={() => onTabChange('paste')}
      >
        <FileText size={17} strokeWidth={2.2} />
        <span>Paste Report Text</span>
      </button>
    </div>
  );
}
