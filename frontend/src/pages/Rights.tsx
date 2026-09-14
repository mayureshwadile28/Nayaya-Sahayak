import { useCallback, useState } from 'react';
import type { AppScreen, DocumentType, RightsResponse, Translations } from '../types';
import { getRights } from '../hooks/useApi';
import { sanitizeHtml } from '../utils/sanitize';

interface RightsProps {
  t: (section: keyof Translations, key: string) => string;
  documentType: DocumentType;
  rights: RightsResponse | null;
  onRightsLoaded: (result: RightsResponse) => void;
  onNavigate: (screen: AppScreen) => void;
  setError: (v: string | null) => void;
}

const INDIAN_STATES = [
  'Delhi', 'Maharashtra', 'Karnataka', 'Tamil Nadu', 'Uttar Pradesh',
  'Gujarat', 'Rajasthan', 'West Bengal', 'Madhya Pradesh', 'Kerala',
  'Telangana', 'Andhra Pradesh', 'Bihar', 'Punjab', 'Haryana',
  'Odisha', 'Jharkhand', 'Assam', 'Chhattisgarh', 'Uttarakhand',
  'Goa', 'Himachal Pradesh', 'Jammu and Kashmir', 'Tripura',
  'Meghalaya', 'Manipur', 'Nagaland', 'Arunachal Pradesh',
  'Mizoram', 'Sikkim',
];

export default function Rights({
  t,
  documentType,
  rights,
  onRightsLoaded,
  onNavigate,
  setError,
}: RightsProps) {
  const [selectedState, setSelectedState] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleFetchRights = useCallback(async () => {
    if (!selectedState) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await getRights(documentType, selectedState);
      onRightsLoaded(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load rights data';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [selectedState, documentType, onRightsLoaded, setError]);

  return (
    <section className="animate-fade-in" aria-labelledby="rights-heading">
      <button
        id="rights-back-btn"
        onClick={() => onNavigate('analysis')}
        className="btn-secondary text-sm mb-6"
      >
        ← {t('common', 'back')}
      </button>

      <h1 id="rights-heading" className="font-heading text-3xl font-bold text-white mb-6">
        📋 {t('rights', 'title')}
      </h1>

      {/* State Selector */}
      <div className="glass-card mb-6">
        <label htmlFor="state-select" className="block text-sm font-medium text-gray-300 mb-2">
          {t('rights', 'state_label')}
        </label>
        <div className="flex gap-3">
          <select
            id="state-select"
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            className="input-field flex-1"
            aria-label={t('rights', 'state_label')}
          >
            <option value="">{t('rights', 'state_placeholder')}</option>
            {INDIAN_STATES.map((state) => (
              <option key={state} value={state}>{state}</option>
            ))}
          </select>
          <button
            id="rights-fetch-btn"
            onClick={handleFetchRights}
            disabled={!selectedState || isLoading}
            className="btn-primary"
          >
            {isLoading ? <span className="spinner" aria-hidden="true"></span> : 'Go'}
          </button>
        </div>
      </div>

      {rights && (
        <div className="space-y-6 animate-stagger">
          {/* Rights Checklist */}
          <div className="glass-card">
            <h2 className="font-heading text-xl font-semibold text-white mb-4">
              ✅ {t('rights', 'rights_heading')}
            </h2>
            <ul className="space-y-3" role="list">
              {rights.rights.map((right, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3 p-3 rounded-xl bg-white/5 hover:bg-white/8 transition-colors"
                >
                  <span className="text-green-400 flex-shrink-0 mt-0.5" aria-hidden="true">✓</span>
                  <span className="text-sm text-gray-300">{sanitizeHtml(right)}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Forum Info */}
          <div className="glass-card">
            <h2 className="font-heading text-xl font-semibold text-white mb-3">
              🏛️ {t('rights', 'forum_heading')}
            </h2>
            <div className="p-4 rounded-xl bg-primary-600/10 border border-primary-600/20 mb-3">
              <h3 className="font-semibold text-primary-300 mb-1">
                {sanitizeHtml(rights.legal_aid.forum)}
              </h3>
              <p className="text-sm text-gray-300">
                {sanitizeHtml(rights.legal_aid.forum_description)}
              </p>
            </div>

            {rights.legal_aid.filing_process && (
              <div className="mt-4">
                <h3 className="text-sm font-medium text-gray-300 mb-2">
                  {t('rights', 'filing_heading')}
                </h3>
                <p className="text-sm text-gray-400 whitespace-pre-line">
                  {sanitizeHtml(rights.legal_aid.filing_process)}
                </p>
              </div>
            )}

            {rights.legal_aid.online_portal && (
              <div className="mt-4 p-3 rounded-xl bg-accent-500/10 border border-accent-500/20">
                <h3 className="text-sm font-medium text-accent-400 mb-1">
                  {t('rights', 'portal_heading')}
                </h3>
                <a
                  href={rights.legal_aid.online_portal}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-accent-300 underline hover:text-accent-200 transition-colors"
                  aria-label={`Visit ${rights.legal_aid.online_portal}`}
                >
                  {rights.legal_aid.online_portal}
                </a>
              </div>
            )}
          </div>

          {/* Legal Aid Eligibility */}
          <div className="glass-card">
            <h2 className="font-heading text-xl font-semibold text-white mb-3">
              🤝 {t('rights', 'eligibility_heading')}
            </h2>
            <ul className="space-y-2" role="list">
              {rights.legal_aid.eligible_categories.map((cat, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="text-accent-400 flex-shrink-0" aria-hidden="true">•</span>
                  <span className="text-gray-300">{sanitizeHtml(cat)}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Contact Info */}
          <div className="glass-card">
            <h2 className="font-heading text-xl font-semibold text-white mb-3">
              📞 {t('rights', 'contact_heading')}
            </h2>
            <div className="space-y-2">
              {Object.entries(rights.legal_aid.contact_info).map(([key, value]) => (
                <div key={key} className="flex items-start gap-2 text-sm">
                  <span className="text-gray-500 capitalize min-w-[100px]">
                    {key.replace(/_/g, ' ')}:
                  </span>
                  <span className="text-gray-300">{sanitizeHtml(value)}</span>
                </div>
              ))}
            </div>

            <div className="mt-4 p-3 rounded-xl bg-amber-500/5 border border-amber-500/15 text-xs text-amber-300/80" role="note">
              {t('rights', 'verification_note')}
            </div>
          </div>

          {/* Disclaimer */}
          <div className="disclaimer-banner" role="note">
            {sanitizeHtml(rights.disclaimer)}
          </div>
        </div>
      )}
    </section>
  );
}
