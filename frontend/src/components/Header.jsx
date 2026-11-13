import React from 'react';
import LanguageSelector from './LanguageSelector';

/**
 * Header component displaying branding, medical icon, tagline,
 * and the language selection controls.
 */
export default function Header({ selectedLanguage, onLanguageChange }) {
  return (
    <header className="header-wrapper">
      <div className="header-top">
        <div className="brand-section">
          <div className="brand-icon" aria-hidden="true">
            {/* Medical Heartbeat / Pulse SVG Icon */}
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
          </div>
          <div>
            <h1 className="brand-title">
              Report<span>Saathi</span>
            </h1>
            <p className="brand-tagline">
              Understand your medical reports in simple language.
            </p>
          </div>
        </div>

        {/* Language Selection Segmented Control */}
        <LanguageSelector
          selectedLanguage={selectedLanguage}
          onLanguageChange={onLanguageChange}
        />
      </div>
    </header>
  );
}

