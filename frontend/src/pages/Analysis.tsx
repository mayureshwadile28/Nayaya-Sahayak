import { useEffect } from 'react';
import type { AnalysisResponse, AppScreen, Language, Translations } from '../types';
import { analyzeDocument } from '../hooks/useApi';
import { renderSafeMarkdown, sanitizeHtml } from '../utils/sanitize';

interface AnalysisProps {
  t: (section: keyof Translations, key: string) => string;
  documentId: string;
  analysis: AnalysisResponse | null;
  language: Language;
  onAnalysisComplete: (result: AnalysisResponse) => void;
  onNavigate: (screen: AppScreen) => void;
  setIsLoading: (v: boolean) => void;
  setError: (v: string | null) => void;
  isLoading: boolean;
}

const SEVERITY_CONFIG = {
  high: {
    className: 'severity-high',
    icon: '⚠️',
    ariaLabel: 'High risk',
  },
  medium: {
    className: 'severity-medium',
    icon: '⚡',
    ariaLabel: 'Medium risk',
  },
  low: {
    className: 'severity-low',
    icon: 'ℹ️',
    ariaLabel: 'Low risk',
  },
} as const;

const DOC_TYPE_ICONS: Record<string, string> = {
  rental: '🏠',
  employment: '💼',
  consumer: '🛡️',
  unknown: '📄',
};

export default function Analysis({
  t,
  documentId,
  analysis,
  language,
  onAnalysisComplete,
  onNavigate,
  setIsLoading,
  setError,
  isLoading,
}: AnalysisProps) {
  // Run analysis on mount if not already done
  useEffect(() => {
    if (analysis) return;

    let cancelled = false;
    const runAnalysis = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await analyzeDocument(documentId, language);
        if (!cancelled) {
          onAnalysisComplete(result);
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Analysis failed';
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };
    runAnalysis();
    return () => { cancelled = true; };
  }, [documentId, analysis, language, onAnalysisComplete, setIsLoading, setError]);

  if (isLoading) {
    return (
      <div className="text-center py-20 animate-fade-in" role="status" aria-label="Analyzing document">
        <div className="spinner w-12 h-12 border-4 border-primary-500 border-r-transparent mx-auto mb-4"></div>
        <p className="text-lg text-gray-300">Analyzing your document...</p>
        <p className="text-sm text-gray-500 mt-2">This may take a moment</p>
      </div>
    );
  }

  if (!analysis) return null;

  const docIcon = DOC_TYPE_ICONS[analysis.document_type] || '📄';

  return (
    <section className="animate-fade-in" aria-labelledby="analysis-heading">
      <h1 id="analysis-heading" className="font-heading text-3xl font-bold text-white mb-6">
        {t('analysis', 'title')}
      </h1>

      {/* Document Type Badge */}
      <div className="flex items-center gap-3 mb-6">
        <span className="text-2xl" role="img" aria-hidden="true">{docIcon}</span>
        <span className="px-4 py-1.5 rounded-full bg-primary-600/20 border border-primary-600/30 text-primary-300 font-medium">
          {t('common', `document_type_${analysis.document_type}`)}
        </span>
      </div>

      {/* Summary */}
      <div className="glass-card mb-6">
        <h2 className="font-heading text-xl font-semibold text-white mb-3">
          {t('analysis', 'summary_heading')}
        </h2>
        <div 
          className="text-gray-300 leading-relaxed space-y-2 markdown-content"
          dangerouslySetInnerHTML={{ __html: renderSafeMarkdown(analysis.summary) }}
        />
      </div>

      {/* Key Details Grid */}
      <div className="grid sm:grid-cols-3 gap-4 mb-6 animate-stagger">
        {analysis.parties.length > 0 && (
          <div className="glass-card">
            <h3 className="text-sm font-medium text-gray-400 mb-2">
              {t('analysis', 'parties_heading')}
            </h3>
            <ul className="space-y-1">
              {analysis.parties.slice(0, 5).map((party, i) => (
                <li key={i} className="text-sm text-white">{sanitizeHtml(party)}</li>
              ))}
            </ul>
          </div>
        )}

        {analysis.dates.length > 0 && (
          <div className="glass-card">
            <h3 className="text-sm font-medium text-gray-400 mb-2">
              {t('analysis', 'dates_heading')}
            </h3>
            <ul className="space-y-1">
              {analysis.dates.slice(0, 5).map((date, i) => (
                <li key={i} className="text-sm text-white">{sanitizeHtml(date)}</li>
              ))}
            </ul>
          </div>
        )}

        {analysis.amounts.length > 0 && (
          <div className="glass-card">
            <h3 className="text-sm font-medium text-gray-400 mb-2">
              {t('analysis', 'amounts_heading')}
            </h3>
            <ul className="space-y-1">
              {analysis.amounts.slice(0, 5).map((amount, i) => (
                <li key={i} className="text-sm text-white font-medium">{sanitizeHtml(amount)}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Key Terms */}
      {Object.keys(analysis.key_terms).length > 0 && (
        <div className="glass-card mb-6">
          <h2 className="font-heading text-xl font-semibold text-white mb-3">
            {t('analysis', 'key_terms_heading')}
          </h2>
          <div className="grid sm:grid-cols-2 gap-3">
            {Object.entries(analysis.key_terms).map(([key, value]) => (
              <div key={key} className="flex items-center gap-2 p-2 rounded-lg bg-white/5">
                <span className="text-sm text-gray-400">{key.replace(/_/g, ' ')}:</span>
                <span className="text-sm text-white font-medium">{sanitizeHtml(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk Flags */}
      <div className="glass-card mb-6">
        <h2 className="font-heading text-xl font-semibold text-white mb-4">
          {t('analysis', 'risks_heading')}
        </h2>

        {analysis.risk_flags.length === 0 ? (
          <p className="text-gray-400">{t('analysis', 'no_risks')}</p>
        ) : (
          <div className="space-y-4 animate-stagger">
            {analysis.risk_flags.map((flag, i) => {
              const config = SEVERITY_CONFIG[flag.severity];
              return (
                <div
                  key={i}
                  className="p-4 rounded-xl bg-white/5 border border-white/10 transition-all hover:border-white/20"
                  role="article"
                  aria-label={`${config.ariaLabel}: ${flag.category.replace(/_/g, ' ')}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-0.5">
                      {/* Severity: icon + text label — never color alone */}
                      <span className={config.className} aria-label={config.ariaLabel}>
                        <span role="img" aria-hidden="true">{config.icon}</span>
                        <span>{t('analysis', `severity_${flag.severity}`)}</span>
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-semibold text-white capitalize mb-1">
                        {flag.category.replace(/_/g, ' ')}
                      </h4>
                      <div 
                        className="text-sm text-gray-300 mb-2 markdown-content"
                        dangerouslySetInnerHTML={{ __html: renderSafeMarkdown(flag.reason) }}
                      />
                      <details className="group">
                        <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300 transition-colors">
                          View clause text
                        </summary>
                        <p className="mt-2 text-xs text-gray-400 italic p-2 rounded-lg bg-white/5">
                          "{sanitizeHtml(flag.clause_text)}"
                        </p>
                      </details>
                      {flag.legal_reference && (
                        <p className="text-xs text-primary-400 mt-1">
                          📜 {sanitizeHtml(flag.legal_reference)}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-4">
        <button
          id="analysis-ask-btn"
          onClick={() => onNavigate('chat')}
          className="btn-primary"
          aria-label={t('analysis', 'ask_question')}
        >
          💬 {t('analysis', 'ask_question')}
        </button>
        <button
          id="analysis-rights-btn"
          onClick={() => onNavigate('rights')}
          className="btn-accent"
          aria-label={t('analysis', 'view_rights')}
        >
          📋 {t('analysis', 'view_rights')}
        </button>
        <button
          id="analysis-export-btn"
          onClick={() => onNavigate('export')}
          className="btn-secondary"
          aria-label={t('analysis', 'export_brief')}
        >
          📥 {t('analysis', 'export_brief')}
        </button>
      </div>
    </section>
  );
}
