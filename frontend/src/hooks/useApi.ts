/**
 * API client for Nyaya Sahayak backend.
 * All calls go through this module — no direct fetch() elsewhere.
 */

import type {
  AnalysisResponse,
  AskRequest,
  AskResponse,
  DocumentUploadResponse,
  ExportRequest,
  ExportResponse,
  Language,
  RightsResponse,
  SituationRequest,
} from '../types';

const API_BASE = 'http://localhost:8000/api';

class ApiError extends Error {
  status: number;
  detail: string | null;

  constructor(status: number, message: string, detail: string | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail: string | null = null;
    try {
      const errorData = await response.json();
      detail = errorData.detail || errorData.error || null;
    } catch {
      // Response body isn't JSON
    }
    throw new ApiError(
      response.status,
      detail || `Request failed with status ${response.status}`,
      detail
    );
  }
  return response.json() as Promise<T>;
}

export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/documents`, {
    method: 'POST',
    body: formData,
  });

  return handleResponse<DocumentUploadResponse>(response);
}

export async function describeSituation(
  description: string,
  language: Language = 'en'
): Promise<DocumentUploadResponse> {
  const body: SituationRequest = { description, language };

  const response = await fetch(`${API_BASE}/documents/describe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  return handleResponse<DocumentUploadResponse>(response);
}

export async function analyzeDocument(
  documentId: string,
  language: Language = 'en'
): Promise<AnalysisResponse> {
  const body = { language };
  const response = await fetch(`${API_BASE}/documents/${documentId}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  return handleResponse<AnalysisResponse>(response);
}

export async function askQuestion(
  documentId: string,
  question: string,
  language: Language = 'en'
): Promise<AskResponse> {
  const body: AskRequest = { question, language };

  const response = await fetch(`${API_BASE}/documents/${documentId}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  return handleResponse<AskResponse>(response);
}

export async function getRights(
  docType: string,
  state: string
): Promise<RightsResponse> {
  const params = new URLSearchParams({ doc_type: docType, state });

  const response = await fetch(`${API_BASE}/rights?${params.toString()}`);

  return handleResponse<RightsResponse>(response);
}

export async function exportBrief(
  documentId: string,
  language: Language = 'en',
  format: string = 'markdown'
): Promise<ExportResponse> {
  const body: ExportRequest = { language, format: format as 'markdown' | 'pdf' };

  const response = await fetch(`${API_BASE}/documents/${documentId}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  return handleResponse<ExportResponse>(response);
}

export async function healthCheck(): Promise<{ status: string; service: string }> {
  const response = await fetch(`${API_BASE}/health`);
  return handleResponse<{ status: string; service: string }>(response);
}

export { ApiError };
