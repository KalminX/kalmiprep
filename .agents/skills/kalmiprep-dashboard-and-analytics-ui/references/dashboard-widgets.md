# KalmiPrep Dashboard Widgets Reference

## 1. Circular SVG Mastery Progress Ring
```html
<div class="relative w-20 h-20 flex items-center justify-center">
  <svg class="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
    <!-- Background Track -->
    <path class="text-slate-100 dark:text-navy-800" stroke-width="3.5" stroke="currentColor" fill="none"
      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
    <!-- Progress Indicator -->
    <path class="text-brand-500 transition-all duration-1000 ease-out" stroke-dasharray="78, 100" stroke-width="3.5" stroke-linecap="round" stroke="currentColor" fill="none"
      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
  </svg>
  <div class="absolute flex flex-col items-center">
    <span class="text-sm font-bold text-slate-900 dark:text-white font-mono">78%</span>
  </div>
</div>
```

## 2. Teacher Wallet Balance Hero Card
```html
<div class="relative overflow-hidden p-6 rounded-3xl bg-gradient-to-br from-navy-900 via-navy-850 to-navy-950 text-white border border-navy-700/80 shadow-elevated">
  <div class="flex items-center justify-between">
    <span class="text-xs font-semibold tracking-wider uppercase text-slate-400">Teacher Wallet</span>
    <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-brand-500/20 text-brand-300 border border-brand-500/30">
      Verified Tutor
    </span>
  </div>
  <div class="mt-4">
    <span class="text-xs text-slate-400">Available Balance</span>
    <h2 class="text-3xl font-extrabold tracking-tight font-mono text-white mt-0.5">₦42,500.00</h2>
  </div>
  <div class="mt-6 pt-4 border-t border-navy-800 flex items-center justify-between">
    <span class="text-xs text-slate-400">Pending Review: <strong class="text-slate-200">₦0.00</strong></span>
    <button type="button" class="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-brand-600 hover:bg-brand-500 transition-colors shadow-sm">
      Request Withdrawal
    </button>
  </div>
</div>
```
