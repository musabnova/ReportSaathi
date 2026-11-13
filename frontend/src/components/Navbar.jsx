import React, { useState } from 'react';
import LanguageSelector from './LanguageSelector';
import { Activity, ArrowRight, Menu, X, Shield } from 'lucide-react';

/**
 * Modern SaaS Navigation Bar
 * Features brand logo, navigation links, language selector, and 'Analyze Report' CTA.
 */
export default function Navbar({ selectedLanguage, onLanguageChange, onAnalyzeClick }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleNavClick = (id) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <nav className="navbar-container" aria-label="Main Navigation">
      <div className="navbar-inner">
        {/* Brand Logo & Name */}
        <a href="#home" className="navbar-brand" onClick={(e) => { e.preventDefault(); handleNavClick('home'); }}>
          <div className="brand-logo-icon" aria-hidden="true">
            <Activity size={22} strokeWidth={2.4} />
          </div>
          <div className="brand-text">
            <span className="brand-title-main">Report<span className="brand-title-accent">Saathi</span></span>
            <span className="brand-badge">HEALTH LITERACY</span>
          </div>
        </a>

        {/* Desktop Navigation Links */}
        <div className="navbar-links">
          <button type="button" className="nav-link-btn" onClick={() => handleNavClick('home')}>Home</button>
          <button type="button" className="nav-link-btn" onClick={() => handleNavClick('how-it-works')}>How It Works</button>
          <button type="button" className="nav-link-btn" onClick={() => handleNavClick('features')}>Features</button>
          <button type="button" className="nav-link-btn" onClick={() => handleNavClick('about')}>About</button>
        </div>

        {/* Desktop Right Actions: Language Selector + CTA */}
        <div className="navbar-actions">
          <LanguageSelector
            selectedLanguage={selectedLanguage}
            onLanguageChange={onLanguageChange}
          />
          <button
            type="button"
            className="navbar-cta-btn"
            onClick={onAnalyzeClick}
          >
            <span>Analyze Report</span>
            <ArrowRight size={16} strokeWidth={2.2} />
          </button>
        </div>

        {/* Mobile Hamburger Toggle */}
        <button
          type="button"
          className="mobile-menu-toggle"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="mobile-drawer">
          <div className="mobile-nav-links">
            <button type="button" className="mobile-nav-item" onClick={() => handleNavClick('home')}>Home</button>
            <button type="button" className="mobile-nav-item" onClick={() => handleNavClick('how-it-works')}>How It Works</button>
            <button type="button" className="mobile-nav-item" onClick={() => handleNavClick('features')}>Features</button>
            <button type="button" className="mobile-nav-item" onClick={() => handleNavClick('about')}>About & Trust</button>
          </div>
          <div className="mobile-drawer-footer">
            <div className="mobile-lang-wrapper">
              <span className="mobile-lang-label">Explanation Language:</span>
              <LanguageSelector
                selectedLanguage={selectedLanguage}
                onLanguageChange={onLanguageChange}
              />
            </div>
            <button
              type="button"
              className="navbar-cta-btn mobile-cta-full"
              onClick={() => { setMobileMenuOpen(false); onAnalyzeClick(); }}
            >
              <span>Analyze Report</span>
              <ArrowRight size={16} strokeWidth={2.2} />
            </button>
          </div>
        </div>
      )}
    </nav>
  );
}

