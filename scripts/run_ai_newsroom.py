import html

import ai_newsroom


_original_sanitize = ai_newsroom.sanitize_body_html


def sanitize_with_fallback_link(body_html, allowed_urls):
    cleaned = _original_sanitize(body_html, allowed_urls)
    if ai_newsroom.extract_links(cleaned):
        return cleaned

    allowed = list(allowed_urls)
    if not allowed:
        return cleaned

    source_url = allowed[0]
    safe_url = html.escape(source_url, quote=True)
    fallback = (
        '<p>Read the original source report: '
        f'<a href="{safe_url}" rel="nofollow noopener" target="_blank">source report</a>.</p>'
    )
    return cleaned + fallback


ai_newsroom.sanitize_body_html = sanitize_with_fallback_link

if __name__ == '__main__':
    ai_newsroom.main()
