import { useCallback, useState, useEffect, lazy, Suspense } from 'react';
import type {
  AnalysisResponse,
  AppScreen,
  ChatMessage,
  DocumentType,
  RightsResponse,
} from './types';
import { useLanguage } from './hooks/useLanguage';
import Landing from './pages/Landing';
import ClarificationModal from './components/ClarificationModal';

// Lazy-load heavy pages to reduce initial bundle size
const Upload = lazy(() => import('./pages/Upload'));
const Analysis = lazy(() => import('./pages/Analysis'));
const Chat = lazy(() => import('./pages/Chat'));
const Rights = lazy(() => import('./pages/Rights'));
const Export = lazy(() => import('./pages/Export'));

function App() {
  const [currentScreen, setCurrentScreen] = useState<AppScreen>('landing');
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [documentType, setDocumentType] = useState<DocumentType | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [rights, setRights] = useState<RightsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clarificationQuestions, setClarificationQuestions] = useState<string[]>([]);
  const [showClarification, setShowClarification] = useState(false);
  const [isSubmittingClarification, setIsSubmittingClarification] = useState(false);
  const { language, toggleLanguage, t } = useLanguage();

  const handleDocumentProcessed = useCallback(
    async (docId: string, docType: DocumentType) => {
      setDocumentId(docId);
      setDocumentType(docType);
      
      try {
        const res = await fetch(`/api/documents/${docId}/clarify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ language }),
        });
        if (res.ok) {
          const data = await res.json();
          if (data.questions && data.questions.length > 0) {
            setClarificationQuestions(data.questions);
            setShowClarification(true);
            return; // Pause transition
          }
        }
      } catch (err) {
        console.error('Clarification failed', err);
      }

      setCurrentScreen('analysis');
      setChatMessages([]);
      setRights(null);
      setError(null);
    },
    [language]
  );

  const handleClarificationSubmit = async (answers: string) => {
    if (!documentId) return;
    setIsSubmittingClarification(true);
    try {
      await fetch(`/api/documents/${documentId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: answers }),
      });
    } catch (err) {
      console.error('Failed to submit answers', err);
    }
    
    setIsSubmittingClarification(false);
    setShowClarification(false);
    setClarificationQuestions([]);
    
    setCurrentScreen('analysis');
    setChatMessages([]);
    setRights(null);
    setError(null);
  };

  const handleClarificationSkip = () => {
    setShowClarification(false);
    setClarificationQuestions([]);
    
    setCurrentScreen('analysis');
    setChatMessages([]);
    setRights(null);
    setError(null);
  };

  const handleAnalysisComplete = useCallback((result: AnalysisResponse) => {
    setAnalysis(result);
  }, []);

  const handleNavigate = useCallback((screen: AppScreen) => {
    setCurrentScreen(screen);
    setError(null);
  }, []);

  const handleAddChatMessage = useCallback((message: ChatMessage) => {
    setChatMessages((prev) => [...prev, message]);
  }, []);

  const handleRightsLoaded = useCallback((result: RightsResponse) => {
    setRights(result);
  }, []);

  const handleStartOver = useCallback(() => {
    setCurrentScreen('landing');
    setDocumentId(null);
    setDocumentType(null);
    setAnalysis(null);
    setChatMessages([]);
    setRights(null);
    setError(null);
  }, []);

  // Invalidate cached text when language changes so it can be re-fetched
  useEffect(() => {
    setAnalysis(null);
    setRights(null);
  }, [language]);

  return (
    <div className="min-h-screen">
      {/* Skip Navigation Link for Accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:bg-accent-500 focus:text-white focus:rounded-lg"
      >
        Skip to main content
      </a>

      {/* Navigation Header */}
      <nav
        className="sticky top-0 z-50 border-b border-white/10"
        style={{ background: 'rgba(15, 23, 42, 0.85)', backdropFilter: 'blur(12px)' }}
        aria-label="Main navigation"
      >
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <button
            id="nav-home-btn"
            onClick={handleStartOver}
            className="flex items-center gap-2 text-lg font-heading font-semibold text-white hover:text-accent-400 transition-colors"
            aria-label="Go to home page"
          >
            <span className="text-2xl" role="img" aria-label="Scale of justice">⚖️</span>
            <span>{t('landing', 'title')}</span>
          </button>

          <div className="flex items-center gap-4">
            {/* Breadcrumb */}
            {currentScreen !== 'landing' && (
              <div className="hidden sm:flex items-center gap-2 text-sm text-gray-400" aria-label="Breadcrumb">
                <button
                  onClick={handleStartOver}
                  className="hover:text-white transition-colors"
                >
                  {t('landing', 'title')}
                </button>
                <span>/</span>
                <span className="text-white capitalize">{currentScreen}</span>
              </div>
            )}

            {/* Language Toggle */}
            <button
              id="language-toggle-btn"
              onClick={toggleLanguage}
              className="btn-secondary text-sm px-3 py-1.5"
              aria-label={`Switch to ${language === 'en' ? 'Hindi' : 'English'}`}
            >
              {language === 'en' ? 'हिंदी' : 'English'}
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main id="main-content" className="max-w-6xl mx-auto px-4 py-8">
        {error && (
          <div
            className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300"
            role="alert"
          >
            <p>{error}</p>
            <button
              onClick={() => setError(null)}
              className="mt-2 text-sm underline hover:text-red-200"
            >
              {t('common', 'retry')}
            </button>
          </div>
        )}

        {showClarification && (
          <ClarificationModal
            questions={clarificationQuestions}
            onSubmit={handleClarificationSubmit}
            onSkip={handleClarificationSkip}
            isSubmitting={isSubmittingClarification}
          />
        )}

        {currentScreen === 'landing' && (
          <Landing
            t={t}
            onNavigate={handleNavigate}
          />
        )}

        {currentScreen === 'upload' && (
          <Suspense fallback={<div className="text-center py-12" role="status" aria-live="polite"><span className="loading-spinner" aria-hidden="true" /><p className="text-gray-400 mt-2">Loading...</p></div>}>
            <Upload
              t={t}
              language={language}
              onDocumentProcessed={handleDocumentProcessed}
              onBack={() => handleNavigate('landing')}
              setIsLoading={setIsLoading}
              setError={setError}
              isLoading={isLoading}
            />
          </Suspense>
        )}

        {currentScreen === 'analysis' && documentId && (
          <Suspense fallback={<div className="text-center py-12" role="status" aria-live="polite"><span className="loading-spinner" aria-hidden="true" /><p className="text-gray-400 mt-2">Analyzing document...</p></div>}>
            <Analysis
              t={t}
              language={language}
              documentId={documentId}
              analysis={analysis}
              onAnalysisComplete={handleAnalysisComplete}
              onNavigate={handleNavigate}
              setIsLoading={setIsLoading}
              setError={setError}
              isLoading={isLoading}
            />
          </Suspense>
        )}

        {currentScreen === 'chat' && documentId && (
          <Suspense fallback={<div className="text-center py-12" role="status" aria-live="polite"><span className="loading-spinner" aria-hidden="true" /><p className="text-gray-400 mt-2">Loading chat...</p></div>}>
            <Chat
              t={t}
              language={language}
              documentId={documentId}
              messages={chatMessages}
              onAddMessage={handleAddChatMessage}
              onNavigate={handleNavigate}
            />
          </Suspense>
        )}

        {currentScreen === 'rights' && documentType && (
          <Suspense fallback={<div className="text-center py-12" role="status" aria-live="polite"><span className="loading-spinner" aria-hidden="true" /><p className="text-gray-400 mt-2">Loading rights information...</p></div>}>
            <Rights
              t={t}
              documentType={documentType}
              rights={rights}
              onRightsLoaded={handleRightsLoaded}
              onNavigate={handleNavigate}
              setError={setError}
            />
          </Suspense>
        )}

        {currentScreen === 'export' && documentId && analysis && (
          <Suspense fallback={<div className="text-center py-12" role="status" aria-live="polite"><span className="loading-spinner" aria-hidden="true" /><p className="text-gray-400 mt-2">Preparing export...</p></div>}>
            <Export
              t={t}
              language={language}
              documentId={documentId}
              analysis={analysis}
              onNavigate={handleNavigate}
            />
          </Suspense>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 mt-16 py-6">
        <div className="max-w-6xl mx-auto px-4 text-center text-sm text-gray-500">
          <p>{t('common', 'disclaimer_short')}</p>
          <p className="mt-1">{t('common', 'powered_by')}</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
