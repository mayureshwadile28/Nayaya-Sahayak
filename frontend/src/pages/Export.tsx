import { useCallback, useState } from 'react';
import type { AnalysisResponse, AppScreen, Language, Translations } from '../types';
import { exportBrief } from '../hooks/useApi';
import { renderSafeMarkdown } from '../utils/sanitize';

interface ExportProps {
  t: (section: keyof Translations, key: string) => string;
  language: Language;
  documentId: string;
  analysis: AnalysisResponse;
  onNavigate: (screen: AppScreen) => void;
}

export default function Export({
  t,
  language,
  documentId,
  onNavigate,
}: ExportProps) {
  const [briefContent, setBriefContent] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    setIsGenerating(true);
    setError(null);

    try {
      const result = await exportBrief(documentId, language);
      setBriefContent(result.content);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Export failed';
      setError(message);
    } finally {
      setIsGenerating(false);
    }
  }, [documentId, language]);

  const handleDownload = useCallback(() => {
    if (!briefContent) return;

    const blob = new Blob([briefContent], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `nyaya_sahayak_brief_${documentId.slice(0, 8)}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [briefContent, documentId]);

  return (
    <section className="animate-fade-in" aria-labelledby="export-heading">
      <button
        id="export-back-btn"
        onClick={() => onNavigate('analysis')}
        className="btn-secondary text-sm mb-6"
      >
        ← {t('common', 'back')}
      </button>

      <h1 id="export-heading" className="font-heading text-3xl font-bold text-white mb-4">
        📥 {t('export', 'title')}
      </h1>

      <p className="text-gray-400 mb-6">{t('export', 'description')}</p>

      {/* Generate Button */}
      {!briefContent && (
        <button
          id="export-generate-btn"
          onClick={handleGenerate}
          disabled={isGenerating}
          className="btn-primary text-lg px-8 py-4 mb-6"
        >
          {isGenerating ? (
            <>
              <span className="spinner mr-2" aria-hidden="true"></span>
              Generating brief...
            </>
          ) : (
            <>📋 Generate Lawyer-Prep Brief</>
          )}
        </button>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 mb-6" role="alert">
          {error}
        </div>
      )}

      {/* Brief Preview */}
      {briefContent && (
        <div className="space-y-4">
          <div className="flex gap-3 mb-4">
            <button
              id="export-download-btn"
              onClick={handleDownload}
              className="btn-accent"
              aria-label={t('export', 'download')}
            >
              📥 {t('export', 'download')}
            </button>
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="btn-secondary"
              aria-label="Regenerate brief"
            >
              🔄 Regenerate
            </button>
          </div>

          <div className="glass-card">
            <h2 className="font-heading text-lg font-semibold text-white mb-4">
              {t('export', 'preview')}
            </h2>
            <div
              className="prose prose-invert prose-sm max-w-none [&_h1]:font-heading [&_h1]:text-xl [&_h2]:font-heading [&_h2]:text-lg [&_h3]:font-heading [&_h3]:text-base [&_h4]:font-heading [&_h4]:text-sm [&_li]:text-gray-300 [&_p]:text-gray-300 [&_strong]:text-white [&_a]:text-primary-400"
              dangerouslySetInnerHTML={{ __html: renderSafeMarkdown(briefContent) }}
            />
          </div>
        </div>
      )}
    </section>
  );
}
