"""Template helpers for the dashboard and public site."""

from django import template
from django.utils.safestring import mark_safe

from apps.common.utils import human_filesize

register = template.Library()


@register.filter
def attr(obj, name):
    """Resolve dotted attribute paths for the generic dashboard tables."""
    if obj is None:
        return ""
    current = obj
    for part in str(name).split("."):
        if current is None:
            return ""
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        current = getattr(current, part, None)
        if callable(current):
            try:
                current = current()
            except TypeError:
                return ""
    return "" if current is None else current


@register.filter
def filesize(value):
    return human_filesize(value)


@register.filter
def initials(value):
    parts = [p for p in str(value or "").replace(".", " ").split() if p]
    if not parts:
        return "LA"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


@register.filter
def percentage(value, total):
    try:
        total = float(total)
        if total <= 0:
            return 0
        return round((float(value) / total) * 100)
    except (TypeError, ValueError):
        return 0


@register.simple_tag
def status_pill(status):
    palette = {
        "draft": "bg-slate-100 text-slate-600 border-slate-200",
        "ready": "bg-amber-50 text-amber-700 border-amber-200",
        "delivered": "bg-emerald-50 text-emerald-700 border-emerald-200",
        "archived": "bg-slate-100 text-slate-500 border-slate-200",
        "new": "bg-sky-50 text-sky-700 border-sky-200",
        "read": "bg-slate-100 text-slate-600 border-slate-200",
        "replied": "bg-emerald-50 text-emerald-700 border-emerald-200",
        "submitted": "bg-amber-50 text-amber-700 border-amber-200",
        "in_review": "bg-sky-50 text-sky-700 border-sky-200",
        "approved": "bg-emerald-50 text-emerald-700 border-emerald-200",
        "in_production": "bg-indigo-50 text-indigo-700 border-indigo-200",
        "completed": "bg-emerald-50 text-emerald-700 border-emerald-200",
        "cancelled": "bg-rose-50 text-rose-700 border-rose-200",
        "active": "bg-emerald-50 text-emerald-700 border-emerald-200",
        "lead": "bg-amber-50 text-amber-700 border-amber-200",
    }
    classes = palette.get(str(status).lower(), "bg-slate-100 text-slate-600 border-slate-200")
    label = str(status).replace("_", " ").title()
    return mark_safe(
        f'<span class="inline-flex items-center rounded-full border px-2.5 py-0.5 '
        f'text-[11px] font-medium tracking-wide {classes}">{label}</span>'
    )


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """Rebuild the querystring keeping existing filters (used for pagination)."""
    request = context.get("request")
    params = request.GET.copy() if request else {}
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    encoded = params.urlencode() if hasattr(params, "urlencode") else ""
    return f"?{encoded}" if encoded else "?"