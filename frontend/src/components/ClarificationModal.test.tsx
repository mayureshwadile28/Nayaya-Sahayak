import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ClarificationModal from './ClarificationModal';

describe('ClarificationModal', () => {
  const defaultProps = {
    questions: [
      'What was the original lease start date?',
      'Did the landlord provide written notice?',
    ],
    onSubmit: vi.fn(),
    onSkip: vi.fn(),
    isSubmitting: false,
  };

  it('renders nothing when questions array is empty', () => {
    const { container } = render(
      <ClarificationModal {...defaultProps} questions={[]} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders dialog with accessibility attributes and questions', () => {
    render(<ClarificationModal {...defaultProps} />);

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'clarification-modal-title');

    expect(screen.getByText('What was the original lease start date?')).toBeInTheDocument();
    expect(screen.getByText('Did the landlord provide written notice?')).toBeInTheDocument();
  });

  it('calls onSkip when Skip button is clicked', () => {
    const onSkip = vi.fn();
    render(<ClarificationModal {...defaultProps} onSkip={onSkip} />);

    const skipButton = screen.getByRole('button', { name: /skip/i });
    fireEvent.click(skipButton);

    expect(onSkip).toHaveBeenCalledTimes(1);
  });

  it('calls onSkip when Escape key is pressed', () => {
    const onSkip = vi.fn();
    render(<ClarificationModal {...defaultProps} onSkip={onSkip} />);

    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
    expect(onSkip).toHaveBeenCalledTimes(1);
  });

  it('submits typed answers when form is submitted', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ClarificationModal {...defaultProps} onSubmit={onSubmit} />);

    const textarea = screen.getByLabelText(/your answers/i);
    fireEvent.change(textarea, { target: { value: 'Lease started Jan 2023, no notice given.' } });

    const submitButton = screen.getByRole('button', { name: /submit answers/i });
    fireEvent.click(submitButton);

    expect(onSubmit).toHaveBeenCalledWith('Lease started Jan 2023, no notice given.');
  });
});
