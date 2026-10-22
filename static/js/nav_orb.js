/**
 * KalmiPrep Navigation Indicator & Highlight Engine
 * Responsibilities:
 * 1. Coordinates top-level route switch loading indicators (hairline beam & indicator pill).
 * 2. Synchronizes active highlight states across desktop navbar and mobile bottom navigation.
 * 3. Listens to HTMX and popstate events to keep navigation UI in sync with current route.
 */

(function () {
  'use strict';

  let loadingPillTimer = null;

  function getActiveSection(pathname) {
    if (!pathname) pathname = window.location.pathname;
    if (pathname === '/' || pathname === '') return 'core';
    if (pathname.startsWith('/curriculum')) return 'curriculum';
    if (pathname.startsWith('/questions')) return 'questions';
    if (pathname.startsWith('/practice')) return 'practice';
    if (pathname.startsWith('/progress') || pathname.startsWith('/accounts')) return 'progress';
    return '';
  }

  // --- SUBTLE KALMIPREP LOADING BEAM & PILL ---
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

  // --- NAVIGATION HIGHLIGHT DOM ALIGNMENT ---
  function syncNavDOM(activeSection) {
    if (!activeSection) activeSection = getActiveSection();

    // 1. Mobile Bottom Bar
    const mobileContainer = document.getElementById('bottom-nav-container');
    if (mobileContainer) {
      const mobileItems = mobileContainer.querySelectorAll('.mobile-nav-item');

      mobileItems.forEach((item) => {
        const itemSection = item.getAttribute('data-nav');
        const isMatch = itemSection === activeSection;
        const isCenterAction = item.querySelector('.bg-gradient-to-tr');

        if (isCenterAction) {
          if (isMatch) {
            item.classList.remove('border-transparent');
            item.classList.add('border-brand-300', 'dark:border-brand-500/50', 'bg-brand-50/70', 'dark:bg-navy-800', 'ring-2', 'ring-brand-500/20');
          } else {
            item.classList.remove('border-brand-300', 'dark:border-brand-500/50', 'bg-brand-50/70', 'dark:bg-navy-800', 'ring-2', 'ring-brand-500/20');
            item.classList.add('border-transparent');
          }
        } else {
          if (isMatch) {
            item.classList.remove('text-slate-500', 'dark:text-slate-400', 'font-medium', 'border-transparent');
            item.classList.add('bg-brand-50/80', 'dark:bg-navy-800', 'text-brand-600', 'dark:text-brand-400', 'font-bold', 'border-brand-200/90', 'dark:border-navy-700', 'shadow-sm');
          } else {
            item.classList.remove('bg-brand-50/80', 'dark:bg-navy-800', 'text-brand-600', 'dark:text-brand-400', 'font-bold', 'border-brand-200/90', 'dark:border-navy-700', 'shadow-sm');
            item.classList.add('text-slate-500', 'dark:text-slate-400', 'font-medium', 'border-transparent');
          }
        }
      });
    }

    // 2. Desktop Navigation
    const desktopContainer = document.getElementById('desktop-nav');
    if (desktopContainer) {
      const desktopItems = desktopContainer.querySelectorAll('.desktop-nav-link');

      desktopItems.forEach((item) => {
        const itemSection = item.getAttribute('data-nav');
        const isMatch = itemSection === activeSection;

        if (isMatch) {
          item.classList.remove('text-slate-600', 'dark:text-slate-400', 'font-medium', 'border-transparent');
          item.classList.add('bg-white', 'dark:bg-navy-800', 'text-brand-600', 'dark:text-brand-400', 'font-bold', 'border-slate-200', 'dark:border-navy-700', 'shadow-sm');
        } else {
          item.classList.remove('bg-white', 'dark:bg-navy-800', 'text-brand-600', 'dark:text-brand-400', 'font-bold', 'border-slate-200', 'dark:border-navy-700', 'shadow-sm');
          item.classList.add('text-slate-600', 'dark:text-slate-400', 'font-medium', 'border-transparent');
        }
      });
    }
  }

  function updateActiveNav() {
    const activeSection = getActiveSection();
    if (window.useKalmiStore) {
      window.useKalmiStore.getState().finishNavTransition(activeSection, false);
    } else {
      syncNavDOM(activeSection);
    }
  }

  // --- ZUSTAND TRANSITION EVENT LISTENERS ---
  window.addEventListener('kalmi:nav-pending-start', () => {
    startLoadingIndicator();
  });

  window.addEventListener('kalmi:nav-pending-finish', (e) => {
    finishLoadingIndicator();
    const activeSection = e.detail?.activeSection || getActiveSection();
    syncNavDOM(activeSection);
  });

  window.addEventListener('kalmi:nav-pending-cancel', () => {
    finishLoadingIndicator();
  });

  // --- HTMX LIFECYCLE HOOKS ---
  document.addEventListener('htmx:beforeRequest', (e) => {
    const target = e.detail?.target;
    if (target && target.id === 'main-content') {
      if (window.useKalmiStore) {
        window.useKalmiStore.getState().startNavTransition(e.detail?.requestConfig?.path || '');
      } else {
        startLoadingIndicator();
      }
    }
  });

  document.addEventListener('htmx:afterSwap', (e) => {
    if (e.detail?.target?.id === 'main-content') {
      const newSection = getActiveSection(window.location.pathname);
      if (window.useKalmiStore) {
        window.useKalmiStore.getState().finishNavTransition(newSection, true);
      } else {
        finishLoadingIndicator();
        syncNavDOM(newSection);
      }

      // Close mobile hamburger menu if open
      const mobileMenu = document.getElementById('mobile-menu');
      if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
        mobileMenu.classList.add('hidden');
      }
    }
  });

  document.addEventListener('htmx:responseError', (e) => {
    if (e.detail?.target?.id === 'main-content') {
      if (window.useKalmiStore) {
        window.useKalmiStore.getState().cancelNavTransition();
      } else {
        finishLoadingIndicator();
      }
    }
  });

  document.addEventListener('htmx:sendError', (e) => {
    if (e.detail?.target?.id === 'main-content') {
      if (window.useKalmiStore) {
        window.useKalmiStore.getState().cancelNavTransition();
      } else {
        finishLoadingIndicator();
      }
    }
  });

  // Browser Back / Forward
  window.addEventListener('popstate', () => {
    updateActiveNav();
  });

  window.addEventListener('resize', () => {
    syncNavDOM();
  });

  // Initial synchronization on load
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(updateActiveNav, 30);
  });

  window.KalmiNav = {
    update: updateActiveNav,
    sync: syncNavDOM
  };

})();
