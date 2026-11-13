import React from 'react';

/**
 * Reusable Status Badge Component.
 * Accessible visual status indicators:
 * Green = Normal (within range)
 * Red = High (out of range)
 * Blue = Low (below reference range)
 * Grey = Unknown
 */
export default function StatusBadge({ status }) {
  const normalizedStatus = (status || 'unknown').toLowerCase().trim();

  let config = {
    className: 'status-unknown',
    label: 'Unknown',
    dotClass: 'dot-unknown',
  };

  switch (normalizedStatus) {
    case 'normal':
      config = {
        className: 'status-normal',
        label: 'Normal',
        dotClass: 'dot-normal',
      };
      break;
    case 'high':
      config = {
        className: 'status-high',
        label: 'High',
        dotClass: 'dot-high',
      };
      break;
    case 'low':
      config = {
        className: 'status-low',
        label: 'Low',
        dotClass: 'dot-low',
      };
      break;
    default:
      config = {
        className: 'status-unknown',
        label: 'Unknown',
        dotClass: 'dot-unknown',
      };
      break;
  }

  return (
    <span className={`status-pill ${config.className}`} role="status">
      <span className={`status-dot ${config.dotClass}`} aria-hidden="true" />
      <span className="status-label">{config.label}</span>
    </span>
  );
}
