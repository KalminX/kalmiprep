# KalmiPrep Mobile Navigation Patterns Reference

## 1. Floating Bottom Dock Pattern (`templates/components/bottom_nav.html`)
```html
<nav id="mobileBottomNav" class="md:hidden fixed bottom-3 inset-x-3 z-40 bg-white/90 dark:bg-navy-900/90 backdrop-blur-xl border border-slate-200/80 dark:border-navy-750 rounded-2xl shadow-glass pb-[env(safe-area-inset-bottom,0.5rem)]">
  <div class="grid grid-cols-5 h-14 items-center">
    <!-- Home Tab -->
    <a href="{% url 'core:landing' %}" class="flex flex-col items-center justify-center gap-1 text-slate-500 dark:text-slate-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors {% if request.resolver_match.app_name == 'core' %}text-brand-600 dark:text-brand-400 font-semibold{% endif %}">
      <i data-lucide="home" class="w-5 h-5"></i>
      <span class="text-[10px] tracking-tight">Home</span>
    </a>

    <!-- Curriculum Tab -->
    <a href="{% url 'curriculum:subject_list' %}" class="flex flex-col items-center justify-center gap-1 text-slate-500 dark:text-slate-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors {% if request.resolver_match.app_name == 'curriculum' %}text-brand-600 dark:text-brand-400 font-semibold{% endif %}">
      <i data-lucide="book-open" class="w-5 h-5"></i>
      <span class="text-[10px] tracking-tight">Catalog</span>
    </a>

    <!-- Practice Primary Action Center Floating Button -->
    <a href="{% url 'practice:setup' %}" class="flex flex-col items-center justify-center -mt-5">
      <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-brand-600 to-emerald-400 flex items-center justify-center text-white shadow-[0_4px_16px_rgba(34,197,94,0.45)] hover:scale-105 active:scale-95 transition-transform">
        <i data-lucide="zap" class="w-6 h-6"></i>
      </div>
      <span class="text-[10px] font-semibold text-brand-600 dark:text-brand-400 mt-1">CBT</span>
    </a>

    <!-- Progress Tab -->
    <a href="{% url 'progress:dashboard' %}" class="flex flex-col items-center justify-center gap-1 text-slate-500 dark:text-slate-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors {% if request.resolver_match.app_name == 'progress' %}text-brand-600 dark:text-brand-400 font-semibold{% endif %}">
      <i data-lucide="bar-chart-2" class="w-5 h-5"></i>
      <span class="text-[10px] tracking-tight">Progress</span>
    </a>

    <!-- Account / Classrooms Tab -->
    <a href="{% url 'accounts:profile' %}" class="flex flex-col items-center justify-center gap-1 text-slate-500 dark:text-slate-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors {% if request.resolver_match.app_name == 'accounts' %}text-brand-600 dark:text-brand-400 font-semibold{% endif %}">
      <i data-lucide="user" class="w-5 h-5"></i>
      <span class="text-[10px] tracking-tight">Profile</span>
    </a>
  </div>
</nav>
```
