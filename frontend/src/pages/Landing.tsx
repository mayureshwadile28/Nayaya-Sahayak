import type { AppScreen, Translations } from '../types';

interface LandingProps {
  t: (section: keyof Translations, key: string) => string;
  onNavigate: (screen: AppScreen) => void;
}

export default function Landing({ t, onNavigate }: LandingProps) {
  return (
    <section className="animate-fade-in" aria-labelledby="landing-heading">
      {/* Hero */}
      <div className="text-center py-12 md:py-20">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent-500/10 border border-accent-500/20 text-accent-400 text-sm font-medium mb-6">
          <span role="img" aria-label="Scale">⚖️</span>
          <span>GenAI Legal Information Tool</span>
        </div>

        <h1
          id="landing-heading"
          className="font-heading text-4xl md:text-6xl font-bold text-white mb-4"
          style={{
            background: 'linear-gradient(135deg, #ffffff 0%, #93c5fd 50%, #fbbf24 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          {t('landing', 'title')}
        </h1>
        <p className="text-xl md:text-2xl text-gray-300 font-heading mb-2">
          {t('landing', 'subtitle')}
        </p>
        <p className="text-lg text-gray-400 max-w-2xl mx-auto mb-8">
          {t('landing', 'tagline')}
        </p>

        {/* Disclaimer — in body copy, not hidden in footer */}
        <div className="disclaimer-banner max-w-2xl mx-auto mb-10" role="note" aria-label="Important disclaimer">
          {t('landing', 'disclaimer')}
        </div>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
          <button
            id="cta-upload-btn"
            onClick={() => onNavigate('upload')}
            className="btn-primary text-lg px-8 py-4"
            aria-label={t('landing', 'cta_upload')}
          >
            <span className="mr-2" role="img" aria-hidden="true">📄</span>
            {t('landing', 'cta_upload')}
          </button>
          <button
            id="cta-describe-btn"
            onClick={() => onNavigate('upload')}
            className="btn-accent text-lg px-8 py-4"
            aria-label={t('landing', 'cta_describe')}
          >
            <span className="mr-2" role="img" aria-hidden="true">💬</span>
            {t('landing', 'cta_describe')}
          </button>
        </div>

        <p className="text-sm text-gray-500">
          {t('landing', 'supported_docs')}
        </p>
      </div>

      {/* Feature Cards */}
      <div className="grid md:grid-cols-3 gap-6 mt-8 animate-stagger">
        <div className="glass-card text-center" role="article">
          <div className="text-3xl mb-3" role="img" aria-label="Rental agreement">🏠</div>
          <h3 className="font-heading text-lg font-semibold text-white mb-2">
            Rental Agreements
          </h3>
          <p className="text-sm text-gray-400">
            Understand deposit terms, notice periods, lock-in clauses, maintenance responsibilities,
            and eviction rights.
          </p>
        </div>

        <div className="glass-card text-center" role="article">
          <div className="text-3xl mb-3" role="img" aria-label="Employment agreement">💼</div>
          <h3 className="font-heading text-lg font-semibold text-white mb-2">
            Employment Contracts
          </h3>
          <p className="text-sm text-gray-400">
            Review offer letters, non-compete clauses, termination terms, payment schedules,
            and gig-work agreements.
          </p>
        </div>

        <div className="glass-card text-center" role="article">
          <div className="text-3xl mb-3" role="img" aria-label="Consumer dispute">🛡️</div>
          <h3 className="font-heading text-lg font-semibold text-white mb-2">
            Consumer Disputes
          </h3>
          <p className="text-sm text-gray-400">
            Analyze defective product notices, refund claims, service complaints,
            and know your consumer rights.
          </p>
        </div>
      </div>

      {/* How It Works */}
      <div className="mt-16 text-center">
        <h2 className="font-heading text-2xl font-semibold text-white mb-8">How It Works</h2>
        <div className="grid md:grid-cols-4 gap-6 animate-stagger">
          {[
            { step: '1', icon: '📤', title: 'Upload or Describe', desc: 'Share your document or describe your situation' },
            { step: '2', icon: '🔍', title: 'AI Analysis', desc: 'AI identifies key terms and flags risks' },
            { step: '3', icon: '💡', title: 'Understand Rights', desc: 'Learn your rights and where to get help' },
            { step: '4', icon: '📋', title: 'Get Prepared', desc: 'Export a brief for your lawyer meeting' },
          ].map((item) => (
            <div key={item.step} className="relative">
              <div className="glass-card text-center py-8">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-7 h-7 rounded-full bg-primary-600 flex items-center justify-center text-sm font-bold text-white">
                  {item.step}
                </div>
                <div className="text-2xl mb-2" role="img" aria-hidden="true">{item.icon}</div>
                <h3 className="font-heading font-semibold text-white text-sm mb-1">{item.title}</h3>
                <p className="text-xs text-gray-400">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
