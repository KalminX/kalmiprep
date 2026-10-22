import html
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="smart_ellipsis", is_safe=True)
def smart_ellipsis(value, length=24):
    """
    Truncates text exceeding `length` with an ellipsis ('…'),
    rendering an interactive, accessible element that:
    1. Expands on click / tap to reveal the full string.
    2. Automatically collapses back when the user scrolls or moves away.
    """
    if not value:
        return ""

    text = str(value).strip()
    try:
        max_len = int(length)
    except (ValueError, TypeError):
        max_len = 24

    if len(text) <= max_len:
        return text

    # Shorten text cleanly at max_len
    short_text = text[:max_len].rstrip() + "…"

    escaped_full = html.escape(text)
    escaped_short = html.escape(short_text)

    # Render interactive expandable element with data attributes
    html_out = (
        f'<span class="kalmi-smart-ellipsis inline-flex items-center gap-1 cursor-pointer select-none max-w-full '
        f'transition-all duration-150 rounded px-1 -mx-0.5 hover:bg-slate-100 dark:hover:bg-slate-800" '
        f'data-full-text="{escaped_full}" '
        f'data-short-text="{escaped_short}" '
        f'data-expanded="false" '
        f'title="Tap or click to view full text" '
        f'tabindex="0" role="button" aria-expanded="false">'
        f'<span class="ellipsis-text font-inherit break-words">{escaped_short}</span>'
        f'<span class="ellipsis-icon text-[10px] text-slate-400 dark:text-slate-500 transition-transform duration-200">▾</span>'
        f'</span>'
    )
    return mark_safe(html_out)


@register.filter(name="smart_ellipsis_words", is_safe=True)
def smart_ellipsis_words(value, count=8):
    """
    Word-based version of smart_ellipsis.
    Truncates after `count` words with interactive expansion.
    """
    if not value:
        return ""

    text = str(value).strip()
    words = text.split()
    try:
        max_words = int(count)
    except (ValueError, TypeError):
        max_words = 8

    if len(words) <= max_words:
        return text

    short_text = " ".join(words[:max_words]) + "…"

    escaped_full = html.escape(text)
    escaped_short = html.escape(short_text)

    html_out = (
        f'<span class="kalmi-smart-ellipsis inline-flex items-center gap-1 cursor-pointer select-none max-w-full '
        f'transition-all duration-150 rounded px-1 -mx-0.5 hover:bg-slate-100 dark:hover:bg-slate-800" '
        f'data-full-text="{escaped_full}" '
        f'data-short-text="{escaped_short}" '
        f'data-expanded="false" '
        f'title="Tap or click to view full text" '
        f'tabindex="0" role="button" aria-expanded="false">'
        f'<span class="ellipsis-text font-inherit break-words">{escaped_short}</span>'
        f'<span class="ellipsis-icon text-[10px] text-slate-400 dark:text-slate-500 transition-transform duration-200">▾</span>'
        f'</span>'
    )
    return mark_safe(html_out)


@register.filter(name="highlight_search", is_safe=True)
def highlight_search(text, search_query):
    """
    Safely highlights search terms within text without corrupting HTML tags
    or KaTeX / LaTeX mathematical formulas ($...$, \\(...\\), \\[[...\\], $$...$$).
    Applies accessible, high-contrast amber highlighting in both light and dark modes.
    """
    if not text or not search_query:
        return text or ""

    import re

    query_str = str(search_query).strip()
    if not query_str:
        return text

    # Extract search tokens with length >= 2, stripping quotes
    tokens = [re.escape(t.strip("\"'")) for t in query_str.split() if len(t.strip("\"'")) >= 2]
    if not tokens:
        return text

    # Match HTML tags and LaTeX math blocks
    delim_pattern = re.compile(r"(<[^>]+>|\$\$[\s\S]*?\$\$|\$[^$\n]+?\$|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\))")
    parts = delim_pattern.split(str(text))

    token_pattern = re.compile(r"(" + "|".join(sorted(tokens, key=len, reverse=True)) + r")", re.IGNORECASE)

    result = []
    for part in parts:
        if not part:
            continue
        is_delim = (
            (part.startswith("<") and part.endswith(">")) or
            (part.startswith("$") and part.endswith("$")) or
            (part.startswith(r"\(") and part.endswith(r"\)")) or
            (part.startswith(r"\[") and part.endswith(r"\]"))
        )
        if is_delim:
            result.append(part)
        else:
            highlighted = token_pattern.sub(
                r'<mark class="bg-amber-100 dark:bg-amber-950 text-amber-900 dark:text-amber-200 font-semibold px-1 py-0.5 rounded border border-amber-300 dark:border-amber-700/60 shadow-xs">\1</mark>',
                part
            )
            result.append(highlighted)

    return mark_safe("".join(result))


@register.filter(name="has_search_term")
def has_search_term(text, search_query):
    """
    Returns True if any meaningful token (len >= 2) from search_query
    is present in text (case-insensitive). Used to automatically reveal
    the explanation drawer if the searched keyword was found in the solution.
    """
    if not text or not search_query:
        return False

    import re

    query_str = str(search_query).strip()
    if not query_str:
        return False

    tokens = [re.escape(t.strip("\"'")) for t in query_str.split() if len(t.strip("\"'")) >= 2]
    if not tokens:
        return False

    pattern = re.compile(r"(" + "|".join(tokens) + r")", re.IGNORECASE)
    return bool(pattern.search(str(text)))

