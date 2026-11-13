import React from 'react';
import { Globe } from 'lucide-react';

/**
 * Modern Segmented Control for switching explanation language.
 * Supports English, Hindi, and Kannada.
 */
export default function LanguageSelector({ selectedLanguage, onLanguageChange }) {
  const languages = [
    { id: 'English', label: 'English' },
    { id: 'Hindi', label: 'हिंदी' },
    { id: 'Kannada', label: 'ಕನ್ನಡ' },
  ];

  return (
    <div className="lang-selector-wrapper">
      <div className="lang-icon-wrapper" aria-hidden="true">
        <Globe size={14} className="lang-globe-icon" />
      </div>
      <div className="lang-selector" role="radiogroup" aria-label="Select explanation language">
        {languages.map((lang) => {
          const isActive = selectedLanguage === lang.id;
          return (
            <button
              key={lang.id}
              type="button"
              role="radio"
              aria-checked={isActive}
              className={`lang-btn ${isActive ? 'active' : ''}`}
              onClick={() => onLanguageChange(lang.id)}
            >
              {lang.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
