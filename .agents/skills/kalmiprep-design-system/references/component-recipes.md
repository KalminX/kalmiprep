# KalmiPrep Component Recipes Reference

Copy-paste standard Tailwind patterns for consistency across all templates.

## 1. Buttons

### Secondary Surface Button
```html
<button type="button" class="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-navy-800 border border-slate-200 dark:border-navy-700 hover:bg-slate-50 dark:hover:bg-navy-750 active:scale-[0.98] shadow-subtle transition-all duration-150">
  <i data-lucide="filter" class="w-4 h-4 text-slate-400"></i>
  <span>Filter Topics</span>
</button>
```

### Ghost Icon Button
```html
<button type="button" class="p-2 rounded-xl text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-navy-800 transition-colors duration-150">
  <i data-lucide="bookmark" class="w-5 h-5"></i>
</button>
```

### Danger Action Button
```html
<button type="button" class="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-sm font-medium text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 hover:bg-rose-100 dark:hover:bg-rose-900/50 transition-colors duration-150">
  <i data-lucide="trash-2" class="w-4 h-4"></i>
  <span>Clear Session</span>
</button>
```

---

## 2. Form Inputs

### Text Input with Icon
```html
<div class="relative">
  <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400 dark:text-slate-500">
    <i data-lucide="search" class="w-4 h-4"></i>
  </div>
  <input type="text" class="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm bg-white dark:bg-navy-900 border border-slate-200 dark:border-navy-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all" placeholder="Search calculus, stoichiometry, optics...">
</div>
```

---

## 3. Cards & Containers

### Interactive Subject Selection Card
```html
<a href="#" class="group relative block p-5 rounded-2xl bg-white dark:bg-navy-900 border border-slate-200/80 dark:border-navy-800 hover:border-brand-500/60 dark:hover:border-brand-500/60 shadow-card hover:shadow-elevated transition-all duration-200">
  <div class="flex items-start justify-between">
    <div class="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/60 flex items-center justify-center text-blue-600 dark:text-blue-400">
      <i data-lucide="sigma" class="w-5 h-5"></i>
    </div>
    <span class="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-navy-800 text-slate-600 dark:text-slate-400">
      1,420 Questions
    </span>
  </div>
  <h3 class="mt-4 font-semibold text-slate-900 dark:text-white group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
    Mathematics
  </h3>
  <p class="mt-1 text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
    Algebra, Calculus, Trigonometry, Statistics and Geometry for JAMB & WAEC.
  </p>
</a>
```

---

## 4. Modal Backdrop & Dialog
```html
<div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm transition-opacity">
  <div class="w-full max-w-lg p-6 rounded-3xl bg-white dark:bg-navy-900 border border-slate-200 dark:border-navy-750 shadow-elevated">
    <!-- Header, Body, Footer -->
  </div>
</div>
```
