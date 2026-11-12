/**
 * KalmiPrep Error Beacon Client
 *
 * Silently captures uncaught JavaScript exceptions, unhandled Promise rejections,
 * KaTeX formula rendering errors, and offline network transitions during exams.
 * Transmits diagnostic payloads asynchronously via navigator.sendBeacon().
 */
(function () {
  'use strict';

  const BEACON_URL = '/api/telemetry/error-beacon/';
  const seenErrors = new Set();

  function sendErrorBeacon(data) {
    const errorKey = `${data.message}:${data.path}`;
    if (seenErrors.has(errorKey)) return; // Debounce duplicate errors
    seenErrors.add(errorKey);
    if (seenErrors.size > 20) seenErrors.clear();

    const payload = JSON.stringify({
      message: data.message || 'Unknown Client Error',
      stack_trace: data.stack || '',
      path: window.location.pathname,
      domain: data.domain || 'CLIENT_JS',
      severity: data.severity || 'ERROR',
      metadata: {
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        viewport: { width: window.innerWidth, height: window.innerHeight },
        isOnline: navigator.onLine,
        ...data.metadata
      }
    });

    if (navigator.sendBeacon) {
      const blob = new Blob([payload], { type: 'application/json' });
      navigator.sendBeacon(BEACON_URL, blob);
    } else if (window.fetch) {
      fetch(BEACON_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payload,
        keepalive: true
      }).catch(() => {});
    }
  }

  // 1. Unhandled JavaScript Exceptions
  window.addEventListener('error', function (event) {
    // Ignore benign cross-origin extension scripts
    if (!event.filename || event.filename.includes('chrome-extension')) return;

    sendErrorBeacon({
      message: event.message || 'Script error',
      stack: event.error ? event.error.stack : `${event.filename}:${event.lineno}:${event.colno}`,
      domain: 'CLIENT_JS',
      severity: 'ERROR'
    });
  });

  // 2. Unhandled Promise Rejections
  window.addEventListener('unhandledrejection', function (event) {
    const reason = event.reason;
    sendErrorBeacon({
      message: `Unhandled Promise Rejection: ${reason ? (reason.message || String(reason)) : 'Unknown'}`,
      stack: reason && reason.stack ? reason.stack : '',
      domain: 'CLIENT_JS',
      severity: 'WARNING'
    });
  });

  // 3. KaTeX Render Error Observer
  document.addEventListener('DOMContentLoaded', function () {
    // Check for any .katex-error rendered on page
    setTimeout(function () {
      const katexErrors = document.querySelectorAll('.katex-error');
      if (katexErrors.length > 0) {
        const errorMsgs = Array.from(katexErrors).map(el => el.textContent || el.title).join('; ');
        sendErrorBeacon({
          message: `KaTeX Render Failure: ${errorMsgs.slice(0, 300)}`,
          stack: errorMsgs,
          domain: 'CLIENT_JS',
          severity: 'HIGH',
          metadata: { katexCount: katexErrors.length }
        });
      }
    }, 1500);
  });

  // 4. Expose helper for programmatic diagnostic logging
  window.KalmiTelemetry = {
    logError: function (message, details, domain, severity) {
      sendErrorBeacon({
        message: message,
        stack: typeof details === 'string' ? details : JSON.stringify(details),
        domain: domain || 'CLIENT_JS',
        severity: severity || 'ERROR'
      });
    }
  };
})();
