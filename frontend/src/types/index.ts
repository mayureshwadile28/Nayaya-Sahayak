/**
 * TypeScript types for Nyaya Sahayak frontend.
 * No `any` types used — all data structures are fully typed.
 */

// --- Enums ---

export type DocumentType = 'rental' | 'employment' | 'consumer' | 'unknown';

export type RiskSeverity = 'high' | 'medium' | 'low';

export type Language = 'en' | 'hi';

export type ExportFormat = 'markdown' | 'pdf';

// --- API Request Types ---

export interface SituationRequest {
  description: string;
  language: Language;
}

export interface AskRequest {
  question: string;
  language: Language;
}

export interface ExportRequest {
  language: Language;
  format: ExportFormat;
}

// --- API Response Types ---

export interface RiskFlag {
  clause_text: string;
  severity: RiskSeverity;
  reason: string;
  category: string;
  legal_reference: string | null;
}

export interface DocumentUploadResponse {
  document_id: string;
  detected_type: DocumentType;
  filename: string | null;
  page_count: number | null;
  message: string;
}

export interface ClarifyResponse {
  questions: string[];
}

export interface AnalysisResponse {
  document_id: string;
  document_type: DocumentType;
  summary: string;
  risk_flags: RiskFlag[];
  key_terms: Record<string, string>;
  parties: string[];
  dates: string[];
  amounts: string[];
}

export interface Citation {
  source: string;
  text: string;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  disclaimer: string;
}

export interface LegalAidInfo {
  eligible_categories: string[];
  forum: string;
  forum_description: string;
  contact_info: Record<string, string>;
  online_portal: string | null;
  filing_process: string;
}

export interface RightsResponse {
  document_type: DocumentType;
  state: string;
  rights: string[];
  legal_aid: LegalAidInfo;
  disclaimer: string;
}

export interface ExportResponse {
  document_id: string;
  filename: string;
  content: string;
  format: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  citations?: Citation[];
}

export interface ErrorResponse {
  error: string;
  detail: string | null;
  status_code: number;
}

// --- UI State Types ---

export type AppScreen =
  | 'landing'
  | 'upload'
  | 'analysis'
  | 'chat'
  | 'rights'
  | 'export';

export interface AppState {
  currentScreen: AppScreen;
  language: Language;
  documentId: string | null;
  documentType: DocumentType | null;
  analysis: AnalysisResponse | null;
  chatMessages: ChatMessage[];
  rights: RightsResponse | null;
  isLoading: boolean;
  error: string | null;
}

// --- i18n Types ---

export interface TranslationSection {
  [key: string]: string;
}

export interface Translations {
  landing: TranslationSection;
  upload: TranslationSection;
  analysis: TranslationSection;
  chat: TranslationSection;
  rights: TranslationSection;
  export: TranslationSection;
  common: TranslationSection;
}
