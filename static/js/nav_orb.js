/**
 * KalmiPrep Smooth Nav Transitions, GSAP Glowing Orb, & Optimistic UI Engine
 * Features:
 * 1. Zero-refresh page switches via HTMX & In-Memory / Session Cache.
 * 2. Instant optimistic UI rendering (0ms perception latency).
 * 3. Pre-fetching on hover and touchstart for lightning-fast tab swaps.
 * 4. Subtle, high-end KalmiPrep transition loader (hairline progress beam + micro-pill badge).
 * 5. GSAP organic glowing orb navigation dock on mobile and desktop.
 */

(function () {
  'use strict';

  // In-Memory Page Cache for Optimistic UI (Stale-While-Revalidate)
  const pageCache = new Map();
  const prefetchingUrls = new Set();
  let loadingPillTimer = null;

  // Initialize cache with sessionStorage if available
  try {
    const saved = sessionStorage.getItem('kalmiprep_page_cache');
    if (saved) {
      const parsed = JSON.parse(saved);
      Object.entries(parsed).forEach(([k, v]) => {
        // Expire cache after 15 minutes
        if (Date.now() - v.timestamp < 15 * 60 * 1000) {
          pageCache.set(k, v);
        }
      });
    }
  } catch (e) {
    // Session storage not accessible or disabled
  }

  function persistCache() {
    try {
      const obj = {};
      pageCache.forEach((v, k) => {
        obj[k] = v;
      });
      sessionStorage.setItem('kalmiprep_page_cache', JSON.stringify(obj));
    } catch (e) {}
  }

  function normalizeUrl(url) {
    if (!url) return '';
    try {
      const parsed = new URL(url, window.location.origin);
      return parsed.pathname + parsed.search;
    } catch (e) {
      return url;
    }
  }

  function getActiveSection(pathname) {
    if (!pathname) pathname = window.location.pathname;
    if (pathname === '/' || pathname === '') return 'core';
    if (pathname.startsWith('/curriculum')) return 'curriculum';
    if (pathname.startsWith('/questions')) return 'questions';
    if (pathname.startsWith('/practice')) return 'practice';
    if (pathname.startsWith('/progress') || pathname.startsWith('/accounts')) return 'progress';
    return '';
  }

  // --- SUBTLE KALMIPREP RELOADING INDICATOR ---
  function startLoadingIndicator() {
    const bar = document.getElementById('page-loading-bar');
    const barInner = document.getElementById('page-loading-bar-inner');
    const pill = document.getElementById('page-loading-pill');

    if (bar && barInner) {
      bar.classList.remove('opacity-0');
      bar.classList.add('opacity-100');
      if (window.gsap) {
        gsap.killTweensOf(barInner);
        gsap.fromTo(barInner, { width: '0%' }, { width: '75%', duration: 0.45, ease: 'power1.out' });
      } else {
        barInner.style.width = '70%';
      }
    }

    // Show floating KalmiPrep micro-pill only if transition exceeds 70ms
    clearTimeout(loadingPillTimer);
    loadingPillTimer = setTimeout(() => {
      if (pill) {
        pill.classList.remove('opacity-0', 'scale-90');
        pill.classList.add('opacity-100', 'scale-100');
        if (window.gsap) {
          gsap.fromTo(pill, { scale: 0.9, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.2, ease: 'back.out(1.5)' });
        }
      }
    }, 70);
  }

  function finishLoadingIndicator() {
    clearTimeout(loadingPillTimer);
    const bar = document.getElementById('page-loading-bar');
    const barInner = document.getElementById('page-loading-bar-inner');
    const pill = document.getElementById('page-loading-pill');

    // Immediately dismiss micro-pill badge
    if (pill) {
      if (window.gsap) {
        gsap.to(pill, {
          opacity: 0,
          scale: 0.9,
          duration: 0.15,
          ease: 'power2.in',
          onComplete: () => {
            pill.classList.remove('opacity-100', 'scale-100');
            pill.classList.add('opacity-0', 'scale-90');
          }
        });
      } else {
        pill.classList.add('opacity-0', 'scale-90');
      }
    }

    // Finish hairline top beam
    if (bar && barInner) {
      if (window.gsap) {
        gsap.to(barInner, {
          width: '100%',
          duration: 0.15,
          ease: 'power2.out',
          onComplete: () => {
            gsap.to(bar, {
              opacity: 0,
              duration: 0.15,
              onComplete: () => {
                barInner.style.width = '0%';
              }
            });
          }
        });
      } else {
        barInner.style.width = '100%';
        setTimeout(() => {
          bar.classList.add('opacity-0');
          barInner.style.width = '0%';
        }, 150);
      }
    }
  }

  // --- GSAP GLOWING ORB MOVEMENT ---
  function moveOrb(orb, container, targetEl, glowSelector, immediate = false, isMobile = false) {
    if (!orb || !container || !targetEl) return;

    const containerRect = container.getBoundingClientRect();
    const targetRect = targetEl.getBoundingClientRect();

    if (containerRect.width === 0 || targetRect.width === 0) return;

    const targetLeft = targetRect.left - containerRect.left;
    const targetWidth = targetRect.width;

    if (immediate || !window.gsap) {
      orb.style.left = targetLeft + 'px';
      orb.style.width = targetWidth + 'px';
      orb.style.opacity = '1';
      return;
    }

    gsap.killTweensOf(orb);
    const glowEl = orb.querySelector(glowSelector);
    if (glowEl) gsap.killTweensOf(glowEl);

    // Physics translation
    gsap.to(orb, {
      left: targetLeft,
      width: targetWidth,
      opacity: 1,
      duration: isMobile ? 0.42 : 0.35,
      ease: isMobile ? 'power3.out' : 'power2.out',
      overwrite: 'auto'
    });

    // Subtle tactile squash & stretch
    gsap.timeline()
      .to(orb, { scaleX: 1.05, scaleY: 0.95, duration: 0.12, ease: 'power2.out' })
      .to(orb, { scaleX: 1.0, scaleY: 1.0, duration: 0.24, ease: 'back.out(2)' });

    // Ambient orb pulse
    if (glowEl) {
      gsap.fromTo(
        glowEl,
        { scale: 0.75, opacity: 0.3 },
        { scale: 1.25, opacity: 0.85, duration: 0.35, yoyo: true, repeat: 1, ease: 'power2.out' }
      );
    }

    // Icon micro-spring
    const icon = targetEl.querySelector('i, svg');
    if (icon) {
      gsap.killTweensOf(icon);
      gsap.fromTo(
        icon,
        { scale: 0.82, y: -2 },
        { scale: 1.0, y: 0, duration: 0.36, ease: 'back.out(2.2)' }
      );
    }
  }

  function updateActiveNav(animate = true) {
    const activeSection = getActiveSection();

    // 1. Mobile Bottom Bar
    const mobileContainer = document.getElementById('bottom-nav-container');
    const mobileOrb = document.getElementById('bottom-nav-orb');
    if (mobileContainer && mobileOrb) {
      const mobileItems = mobileContainer.querySelectorAll('.mobile-nav-item');
      let matchedItem = null;

      mobileItems.forEach((item) => {
        const itemSection = item.getAttribute('data-nav');
        const isMatch = itemSection === activeSection;

        if (isMatch) {
          matchedItem = item;
          item.classList.remove('text-slate-500', 'dark:text-slate-400', 'font-medium');
          item.classList.add('text-brand-600', 'dark:text-brand-400', 'font-bold');
        } else {
          item.classList.remove('text-brand-600', 'dark:text-brand-400', 'font-bold');
          item.classList.add('text-slate-500', 'dark:text-slate-400', 'font-medium');
        }
      });

      if (matchedItem) {
        moveOrb(mobileOrb, mobileContainer, matchedItem, '.orb-glow', !animate, true);
      } else {
        mobileOrb.style.opacity = '0';
      }
    }

    // 2. Desktop Navigation
    const desktopContainer = document.getElementById('desktop-nav');
    const desktopOrb = document.getElementById('desktop-nav-orb');
    if (desktopContainer && desktopOrb) {
      const desktopItems = desktopContainer.querySelectorAll('.desktop-nav-link');
      let matchedItem = null;

      desktopItems.forEach((item) => {
        const itemSection = item.getAttribute('data-nav');
        const isMatch = itemSection === activeSection;

        if (isMatch) {
          matchedItem = item;
          item.classList.remove('text-slate-600', 'dark:text-slate-300', 'font-semibold');
          item.classList.add('text-brand-600', 'dark:text-brand-400', 'font-bold');
        } else {
          item.classList.remove('text-brand-600', 'dark:text-brand-400', 'font-bold');
          item.classList.add('text-slate-600', 'dark:text-slate-300', 'font-semibold');
        }
      });

      if (matchedItem) {
        moveOrb(desktopOrb, desktopContainer, matchedItem, '.desktop-orb-glow', !animate, false);
      } else {
        desktopOrb.style.opacity = '0';
      }
    }
  }

  // --- OPTIMISTIC PREFETCH & CACHING ENGINE ---
  async function prefetchPage(url) {
    const key = normalizeUrl(url);
    if (!key || pageCache.has(key) || prefetchingUrls.has(key)) return;

    // Skip non-GET or special endpoints
    if (key.includes('/logout') || key.includes('/bookmark') || key.includes('/cbt/')) return;

    prefetchingUrls.add(key);

    try {
      const res = await fetch(key, {
        headers: {
          'HX-Request': 'true',
          'HX-Target': 'main-content'
        }
      });
      if (res.ok) {
        const text = await res.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(text, 'text/html');
        const mainEl = doc.getElementById('main-content');
        const titleEl = doc.querySelector('title');

        if (mainEl) {
          pageCache.set(key, {
            title: titleEl ? titleEl.textContent : document.title,
            mainHtml: mainEl.innerHTML,
            timestamp: Date.now()
          });
          persistCache();
        }
      }
    } catch (e) {
      // Network failure, ignore prefetch
    } finally {
      prefetchingUrls.delete(key);
    }
  }

  function applyCachedPage(key, cached, pushHistory = true) {
    const mainEl = document.getElementById('main-content');
    if (!mainEl) return false;

    // Instant DOM swap
    mainEl.innerHTML = cached.mainHtml;
    if (cached.title) {
      document.title = cached.title;
    }

    if (pushHistory) {
      window.history.pushState({ path: key }, cached.title, key);
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'instant' });

    // Render KaTeX math and Lucide icons
    if (window.renderMathAndIcons) {
      window.renderMathAndIcons(mainEl);
    }

    // Update active orb
    updateActiveNav(true);

    // Subtle content entrance animation
    if (window.gsap) {
      gsap.fromTo(mainEl, { opacity: 0.88, y: 6 }, { opacity: 1, y: 0, duration: 0.2, ease: 'power1.out' });
    }

    // Close mobile hamburger menu if open
    const mobileMenu = document.getElementById('mobile-menu');
    if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
      mobileMenu.classList.add('hidden');
    }

    // Brief celebratory flash of loading beam to signify instantaneous swap
    startLoadingIndicator();
    setTimeout(finishLoadingIndicator, 60);

    // Silent background revalidation (Stale-While-Revalidate)
    revalidateInBackground(key);

    return true;
  }

  async function revalidateInBackground(key) {
    try {
      const res = await fetch(key, {
        headers: {
          'HX-Request': 'true',
          'HX-Target': 'main-content'
        }
      });
      if (res.ok) {
        const text = await res.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(text, 'text/html');
        const mainEl = doc.getElementById('main-content');
        const titleEl = doc.querySelector('title');

        if (mainEl) {
          pageCache.set(key, {
            title: titleEl ? titleEl.textContent : document.title,
            mainHtml: mainEl.innerHTML,
            timestamp: Date.now()
          });
          persistCache();
        }
      }
    } catch (e) {}
  }

  // --- EVENT LISTENERS & PREFETCH TRIGGERS ---

  // 1. TouchStart & MouseEnter: Trigger pre-fetching ahead of tap/click
  function attachPrefetchTriggers() {
    document.querySelectorAll('a[data-nav], a[hx-boost="true"]').forEach((link) => {
      const href = link.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;

      // Desktop hover prefetch
      link.addEventListener('mouseenter', () => prefetchPage(href), { passive: true });
      // Mobile touchstart prefetch (fires 100-250ms before click event!)
      link.addEventListener('touchstart', () => prefetchPage(href), { passive: true });
    });
  }

  // 2. Click Handler: Optimistic Instant Swap
  document.addEventListener('click', (e) => {
    const navLink = e.target.closest('a[data-nav]');
    if (!navLink) return;

    const href = navLink.getAttribute('href');
    const key = normalizeUrl(href);

    // Immediate physical feedback: move orb
    const mobileContainer = document.getElementById('bottom-nav-container');
    const mobileOrb = document.getElementById('bottom-nav-orb');
    if (mobileContainer && mobileOrb && mobileContainer.contains(navLink)) {
      moveOrb(mobileOrb, mobileContainer, navLink, '.orb-glow', false, true);
    }
    const desktopContainer = document.getElementById('desktop-nav');
    const desktopOrb = document.getElementById('desktop-nav-orb');
    if (desktopContainer && desktopOrb && desktopContainer.contains(navLink)) {
      moveOrb(desktopOrb, desktopContainer, navLink, '.desktop-orb-glow', false, false);
    }

    // Check if we have an instant cached copy
    if (key && pageCache.has(key)) {
      e.preventDefault();
      e.stopPropagation();
      applyCachedPage(key, pageCache.get(key), true);
      return;
    }

    // Otherwise show subtle reloading indicator while HTMX fulfills request
    startLoadingIndicator();
  });

  // 3. HTMX Lifecycle Events
  document.addEventListener('htmx:beforeRequest', (e) => {
    startLoadingIndicator();
  });

  document.addEventListener('htmx:afterSwap', (e) => {
    finishLoadingIndicator();

    if (e.detail && e.detail.target && e.detail.target.id === 'main-content') {
      const currentUrl = normalizeUrl(window.location.href);
      const mainEl = e.detail.target;

      // Cache newly swapped page in memory
      pageCache.set(currentUrl, {
        title: document.title,
        mainHtml: mainEl.innerHTML,
        timestamp: Date.now()
      });
      persistCache();

      // Synchronize active states and orb location
      updateActiveNav(true);

      // Re-attach hover/touchstart prefetch listeners
      attachPrefetchTriggers();

      // Close mobile menu
      const mobileMenu = document.getElementById('mobile-menu');
      if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
        mobileMenu.classList.add('hidden');
      }
    }
  });

  document.addEventListener('htmx:responseError', finishLoadingIndicator);
  document.addEventListener('htmx:sendError', finishLoadingIndicator);
  document.addEventListener('htmx:afterOnLoad', finishLoadingIndicator);

  // 4. Popstate (Browser Back/Forward)
  window.addEventListener('popstate', (e) => {
    const key = normalizeUrl(window.location.href);
    if (pageCache.has(key)) {
      applyCachedPage(key, pageCache.get(key), false);
    } else {
      updateActiveNav(true);
    }
  });

  // 5. Window Resize
  window.addEventListener('resize', () => {
    updateActiveNav(false);
  });

  // 6. Initial Load & Background Warmup
  document.addEventListener('DOMContentLoaded', () => {
    // Cache the initial rendered page
    const currentUrl = normalizeUrl(window.location.href);
    const mainEl = document.getElementById('main-content');
    if (mainEl) {
      pageCache.set(currentUrl, {
        title: document.title,
        mainHtml: mainEl.innerHTML,
        timestamp: Date.now()
      });
      persistCache();
    }

    // Attach prefetch triggers
    attachPrefetchTriggers();

    setTimeout(() => {
      updateActiveNav(false);
    }, 60);

    // Warm up core navigation paths during idle time (so first click is 0ms!)
    setTimeout(() => {
      const corePaths = ['/curriculum/subjects/', '/practice/setup/', '/questions/', '/progress/dashboard/'];
      corePaths.forEach(p => {
        if (!pageCache.has(p)) {
          prefetchPage(p);
        }
      });
    }, 1200);
  });

  // Global handle
  window.KalmiNav = {
    update: updateActiveNav,
    prefetch: prefetchPage,
    clearCache: () => pageCache.clear()
  };
})();
