# KalmiPrep Mobile Markup Patterns Reference

Copy-paste ready, field-tested markup patterns adhering to the `kalmiprep-all-round-mobile-responsiveness` standard.

---

## 1. Responsive Table-to-Card Stack Pattern

For tabular data (e.g. Leaderboards, Student Rosters, Transaction Ledgers):

```html
<div class="space-y-4">
  <!-- Desktop / Tablet Table View (hidden below md: 768px) -->
  <div class="hidden md:block overflow-x-auto rounded-2xl border border-slate-200 dark:border-navy-800 bg-white dark:bg-navy-900 shadow-sm">
    <table class="w-full text-left text-sm">
      <thead class="bg-slate-50 dark:bg-navy-950/60 text-xs uppercase tracking-wider text-slate-500 font-semibold border-b border-slate-200 dark:border-navy-800">
        <tr>
          <th class="px-4 py-3.5">Student</th>
          <th class="px-4 py-3.5">Status</th>
          <th class="px-4 py-3.5 text-right">Score</th>
          <th class="px-4 py-3.5 text-right">Action</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100 dark:divide-navy-800">
        {% for item in items %}
        <tr class="hover:bg-slate-50/50 dark:hover:bg-navy-800/40 transition-colors">
          <td class="px-4 py-3 font-medium text-slate-900 dark:text-white">{{ item.name }}</td>
          <td class="px-4 py-3 text-xs">{{ item.status_badge|safe }}</td>
          <td class="px-4 py-3 text-right font-mono font-bold">{{ item.score }}%</td>
          <td class="px-4 py-3 text-right">
            <a href="{{ item.url }}" class="text-xs font-bold text-brand-600 hover:underline">View &rarr;</a>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- Mobile Card Stack View (visible ONLY on mobile screens < 768px) -->
  <div class="md:hidden space-y-3">
    {% for item in items %}
    <div class="p-4 rounded-2xl bg-white dark:bg-navy-900 border border-slate-200 dark:border-navy-800 shadow-sm space-y-3">
      <div class="flex items-center justify-between">
        <h4 class="text-sm font-bold text-slate-900 dark:text-white truncate max-w-[200px]">{{ item.name }}</h4>
        <span class="text-xs font-mono font-extrabold text-brand-600 dark:text-brand-400">{{ item.score }}%</span>
      </div>
      <div class="flex items-center justify-between text-xs pt-1 border-t border-slate-100 dark:border-navy-800">
        <span class="text-slate-500">{{ item.status_badge|safe }}</span>
        <a href="{{ item.url }}" class="inline-flex items-center gap-1 font-bold text-brand-600 dark:text-brand-400 py-1.5 px-3 rounded-lg bg-brand-50 dark:bg-navy-800 min-h-[36px]">
          <span>Details</span>
          <i data-lucide="chevron-right" class="w-3.5 h-3.5"></i>
        </a>
      </div>
    </div>
    {% endfor %}
  </div>
</div>
```

---

## 2. Mobile Bottom-Sheet Modal Pattern

Dialogs that render centered on desktop but snap as an accessible bottom-sheet on mobile devices:

```html
<!-- Modal Backdrop Container -->
<div id="cbt-submit-modal" 
     class="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-slate-950/70 backdrop-blur-xs p-0 sm:p-4 hidden transition-opacity duration-200"
     role="dialog" 
     aria-modal="true" 
     aria-labelledby="modal-title">
  
  <!-- Sheet Dialog Surface -->
  <div class="w-full sm:max-w-md bg-white dark:bg-navy-900 rounded-t-3xl sm:rounded-2xl border-t sm:border border-slate-200 dark:border-navy-800 shadow-2xl p-6 space-y-5 max-h-[90dvh] overflow-y-auto pb-safe animate-slide-up sm:animate-fade-in">
    
    <!-- Mobile Drag Handle Affordance -->
    <div class="sm:hidden w-12 h-1.5 rounded-full bg-slate-300 dark:bg-navy-700 mx-auto -mt-1 mb-2"></div>

    <div class="text-center sm:text-left">
      <h3 id="modal-title" class="text-lg font-black text-slate-900 dark:text-white">
        Finish Examination Assessment?
      </h3>
      <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
        Once submitted, responses cannot be edited. Your score will be computed instantly.
      </p>
    </div>

    <!-- Metrics Breakdown Grid -->
    <div class="p-3.5 rounded-xl bg-slate-50 dark:bg-navy-950 border border-slate-200 dark:border-navy-800 grid grid-cols-3 gap-2 text-center text-xs">
      <div>
        <span class="block text-slate-400 text-[10px] uppercase font-bold">Answered</span>
        <strong class="text-emerald-600 text-sm font-mono font-black">38</strong>
      </div>
      <div>
        <span class="block text-slate-400 text-[10px] uppercase font-bold">Unanswered</span>
        <strong class="text-rose-500 text-sm font-mono font-black">2</strong>
      </div>
      <div>
        <span class="block text-slate-400 text-[10px] uppercase font-bold">Flagged</span>
        <strong class="text-amber-500 text-sm font-mono font-black">4</strong>
      </div>
    </div>

    <!-- Actions: Thumb-friendly stacked buttons on mobile -->
    <div class="flex flex-col-reverse sm:flex-row sm:justify-end gap-2.5 pt-2">
      <button type="button" 
              onclick="closeModal()" 
              class="w-full sm:w-auto px-4 py-3 sm:py-2.5 rounded-xl border border-slate-300 dark:border-navy-700 text-xs font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-100 min-h-[44px] flex items-center justify-center">
        Return to Exam
      </button>
      <button type="submit" 
              class="w-full sm:w-auto px-6 py-3 sm:py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-black shadow-sm min-h-[44px] flex items-center justify-center gap-1.5">
        <i data-lucide="check-circle" class="w-4 h-4"></i>
        <span>Confirm Final Submit</span>
      </button>
    </div>

  </div>
</div>
```

---

## 3. KaTeX Formula Horizontal Scroll Wrapper

Ensures matrices, physics derivations, and organic chemistry reaction equations scroll smoothly without expanding the page:

```html
<div class="katex-scroll-wrapper overflow-x-auto overflow-y-hidden max-w-full -webkit-overflow-scrolling-touch touch-pan-x py-1.5 px-1 rounded-xl focus:outline-none focus:ring-1 focus:ring-brand-500" tabindex="0" role="region" aria-label="Mathematical formula container">
  <!-- Formula rendering -->
  <div class="katex-display min-w-0">
    {{ question.question_text|safe }}
  </div>
</div>
```

---

## 4. Mobile Quick Jump Question Ribbon

Compact horizontal strip used in CBT mock exams for 1-click question jumping:

```html
<div class="p-2 rounded-2xl bg-white dark:bg-navy-900 border border-slate-200 dark:border-navy-800 shadow-xs flex items-center gap-1.5 overflow-x-auto no-scrollbar touch-pan-x" role="tablist" aria-label="Question Jump Palette">
  {% for q in questions %}
  <a href="?q={{ q.number }}" 
     class="shrink-0 w-9 h-9 sm:w-10 sm:h-10 rounded-xl text-xs font-bold font-mono flex items-center justify-center transition-all min-h-[36px] min-w-[36px]
            {% if q.is_current %}bg-brand-600 text-white shadow-xs ring-2 ring-brand-400 font-extrabold
            {% elif q.is_answered %}bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800
            {% elif q.is_flagged %}bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 border border-amber-300 dark:border-amber-800
            {% else %}bg-slate-100 dark:bg-navy-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-navy-700{% endif %}"
     role="tab"
     aria-selected="{% if q.is_current %}true{% else %}false{% endif %}"
     aria-label="Question {{ q.number }}">
    {{ q.number }}
  </a>
  {% endfor %}
</div>
```
