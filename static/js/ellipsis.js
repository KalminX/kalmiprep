/**
 * KalmiPrep Smart Expandable Ellipsis Engine
 * 1. Puts clean ellipses on text elements that overflow.
 * 2. Reveals full text on tap / click.
 * 3. Automatically collapses back when the user scrolls or moves away (clicks outside / mouseleave).
 */

(function () {
  'use strict';

  function collapseSmartEllipsis(el) {
    if (!el || el.getAttribute('data-expanded') !== 'true') return;

    el.setAttribute('data-expanded', 'false');
    el.setAttribute('aria-expanded', 'false');

    const textEl = el.querySelector('.ellipsis-text');
    const iconEl = el.querySelector('.ellipsis-icon');

    if (textEl && el.dataset.shortText) {
      textEl.textContent = el.dataset.shortText;
    }
    if (iconEl) {
      iconEl.classList.remove('rotate-180', 'text-brand-600', 'dark:text-brand-400');
    }

    el.classList.remove(
      'ring-1',
      'ring-brand-400',
      'dark:ring-brand-500/50',
      'bg-brand-50/90',
      'dark:bg-navy-800',
      'text-brand-700',
      'dark:text-brand-300',
      'shadow-sm',
      'z-20'
    );
  }

  function expandSmartEllipsis(el) {
    if (!el) return;

    // Collapse any previously expanded ellipsis first
    collapseAllSmartEllipses();

    el.setAttribute('data-expanded', 'true');
    el.setAttribute('aria-expanded', 'true');

    const textEl = el.querySelector('.ellipsis-text');
    const iconEl = el.querySelector('.ellipsis-icon');

    if (textEl && el.dataset.fullText) {
      textEl.textContent = el.dataset.fullText;
    }
    if (iconEl) {
      iconEl.classList.add('rotate-180', 'text-brand-600', 'dark:text-brand-400');
    }

    el.classList.add(
      'ring-1',
      'ring-brand-400',
      'dark:ring-brand-500/50',
      'bg-brand-50/90',
      'dark:bg-navy-800',
      'text-brand-700',
      'dark:text-brand-300',
      'shadow-sm',
      'z-20'
    );
  }

  function collapseAllSmartEllipses() {
    document.querySelectorAll('.kalmi-smart-ellipsis[data-expanded="true"]').forEach((el) => {
      collapseSmartEllipsis(el);
    });
  }

  // 1. Click & Tap Toggle Listener
  document.addEventListener('click', (e) => {
    const ellipsisEl = e.target.closest('.kalmi-smart-ellipsis');
    if (ellipsisEl) {
      e.preventDefault();
      e.stopPropagation();
      const isExpanded = ellipsisEl.getAttribute('data-expanded') === 'true';
      if (isExpanded) {
        collapseSmartEllipsis(ellipsisEl);
      } else {
        expandSmartEllipsis(ellipsisEl);
      }
      return;
    }

    // Interactive Option Preview / Truncated text expansion on click
    const optItem = e.target.closest('.option-preview-item');
    if (optItem) {
      const textContainer = optItem.querySelector('.option-text') || optItem.querySelector('.truncate');
      if (textContainer) {
        if (textContainer.classList.contains('truncate')) {
          textContainer.classList.remove('truncate');
          textContainer.classList.add('break-words', 'whitespace-normal');
        } else if (textContainer.classList.contains('line-clamp-1') || textContainer.classList.contains('line-clamp-2')) {
          textContainer.classList.toggle('line-clamp-none');
        }
      }
      return;
    }

    // Generic truncated element expander
    const directTruncate = e.target.closest('.truncate');
    if (directTruncate && !directTruncate.closest('button') && !directTruncate.closest('a')) {
      directTruncate.classList.remove('truncate');
      directTruncate.classList.add('break-words', 'whitespace-normal');
      return;
    }

    // Clicked outside any ellipsis: collapse all open ellipses
    collapseAllSmartEllipses();
  });

  // 2. Keyboard Access (Enter / Space)
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      const ellipsisEl = document.activeElement && document.activeElement.closest('.kalmi-smart-ellipsis');
      if (ellipsisEl) {
        e.preventDefault();
        const isExpanded = ellipsisEl.getAttribute('data-expanded') === 'true';
        if (isExpanded) {
          collapseSmartEllipsis(ellipsisEl);
        } else {
          expandSmartEllipsis(ellipsisEl);
        }
      }
    } else if (e.key === 'Escape') {
      collapseAllSmartEllipses();
    }
  });

  // 3. Scroll Listener: Immediately collapse when user scrolls
  window.addEventListener('scroll', () => {
    collapseAllSmartEllipses();
  }, { passive: true });

  // 4. Mouse Move Away (Desktop)
  document.addEventListener('mousemove', (e) => {
    const expandedList = document.querySelectorAll('.kalmi-smart-ellipsis[data-expanded="true"]');
    if (expandedList.length === 0) return;

    expandedList.forEach((el) => {
      const rect = el.getBoundingClientRect();
      const buffer = 28; // safety margin for gentle mouse movement
      const isInside = (
        e.clientX >= rect.left - buffer &&
        e.clientX <= rect.right + buffer &&
        e.clientY >= rect.top - buffer &&
        e.clientY <= rect.bottom + buffer
      );
      if (!isInside) {
        collapseSmartEllipsis(el);
      }
    });
  }, { passive: true });

  // 5. Touch Outside (Mobile)
  document.addEventListener('touchstart', (e) => {
    if (!e.target.closest('.kalmi-smart-ellipsis')) {
      collapseAllSmartEllipses();
    }
  }, { passive: true });

  // 6. HTMX Route/Content Swap Cleanup
  document.addEventListener('htmx:beforeSwap', () => {
    collapseAllSmartEllipses();
  });

  // Global handle
  window.KalmiEllipsis = {
    collapseAll: collapseAllSmartEllipses,
    expand: expandSmartEllipsis,
    collapse: collapseSmartEllipsis
  };
})();
