import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import Landing from './Landing';

describe('Landing page', () => {
  const mockT = vi.fn((_section: string, key: string) => {
    const translations: Record<string, string> = {
      title: 'Nyaya Sahayak - Legal AI Assistant',
      subtitle: 'Democratizing Legal Understanding in India',
      tagline: 'Simple, accurate, and confidential document analysis.',
      disclaimer: 'This tool provides informational summaries and does not constitute legal advice.',
      cta_upload: 'Upload Document',
      cta_describe: 'Describe Situation',
      supported_docs: 'Supported: PDF, DOCX, TXT, Images (PNG, JPG)',
    };
    return translations[key] || key;
  });

  const mockNavigate = vi.fn();

  it('renders hero titles, disclaimer, and supported documents note', () => {
    render(<Landing t={mockT} onNavigate={mockNavigate} />);

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Nyaya Sahayak - Legal AI Assistant');
    expect(screen.getByText('Democratizing Legal Understanding in India')).toBeInTheDocument();
    expect(screen.getByRole('note', { name: /important disclaimer/i })).toHaveTextContent(
      'This tool provides informational summaries'
    );
    expect(screen.getByText('Supported: PDF, DOCX, TXT, Images (PNG, JPG)')).toBeInTheDocument();
  });

  it('navigates to upload screen on clicking CTA buttons', () => {
    render(<Landing t={mockT} onNavigate={mockNavigate} />);

    const uploadBtn = screen.getByRole('button', { name: /upload document/i });
    fireEvent.click(uploadBtn);
    expect(mockNavigate).toHaveBeenCalledWith('upload');

    const describeBtn = screen.getByRole('button', { name: /describe situation/i });
    fireEvent.click(describeBtn);
    expect(mockNavigate).toHaveBeenCalledWith('upload');
  });

  it('renders feature cards and How It Works steps', () => {
    render(<Landing t={mockT} onNavigate={mockNavigate} />);

    expect(screen.getByRole('heading', { name: /rental agreements/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /employment contracts/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /consumer disputes/i })).toBeInTheDocument();

    expect(screen.getByRole('heading', { name: /how it works/i })).toBeInTheDocument();
    expect(screen.getByText('Upload or Describe')).toBeInTheDocument();
    expect(screen.getByText('AI Analysis')).toBeInTheDocument();
    expect(screen.getByText('Understand Rights')).toBeInTheDocument();
    expect(screen.getByText('Get Prepared')).toBeInTheDocument();
  });
});
