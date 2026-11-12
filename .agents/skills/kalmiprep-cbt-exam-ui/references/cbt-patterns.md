# KalmiPrep CBT Layout Patterns Reference

## 1. CBT Exam Header Component
```html
<header class="sticky top-0 z-40 w-full bg-white/95 dark:bg-navy-900/95 backdrop-blur-md border-b border-slate-200 dark:border-navy-800">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
    <!-- Left: Subject & Question Progress -->
    <div class="flex items-center gap-3">
      <span class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300">
        Mathematics
      </span>
      <span class="text-sm font-medium text-slate-500 dark:text-slate-400">
        Question <strong class="text-slate-900 dark:text-white">12</strong> of 40
      </span>
    </div>

    <!-- Center: Authoritative Timer -->
    <div id="examTimer" data-server-deadline="{{ session.deadline_iso }}" class="flex items-center gap-2 px-3.5 py-1.5 rounded-full text-sm font-mono font-bold bg-slate-100 dark:bg-navy-800 text-slate-800 dark:text-slate-100 border border-slate-200 dark:border-navy-700 shadow-sm">
      <i data-lucide="clock" class="w-4 h-4 text-brand-500"></i>
      <span id="timerCountdown">44:12</span>
    </div>

    <!-- Right: Calculator & Submit Actions -->
    <div class="flex items-center gap-2">
      <button type="button" id="btnOpenCalculator" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-700 dark:text-slate-200 bg-slate-100 dark:bg-navy-800 hover:bg-slate-200 dark:hover:bg-navy-700 transition-colors">
        <i data-lucide="calculator" class="w-4 h-4"></i>
        <span class="hidden sm:inline">Calculator</span>
      </button>
      <button type="button" id="btnSubmitExam" class="px-4 py-1.5 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-brand-600 to-emerald-500 hover:from-brand-500 hover:to-emerald-400 shadow-sm">
        Submit
      </button>
    </div>
  </div>
</header>
```

## 2. Question Option Card Pattern
```html
<label class="group relative flex items-center p-4 rounded-2xl border cursor-pointer transition-all duration-150 select-none bg-white dark:bg-navy-900 border-slate-200 dark:border-navy-800 hover:border-brand-500/60 dark:hover:border-brand-500/60 hover:bg-slate-50/50 dark:hover:bg-navy-850 has-[:checked]:border-brand-500 has-[:checked]:bg-brand-50/30 dark:has-[:checked]:bg-brand-950/20 has-[:checked]:ring-1 has-[:checked]:ring-brand-500">
  <input type="radio" name="selected_option" value="B" class="w-4 h-4 text-brand-600 focus:ring-brand-500 border-slate-300 dark:border-navy-700 dark:bg-navy-800">
  <span class="ml-3 font-semibold text-sm w-7 h-7 rounded-lg flex items-center justify-center bg-slate-100 dark:bg-navy-800 text-slate-700 dark:text-slate-300 group-has-[:checked]:bg-brand-500 group-has-[:checked]:text-white">
    B
  </span>
  <div class="ml-3 text-sm text-slate-800 dark:text-slate-200 font-sans katex-wrapper">
    \( x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a} \)
  </div>
</label>
```
