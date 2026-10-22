/**
 * KalmiPrep Instant Navigation & Prefetch Engine
 * Uses modern Speculation Rules API with fallback hover/touch micro-prefetching.
 * Cuts page transition latency to 0ms perceptual time without battery or data waste.
 */
(() => {
  // Prevent duplicate prefetching
  const prefetched = new Set();
  const currentOrigin = window.location.origin;

  // URL ignore list (authentication, active exam session, mutations)
  const ignoredPatterns = [
    /\/admin\//,
    /\/accounts\//,
    /\/practice\/session\//,
    /\/session\/\d+/,
    /\/logout\//,
    /#/
  ];

  function shouldPrefetch(url) {
    if (!url) return false;
    try {
      const parsed = new URL(url, currentOrigin);
      if (parsed.origin !== currentOrigin) return false;
      if (parsed.pathname === window.location.pathname && parsed.search === window.location.search) return false;
      if (ignoredPatterns.some(pattern => pattern.test(parsed.pathname))) return false;
      return true;
    } catch {
      return false;
    }
  }

  function prefetchUrl(url) {
    if (prefetched.has(url)) return;
    prefetched.add(url);

    // If native Speculation Rules API is supported, let the browser's speculative pipeline handle it
    if (HTMLScriptElement.supports && HTMLScriptElement.supports('speculationrules')) {
      return;
    }

    // Modern fallback: Low-priority fetch or link prefetch
    if ('fetch' in window) {
      fetch(url, { priority: 'low', credentials: 'same-origin' }).catch(() => {});
    } else {
      const link = document.createElement('link');
      link.rel = 'prefetch';
      link.href = url;
      link.as = 'document';
      document.head.appendChild(link);
    }
  }

  // Pointer & Touch listener on navigation links
  function attachPrefetchListeners() {
    document.querySelectorAll('a[href^="/"], a[href^="' + currentOrigin + '"]').forEach(link => {
      const href = link.getAttribute('href');
      if (!shouldPrefetch(href)) return;

      // Mouse hover (fires 150-300ms before click)
      link.addEventListener('pointerenter', () => prefetchUrl(href), { passive: true, once: true });
      // Mobile touch start (fires before touchend/click)
      link.addEventListener('touchstart', () => prefetchUrl(href), { passive: true, once: true });
    });
  }

  // Run on DOM ready and after HTMX dynamic swaps
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachPrefetchListeners);
  } else {
    attachPrefetchListeners();
  }

  document.addEventListener('htmx:afterSwap', attachPrefetchListeners);
})();
