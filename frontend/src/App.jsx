import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import HeroSection from './components/HeroSection';
import TrustFeatures from './components/TrustFeatures';
import HowItWorks from './components/HowItWorks';
import DisclaimerBanner from './components/DisclaimerBanner';
import TabNavigation from './components/TabNavigation';
import FileUpload from './components/FileUpload';
import TextUpload from './components/TextUpload';
import ResultsSection from './components/ResultsSection';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorAlert from './components/ErrorAlert';
import Footer from './components/Footer';
import LanguageSelector from './components/LanguageSelector';
import { explainFile, explainText } from './services/api';
import { Sparkles, ArrowRight } from 'lucide-react';

/**
 * ReportSaathi — Main Application Coordinator
 * Integrates the modern SaaS landing sections (Hero, How It Works, Features)
 * with the functional Report Analysis Workspace and Results Dashboard.
 */
export default function App() {
  const [selectedLanguage, setSelectedLanguage] = useState('English');
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'paste'

  // Input states
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [pastedText, setPastedText] = useState('');

  // Processing states
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const workspaceRef = useRef(null);

  // Clean up object URL when file changes or unmounts
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }

    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setPreviewUrl(null);
    }
  }, [file]);

  const scrollToWorkspace = () => {
    const el = document.getElementById('workspace');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const scrollToHowItWorks = () => {
    const el = document.getElementById('how-it-works');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleFileSelected = (selectedFile) => {
    setFile(selectedFile);
    setError(null);
  };

  const handleFileCleared = () => {
    setFile(null);
    setPreviewUrl(null);
  };

  const handleClearText = () => {
    setPastedText('');
    setError(null);
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
    // Smooth scroll back to workspace
    setTimeout(() => {
      scrollToWorkspace();
    }, 100);
  };

  // Determine if Explain button should be enabled
  const canSubmit = !isLoading && (
    (activeTab === 'upload' && file !== null) ||
    (activeTab === 'paste' && pastedText.trim().length > 0)
  );

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!canSubmit || isLoading) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    // Smooth scroll to loading area
    setTimeout(() => {
      const loadingEl = document.getElementById('workspace-activity');
      if (loadingEl) loadingEl.scrollIntoView({ behavior: 'smooth' });
    }, 50);

    try {
      let responseData;
      if (activeTab === 'upload') {
        responseData = await explainFile(file, selectedLanguage);
      } else {
        responseData = await explainText(pastedText.trim(), selectedLanguage);
      }
      setResult(responseData);

      // Smooth scroll to results
      setTimeout(() => {
        const resultsEl = document.getElementById('results');
        if (resultsEl) resultsEl.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } catch (err) {
      setError(err.message || 'Failed to explain medical report. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="saas-app-wrapper">
      {/* 1. Global Navigation Bar */}
      <Navbar
        selectedLanguage={selectedLanguage}
        onLanguageChange={(lang) => {
          setSelectedLanguage(lang);
          // If viewing results, user might want to re-explain in new language
        }}
        onAnalyzeClick={scrollToWorkspace}
      />

      {/* 2. Hero Section */}
      <HeroSection
        onAnalyzeClick={scrollToWorkspace}
        onHowItWorksClick={scrollToHowItWorks}
      />

      {/* 3. Features & Trust Pillars */}
      <TrustFeatures />

      {/* 4. How It Works Pipeline */}
      <HowItWorks />

      {/* 5. Report Analysis Workspace */}
      <section id="workspace" ref={workspaceRef} className="workspace-section">
        <div className="workspace-container">
          <div className="workspace-header-row">
            <div>
              <span className="workspace-badge">ANALYSIS WORKSPACE</span>
              <h2 className="workspace-title">Report Analysis Workspace</h2>
              <p className="workspace-description">
                Upload your document (PDF, JPG, PNG up to 5 MB) or paste clinical report text. Select your preferred language to receive clear, plain-language insights.
              </p>
            </div>

            {/* Language Selector embedded in Workspace for immediate accessibility */}
            <div className="workspace-lang-box">
              <span className="workspace-lang-label">Language:</span>
              <LanguageSelector
                selectedLanguage={selectedLanguage}
                onLanguageChange={(lang) => setSelectedLanguage(lang)}
              />
            </div>
          </div>

          {/* Persistent Educational Medical Disclaimer */}
          <DisclaimerBanner />

          {/* Activity Anchor for auto-scrolling */}
          <div id="workspace-activity">
            {/* Loading Indicator */}
            {isLoading && <LoadingSpinner isFile={activeTab === 'upload'} />}

            {/* Error Alert Box */}
            {error && !isLoading && (
              <ErrorAlert message={error} onDismiss={() => setError(null)} />
            )}

            {/* Results Presentation Dashboard */}
            {result && !isLoading && (
              <ResultsSection result={result} onReset={handleReset} />
            )}
          </div>

          {/* Input Section Card (shown when not actively displaying results) */}
          {!result && (
            <div className="workspace-card">
              {/* Tab Navigation: Upload Report vs. Paste Text */}
              <TabNavigation
                activeTab={activeTab}
                onTabChange={(tab) => {
                  setActiveTab(tab);
                  setError(null);
                }}
              />

              {/* Tab 1: File Upload */}
              {activeTab === 'upload' && (
                <FileUpload
                  file={file}
                  previewUrl={previewUrl}
                  onFileSelected={handleFileSelected}
                  onFileCleared={handleFileCleared}
                />
              )}

              {/* Tab 2: Paste Text */}
              {activeTab === 'paste' && (
                <TextUpload
                  text={pastedText}
                  onTextChange={(val) => {
                    setPastedText(val);
                    if (error) setError(null);
                  }}
                  onClearText={handleClearText}
                />
              )}

              {/* Explain Action Button */}
              <div className="workspace-submit-row">
                <button
                  type="button"
                  className="analyze-report-btn"
                  disabled={!canSubmit || isLoading}
                  onClick={handleSubmit}
                >
                  <Sparkles size={18} className="btn-sparkle-icon" />
                  <span>Analyze My Report</span>
                  <ArrowRight size={16} strokeWidth={2.4} />
                </button>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* 6. Footer */}
      <Footer />
    </div>
  );
}
