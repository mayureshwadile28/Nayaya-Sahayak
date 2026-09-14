import { useCallback, useRef, useState } from 'react';
import type { DocumentType, Language, Translations } from '../types';
import { uploadDocument, describeSituation } from '../hooks/useApi';

interface UploadProps {
  t: (section: keyof Translations, key: string) => string;
  language: Language;
  onDocumentProcessed: (docId: string, docType: DocumentType) => Promise<void>;
  onBack: () => void;
  setIsLoading: (v: boolean) => void;
  setError: (v: string | null) => void;
  isLoading: boolean;
}

export default function Upload({
  t,
  language,
  onDocumentProcessed,
  onBack,
  setIsLoading,
  setError,
  isLoading,
}: UploadProps) {
  const [description, setDescription] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback((file: File) => {
    const allowedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
      'image/jpeg',
      'image/png',
    ];
    const maxSize = 10 * 1024 * 1024; // 10MB

    if (!allowedTypes.includes(file.type)) {
      setError('File type not supported. Please upload a PDF, DOCX, JPG, or PNG file.');
      return;
    }

    if (file.size > maxSize) {
      setError('File too large. Maximum size is 10MB.');
      return;
    }

    setSelectedFile(file);
    setError(null);
  }, [setError]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFileSelect(file);
    },
    [handleFileSelect]
  );

  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await uploadDocument(selectedFile);
      await onDocumentProcessed(result.document_id, result.detected_type);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [selectedFile, onDocumentProcessed, setIsLoading, setError]);

  const handleDescribe = useCallback(async () => {
    if (description.trim().length < 20) {
      setError('Please describe your situation in at least 20 characters.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await describeSituation(description, language);
      await onDocumentProcessed(result.document_id, result.detected_type);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to process description';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [description, language, onDocumentProcessed, setIsLoading, setError]);

  return (
    <section className="animate-fade-in" aria-labelledby="upload-heading">
      <button
        id="upload-back-btn"
        onClick={onBack}
        className="btn-secondary text-sm mb-6"
        aria-label={t('common', 'back')}
      >
        ← {t('common', 'back')}
      </button>

      <h1 id="upload-heading" className="font-heading text-3xl font-bold text-white mb-8">
        {t('upload', 'title')}
      </h1>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Upload Section */}
        <div className="glass-card">
          <h2 className="font-heading text-xl font-semibold text-white mb-3">
            <span role="img" aria-hidden="true" className="mr-2">📄</span>
            {t('upload', 'upload_heading')}
          </h2>
          <p className="text-sm text-gray-400 mb-4">{t('upload', 'upload_desc')}</p>

          {/* Drop Zone */}
          <div
            className={`drop-zone ${isDragOver ? 'drag-over' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }}
            role="button"
            tabIndex={0}
            aria-label={t('upload', 'drag_drop')}
            id="file-drop-zone"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc,.jpg,.jpeg,.png"
              onChange={(e) => { if (e.target.files?.[0]) handleFileSelect(e.target.files[0]); }}
              className="hidden"
              id="file-input"
              aria-label="Select file to upload"
            />
            <div className="text-4xl mb-3" role="img" aria-hidden="true">📁</div>
            <p className="text-gray-300 mb-1">{t('upload', 'drag_drop')}</p>
            <p className="text-xs text-gray-500">{t('upload', 'upload_formats')}</p>
          </div>

          {/* Selected File */}
          {selectedFile && (
            <div className="mt-4 p-3 rounded-xl bg-primary-600/10 border border-primary-600/20 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span role="img" aria-hidden="true">📎</span>
                <span className="text-sm text-white truncate max-w-[200px]">{selectedFile.name}</span>
                <span className="text-xs text-gray-400">
                  ({(selectedFile.size / 1024).toFixed(0)} KB)
                </span>
              </div>
              <button
                onClick={() => setSelectedFile(null)}
                className="text-gray-400 hover:text-red-400 transition-colors text-sm"
                aria-label="Remove selected file"
              >
                ✕
              </button>
            </div>
          )}

          <button
            id="upload-submit-btn"
            onClick={handleUpload}
            disabled={!selectedFile || isLoading}
            className="btn-primary w-full mt-4"
            aria-label="Upload and analyze document"
          >
            {isLoading ? (
              <>
                <span className="spinner mr-2" aria-hidden="true"></span>
                {t('upload', 'uploading')}
              </>
            ) : (
              t('upload', 'submit')
            )}
          </button>
        </div>

        {/* Describe Section */}
        <div className="glass-card">
          <h2 className="font-heading text-xl font-semibold text-white mb-3">
            <span role="img" aria-hidden="true" className="mr-2">💬</span>
            {t('upload', 'describe_heading')}
          </h2>
          <p className="text-sm text-gray-400 mb-4">{t('upload', 'describe_desc')}</p>

          <textarea
            id="situation-input"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t('upload', 'describe_placeholder')}
            className="input-field h-48 resize-none"
            aria-label={t('upload', 'describe_heading')}
            maxLength={5000}
          />

          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-gray-500">
              {description.length}/5000
            </span>
            <span className="text-xs text-gray-500">
              Min. 20 characters
            </span>
          </div>

          <button
            id="describe-submit-btn"
            onClick={handleDescribe}
            disabled={description.trim().length < 20 || isLoading}
            className="btn-accent w-full mt-4"
            aria-label="Analyze situation"
          >
            {isLoading ? (
              <>
                <span className="spinner mr-2" aria-hidden="true"></span>
                {t('upload', 'uploading')}
              </>
            ) : (
              t('upload', 'submit')
            )}
          </button>
        </div>
      </div>

      {/* OR Divider (mobile) */}
      <div className="md:hidden flex items-center gap-4 my-6">
        <div className="flex-1 border-t border-white/10"></div>
        <span className="text-gray-500 font-medium">{t('upload', 'or_divider')}</span>
        <div className="flex-1 border-t border-white/10"></div>
      </div>
    </section>
  );
}
