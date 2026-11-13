/**
 * ReportSaathi - Frontend API Service
 * Handles communication with the FastAPI backend.
 * Uses environment variable VITE_API_URL or defaults to localhost.
 */

// Retrieve backend URL from environment without trailing slash
const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

/**
 * Helper to process and standardize HTTP error responses.
 */
async function handleResponseError(response) {
  let errorDetail = '';

  try {
    const errorJson = await response.json();
    errorDetail = errorJson.detail || '';
  } catch {
    errorDetail = response.statusText || 'Unknown server error';
  }

  // Provide user-friendly categorized messages based on HTTP status
  switch (response.status) {
    case 400:
      throw new Error(errorDetail || 'Invalid request. Please check your input.');
    case 413:
      throw new Error('File size exceeds the 5 MB limit. Please upload a smaller document.');
    case 415:
      throw new Error(errorDetail || 'Unsupported file format. Please upload JPG, PNG, or PDF.');
    case 422:
      throw new Error(errorDetail || 'Could not extract readable text from this file. Please ensure the document is clear and sharp.');
    case 429:
      throw new Error('Service is busy due to high demand. Please wait a moment and try again.');
    case 503:
      throw new Error(errorDetail || 'The explanation service is temporarily unavailable. Please try again shortly.');
    case 500:
      throw new Error(errorDetail || 'A server error occurred while analyzing the report.');
    default:
      throw new Error(errorDetail || `Request failed with status ${response.status}`);
  }
}

/**
 * Sends pasted medical report text to the backend for explanation.
 *
 * @param {string} text - Raw report text.
 * @param {string} language - Target language ('English', 'Hindi', 'Kannada').
 * @returns {Promise<Object>} Structured explanation object.
 */
export async function explainText(text, language = 'English') {
  try {
    const response = await fetch(`${API_BASE_URL}/explain-text`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text,
        language,
      }),
    });

    if (!response.ok) {
      await handleResponseError(response);
    }

    return await response.json();
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error(
        `Unable to connect to ReportSaathi backend (${API_BASE_URL}). Please ensure the server is running.`
      );
    }
    throw error;
  }
}

/**
 * Uploads a medical report file (JPG, PNG, PDF) to the backend for OCR and explanation.
 *
 * @param {File} file - Uploaded File instance.
 * @param {string} language - Target language ('English', 'Hindi', 'Kannada').
 * @returns {Promise<Object>} Structured explanation object including extracted_text.
 */
export async function explainFile(file, language = 'English') {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('language', language);

    const response = await fetch(`${API_BASE_URL}/explain-file`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      await handleResponseError(response);
    }

    return await response.json();
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error(
        `Unable to connect to ReportSaathi backend (${API_BASE_URL}). Please ensure the server is running.`
      );
    }
    throw error;
  }
}

