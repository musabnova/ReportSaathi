import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import DisclaimerBanner from './components/DisclaimerBanner';
import TabNavigation from './components/TabNavigation';
import FileUpload from './components/FileUpload';
import TextUpload from './components/TextUpload';
import ResultsSection from './components/ResultsSection';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorAlert from './components/ErrorAlert';
import { explainFile, explainText } from './services/api';

/**
 * Main application component orchestrating user inputs, API calls,
 * and presentation of medical report explanations.
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

  const handleFileSelected = (selectedFile) => {
    setFile(selectedFile);
    setError(null);
    setResult(null);
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
  };

  // Determine if Explain button should be enabled
  const canSubmit = !isLoading && (
    (activeTab === 'upload' && file !== null) ||
    (activeTab === 'paste' && pastedText.trim().length > 0)
  );

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!canSubmit || isLoading) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      let responseData;
      if (activeTab === 'upload') {
        responseData = await explainFile(file, selectedLanguage);
      } else {
        responseData = await explainText(pastedText.trim(), selectedLanguage);
      }
      setResult(responseData);
    } catch (err) {
      setError(err.message || 'Failed to explain medical report. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* 1. Header with App Title & Language Selector */}
      <Header
        selectedLanguage={selectedLanguage}
        onLanguageChange={(lang) => {
          setSelectedLanguage(lang);
          // If we already have results, clearing allows re-explaining in new language
          if (result) {
            setResult(null);
          }
        }}
      />

      {/* 2. Persistent Educational Medical Disclaimer */}
      <DisclaimerBanner />

      {/* 3. Input Section Card (shown if no active result is displayed) */}
      {!result && (
        <main className="card">
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
          <div className="action-section">
            <button
              type="button"
              className="submit-btn"
              disabled={!canSubmit}
              onClick={handleSubmit}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
                <line x1="11" y1="8" x2="11" y2="14" />
                <line x1="8" y1="11" x2="14" y2="11" />
              </svg>
              Explain My Report
            </button>
          </div>
        </main>
      )}

      {/* 4. Loading Indicator */}
      {isLoading && <LoadingSpinner isFile={activeTab === 'upload'} />}

      {/* 5. Error Alert Box */}
      {error && !isLoading && (
        <ErrorAlert message={error} onDismiss={() => setError(null)} />
      )}

      {/* 6. Structured Results View */}
      {result && !isLoading && (
        <ResultsSection result={result} onReset={handleReset} />
      )}
    </div>
  );
}

