/**
 * HTML sanitization utility for model output.
 * Prevents XSS from any model-generated content rendered as HTML/markdown.
 */

/**
 * Sanitize text content by escaping HTML entities.
 * Used before rendering any model-generated content.
 */
export function sanitizeHtml(input: string): string {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(input));
  return div.innerHTML;
}

/**
 * Basic markdown-to-HTML converter with sanitization.
 * Only supports safe subset: bold, italic, lists, links, code.
 * All output is escaped first, then markdown patterns applied.
 */
export function renderSafeMarkdown(input: string): string {
  // First escape all HTML
  let safe = sanitizeHtml(input);

  // Convert markdown patterns (on already-escaped text)
  // Bold: **text** or __text__
  safe = safe.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  safe = safe.replace(/__(.+?)__/g, '<strong>$1</strong>');

  // Italic: *text* or _text_
  safe = safe.replace(/\*(.+?)\*/g, '<em>$1</em>');
  safe = safe.replace(/_(.+?)_/g, '<em>$1</em>');

  // Inline code: `text`
  safe = safe.replace(/`(.+?)`/g, '<code>$1</code>');

  // Line breaks
  safe = safe.replace(/\n/g, '<br/>');

  // Bullet lists: lines starting with - or *
  safe = safe.replace(/^[-*]\s+(.+)$/gm, '<li>$1</li>');
  safe = safe.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');

  // Numbered lists
  safe = safe.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');

  // Headings
  safe = safe.replace(/^### (.+)$/gm, '<h4>$1</h4>');
  safe = safe.replace(/^## (.+)$/gm, '<h3>$1</h3>');
  safe = safe.replace(/^# (.+)$/gm, '<h2>$1</h2>');

  return safe;
}
