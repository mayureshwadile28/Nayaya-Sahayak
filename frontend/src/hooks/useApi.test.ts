import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  analyzeDocument,
  ApiError,
  askQuestion,
  describeSituation,
  exportBrief,
  getRights,
  healthCheck,
  uploadDocument,
} from './useApi';

describe('ApiError', () => {
  it('creates an ApiError with status, message and detail', () => {
    const error = new ApiError(404, 'Not Found', 'Document not found.');
    expect(error.name).toBe('ApiError');
    expect(error.status).toBe(404);
    expect(error.message).toBe('Not Found');
    expect(error.detail).toBe('Document not found.');
  });
});

describe('useApi endpoints', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('healthCheck returns status data', async () => {
    const mockData = { status: 'ok', service: 'nyaya-sahayak-backend' };
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    } as unknown as Response);

    const result = await healthCheck();
    expect(result).toEqual(mockData);
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/health'), { signal: undefined });
  });

  it('describeSituation sends JSON body and returns DocumentUploadResponse', async () => {
    const mockResponse = {
      document_id: 'sess-123',
      detected_type: 'rental',
      message: 'Processed',
    };
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    } as unknown as Response);

    const result = await describeSituation('My landlord is evicting me', 'en');
    expect(result).toEqual(mockResponse);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/documents/describe'),
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: 'My landlord is evicting me', language: 'en' }),
      })
    );
  });

  it('analyzeDocument posts to analyze endpoint', async () => {
    const mockAnalysis = {
      document_id: 'sess-123',
      document_type: 'rental',
      summary: 'Summary text',
      risk_score: 35,
      risk_level: 'medium',
      risk_flags: [],
      key_terms: [],
      statute_references: [],
      next_steps: [],
    };
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => mockAnalysis,
    } as unknown as Response);

    const result = await analyzeDocument('sess-123', 'en');
    expect(result.document_id).toBe('sess-123');
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/documents/sess-123/analyze'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ language: 'en' }),
      })
    );
  });

  it('askQuestion sends question and returns answer with citations', async () => {
    const mockAnswer = {
      answer: 'You have protection under Delhi Rent Control Act.',
      citations: [{ source: 'Delhi Rent Act', text: 'Section 14' }],
    };
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => mockAnswer,
    } as unknown as Response);

    const result = await askQuestion('sess-123', 'Can I be evicted without notice?', 'en');
    expect(result.answer).toContain('Delhi Rent Control Act');
    expect(result.citations).toHaveLength(1);
  });

  it('getRights encodes query parameters properly', async () => {
    const mockRights = {
      document_type: 'rental',
      state: 'Maharashtra',
      rights: [],
      disclaimer: 'For informational purposes only.',
    };
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => mockRights,
    } as unknown as Response);

    const result = await getRights('rental', 'Maharashtra');
    expect(result.state).toBe('Maharashtra');
    expect(fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/rights\?doc_type=rental&state=Maharashtra/),
      { signal: undefined }
    );
  });

  it('exportBrief posts format and returns download brief', async () => {
    const mockExport = {
      document_id: 'sess-123',
      filename: 'brief_sess-123.md',
      content: '# Legal Brief',
      format: 'markdown',
    };
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => mockExport,
    } as unknown as Response);

    const result = await exportBrief('sess-123', 'en', 'markdown');
    expect(result.filename).toBe('brief_sess-123.md');
    expect(result.content).toBe('# Legal Brief');
  });

  it('uploadDocument sends multipart form data', async () => {
    const mockUpload = {
      document_id: 'sess-abc',
      detected_type: 'rental',
      filename: 'lease.pdf',
    };
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => mockUpload,
    } as unknown as Response);

    const file = new File(['dummy content'], 'lease.pdf', { type: 'application/pdf' });
    const result = await uploadDocument(file);
    expect(result.document_id).toBe('sess-abc');
  });

  it('throws ApiError with detail message on non-ok response', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Document session expired.' }),
    } as unknown as Response);

    await expect(analyzeDocument('expired-id')).rejects.toThrow('Document session expired.');
  });

  it('handles non-JSON error responses gracefully', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 502,
      json: async () => {
        throw new Error('Not JSON');
      },
    } as unknown as Response);

    await expect(healthCheck()).rejects.toThrow('Request failed with status 502');
  });

  it('respects AbortSignal passed to API calls', async () => {
    const controller = new AbortController();
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'ok', service: 'test' }),
    } as Response);

    await healthCheck(controller.signal);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/health'),
      expect.objectContaining({ signal: controller.signal })
    );
  });
});
