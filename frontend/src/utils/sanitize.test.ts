import { describe, expect, it } from 'vitest';
import { renderSafeMarkdown, sanitizeHtml } from './sanitize';

describe('sanitizeHtml', () => {
  it('escapes basic HTML tags', () => {
    const input = '<script>alert("xss")</script>';
    const result = sanitizeHtml(input);
    expect(result).not.toContain('<script>');
    expect(result).toContain('&lt;script&gt;');
  });

  it('escapes image onerror payloads', () => {
    const input = '<img src="x" onerror="alert(1)">';
    const result = sanitizeHtml(input);
    expect(result).not.toContain('<img');
    expect(result).toContain('&lt;img');
  });

  it('handles empty string gracefully', () => {
    expect(sanitizeHtml('')).toBe('');
  });

  it('preserves plain text without changes', () => {
    const text = 'Normal legal clause text without html.';
    expect(sanitizeHtml(text)).toBe(text);
  });

  it('escapes special characters like quotes and ampersands', () => {
    const text = 'Landlord & Tenant: "Agreement"';
    const result = sanitizeHtml(text);
    expect(result).toContain('&amp;');
  });
});

describe('renderSafeMarkdown', () => {
  it('converts bold markdown correctly', () => {
    const input = 'This is **important** and __critical__';
    const result = renderSafeMarkdown(input);
    expect(result).toContain('<strong>important</strong>');
    expect(result).toContain('<strong>critical</strong>');
  });

  it('converts italic markdown correctly', () => {
    const input = 'This is *italic* and _emphasized_';
    const result = renderSafeMarkdown(input);
    expect(result).toContain('<em>italic</em>');
    expect(result).toContain('<em>emphasized</em>');
  });

  it('converts inline code correctly', () => {
    const input = 'Use Section `420` of IPC';
    const result = renderSafeMarkdown(input);
    expect(result).toContain('<code>420</code>');
  });

  it('converts markdown headings to headings', () => {
    expect(renderSafeMarkdown('# Title')).toContain('<h2>Title</h2>');
    expect(renderSafeMarkdown('## Subtitle')).toContain('<h3>Subtitle</h3>');
    expect(renderSafeMarkdown('### Section')).toContain('<h4>Section</h4>');
  });

  it('converts newlines to line breaks', () => {
    const input = 'Line 1\nLine 2';
    const result = renderSafeMarkdown(input);
    expect(result).toContain('<br/>');
  });

  it('neutralizes malicious HTML embedded inside markdown', () => {
    const malicious = '**Bold** <script>alert("pwnd")</script>';
    const result = renderSafeMarkdown(malicious);
    expect(result).toContain('<strong>Bold</strong>');
    expect(result).not.toContain('<script>');
    expect(result).toContain('&lt;script&gt;');
  });

  it('handles bullet list lines', () => {
    const input = '- Item 1\n- Item 2';
    const result = renderSafeMarkdown(input);
    expect(result).toContain('<li>Item 1</li>');
    expect(result).toContain('<li>Item 2</li>');
  });
});
