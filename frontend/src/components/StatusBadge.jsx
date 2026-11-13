import React from 'react';

/**
 * Reusable Status Badge Component.
 * Maps status values to exact color schemes specified in PROJECT_SPEC.md:
 * Green = Normal, Red = High, Blue = Low, Grey = Unknown.
 */
export default function StatusBadge({ status }) {
  const normalizedStatus = (status || 'unknown').toLowerCase().trim();

  let config = {
    className: 'unknown',
    label: 'Unknown',
  };

  switch (normalizedStatus) {
    case 'normal':
      config = { className: 'normal', label: 'Normal' };
      break;
    case 'high':
      config = { className: 'high', label: 'High' };
      break;
    case 'low':
      config = { className: 'low', label: 'Low' };
      break;
    default:
      config = { className: 'unknown', label: 'Unknown' };
      break;
  }

  return (
    <span className={`status-badge ${config.className}`}>
      <span className="status-dot" aria-hidden="true" />
      {config.label}
    </span>
  );
}

