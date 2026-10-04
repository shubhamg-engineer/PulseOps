from app.components.theme import get_status_style

def render_status_chip(status_key: str, size: str = "normal") -> str:
    """Return HTML string for status pill with icon + text (never color alone)."""
    meta = get_status_style(status_key)
    font_size = "0.72rem" if size == "small" else "0.78rem"
    padding = "2px 6px" if size == "small" else "3px 9px"
    
    return f"""
    <span class="po-badge" style="
        background-color: {meta['bg']};
        color: {meta['color']};
        border: 1px solid {meta['border']};
        font-size: {font_size};
        padding: {padding};
    ">
        <span>{meta['icon']}</span>
        <span>{meta['label']}</span>
    </span>
    """
