import React, { useEffect, useState } from 'react';
import { useLanguage } from '../hooks/useLanguage';

interface ClarificationModalProps {
  questions: string[];
  onSubmit: (answers: string) => Promise<void>;
  onSkip: () => void;
  isSubmitting: boolean;
}

const ClarificationModal = React.memo(function ClarificationModal({
  questions,
  onSubmit,
  onSkip,
  isSubmitting,
}: ClarificationModalProps) {
  const [answers, setAnswers] = useState<string>('');
  const { t } = useLanguage();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isSubmitting) {
        onSkip();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onSkip, isSubmitting]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!answers.trim()) {
      onSkip();
      return;
    }
    await onSubmit(answers);
  };

  if (!questions || questions.length === 0) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="clarification-modal-title"
    >
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 bg-blue-50 dark:bg-blue-900/30">
          <h2 id="clarification-modal-title" className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <svg
              className="w-6 h-6 text-blue-600 dark:text-blue-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            {t('common', 'Clarifying Questions')}
          </h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
            {t('common', 'The AI needs a bit more information to give you the most accurate summary.')}
          </p>
        </div>

        <div className="p-6 overflow-y-auto">
          <div className="space-y-4 mb-6">
            {questions.map((q, i) => (
              <div key={i} className="flex gap-3">
                <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-sm font-medium">
                  {i + 1}
                </span>
                <p className="text-gray-800 dark:text-gray-200">{q}</p>
              </div>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="answers"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                {t('common', 'Your Answers (Optional)')}
              </label>
              <textarea
                id="answers"
                rows={4}
                value={answers}
                onChange={(e) => setAnswers(e.target.value)}
                aria-label={t('common', 'Your Answers (Optional)')}
                className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors resize-none"
                placeholder={t('common', 'Type your answers here...')}
              />
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button
                type="button"
                onClick={onSkip}
                disabled={isSubmitting}
                className="px-5 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-colors disabled:opacity-50"
              >
                {t('common', 'Skip')}
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !answers.trim()}
                className="px-5 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    {t('common', 'Submitting...')}
                  </>
                ) : (
                  t('common', 'Submit Answers')
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
});

export default ClarificationModal;
