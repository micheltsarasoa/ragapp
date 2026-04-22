import { useRef, useState } from 'react';
import { UploadCloud, LayoutGrid, FileText, ChevronDown, Globe, Lock, Trash2, Loader2, RefreshCw } from 'lucide-react';
import { useIdentity } from '../../hooks/useIdentity';
import { uploadDocument, type Document } from '../../api/documents';
import { IconButton } from './ui/IconButton';
import { StatusBadge } from './ui/StatusBadge';

const ACCEPTED_EXTENSIONS = new Set(['.pdf', '.docx', '.txt', '.md']);
const MAX_BYTES = 10 * 1024 * 1024;

interface CenterPanelProps {
  documents: Document[];
  loading: boolean;
  error: string | null;
  reload: () => void;
  updateVisibility: (source_id: string, visibility: 'public' | 'private') => Promise<void>;
  deleteDocument: (source_id: string) => Promise<void>;
}

export function CenterPanel({ documents, loading, error, reload, updateVisibility, deleteDocument }: CenterPanelProps) {
  const { identity } = useIdentity();
  const fileInputRef   = useRef<HTMLInputElement>(null);
  const [isDragging,   setIsDragging]   = useState(false);
  const [uploading,    setUploading]    = useState(false);
  const [uploadMsg,    setUploadMsg]    = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  const handleFileSelect = async (file: File) => {
    const ext = '.' + (file.name.split('.').pop() ?? '').toLowerCase();
    if (!ACCEPTED_EXTENSIONS.has(ext)) {
      setUploadMsg({ type: 'error', text: `Unsupported file type: ${ext}. Allowed: PDF, DOCX, TXT, MD.` });
      return;
    }
    if (file.size > MAX_BYTES) {
      setUploadMsg({ type: 'error', text: `File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Max 10 MB.` });
      return;
    }
    if (!identity) return;
    setUploading(true);
    setUploadMsg(null);
    try {
      await uploadDocument(file, 'private', identity.user_id);
      setUploadMsg({ type: 'success', text: `"${file.name}" queued for indexing.` });
      reload();
    } catch (err) {
      setUploadMsg({ type: 'error', text: err instanceof Error ? err.message : 'Upload failed' });
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  };

  const handleDeleteClick = (source_id: string) => {
    if (pendingDelete === source_id) {
      deleteDocument(source_id).finally(() => setPendingDelete(null));
    } else {
      setPendingDelete(source_id);
    }
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return iso;
    }
  };

  return (
    <div className="flex-1 h-screen overflow-y-auto bg-background">
      <div className="p-6">
        <h1 className="mb-6 text-xl font-semibold text-primary">Upload Knowledge</h1>

        {/* ── Drop zone ─────────────────────────────────────────── */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => !uploading && fileInputRef.current?.click()}
          className={`mb-6 rounded-xl cursor-pointer transition-all border-2 border-dashed flex items-center justify-center
            ${isDragging
              ? 'border-accent bg-accent/5'
              : 'border-border-default hover:border-border-strong hover:bg-surface-1/40'}`}
          style={{ height: '160px' }}
        >
          <div className="text-center pointer-events-none">
            {uploading ? (
              <Loader2 size={32} className="animate-spin text-accent mx-auto mb-3" />
            ) : (
              <UploadCloud size={32} className={`mx-auto mb-3 transition-colors ${isDragging ? 'text-accent' : 'text-muted-fg'}`} />
            )}
            <p className="text-sm font-medium text-primary mb-1">
              {uploading ? 'Uploading...' : 'Click to upload or drag and drop'}
            </p>
            <p className="text-xs text-muted-fg">PDF, TXT, MD or DOCX (max. 10 MB)</p>
          </div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFileSelect(f); }}
          className="hidden"
        />

        {/* ── Upload feedback ───────────────────────────────────── */}
        {uploadMsg && (
          <div className={`mb-4 px-4 py-3 rounded-lg text-sm animate-fade-up border
            ${uploadMsg.type === 'success'
              ? 'bg-success-dark text-success border-success/30'
              : 'bg-red-950/40 text-red-400 border-red-800/40'}`}
          >
            {uploadMsg.text}
          </div>
        )}

        {/* ── Breadcrumb + actions ──────────────────────────────── */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 text-[13px]">
            <span className="text-muted-fg">Home</span>
            <span className="text-muted-fg">›</span>
            <span className="font-medium text-primary">Knowledge Base</span>
          </div>
          <div className="flex items-center gap-1">
            <IconButton onClick={reload} title="Refresh"><RefreshCw size={18} /></IconButton>
            <IconButton title="Grid view"><LayoutGrid size={18} /></IconButton>
          </div>
        </div>

        {/* ── States ───────────────────────────────────────────── */}
        {loading && (
          <div className="flex items-center gap-2 text-sm text-muted-fg">
            <Loader2 size={16} className="animate-spin" /> Loading documents...
          </div>
        )}
        {error && !loading && (
          <div className="px-4 py-3 rounded-lg text-sm bg-red-950/40 text-red-400 border border-red-800/40">
            {error}
          </div>
        )}
        {!loading && !error && documents.length === 0 && (
          <div className="text-center py-12 text-sm text-muted-fg">
            No documents yet. Upload one to get started.
          </div>
        )}

        {/* ── Document table ────────────────────────────────────── */}
        {!loading && documents.length > 0 && (
          <div className="rounded-xl overflow-hidden bg-surface-1">
            {/* Header */}
            <div className="h-10 flex items-center px-4 border-b border-border-subtle">
              <div className="flex-1 flex items-center gap-1 text-[11px] font-semibold text-muted-fg tracking-wider uppercase">
                File Name <ChevronDown size={12} />
              </div>
              <div className="w-24 text-[11px] font-semibold text-muted-fg tracking-wider uppercase">Visibility</div>
              <div className="w-24 text-[11px] font-semibold text-muted-fg tracking-wider uppercase">Added</div>
              <div className="w-20" />
            </div>

            {/* Rows */}
            {documents.map((doc) => {
              const isConfirming = pendingDelete === doc.source_id;
              return (
                <div
                  key={doc.source_id}
                  className="h-[52px] flex items-center px-4 border-b border-border-subtle last:border-b-0 hover:bg-surface-2 transition-colors animate-fade-up"
                >
                  {/* Filename */}
                  <div className="flex-1 flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 bg-surface-2">
                      <FileText size={16} className="text-accent" />
                    </div>
                    <span className="truncate text-sm font-medium text-primary">{doc.filename}</span>
                  </div>

                  {/* Visibility toggle */}
                  <div className="w-24">
                    <button
                      type="button"
                      onClick={() => updateVisibility(doc.source_id, doc.visibility === 'public' ? 'private' : 'public')}
                      title={`Click to make ${doc.visibility === 'public' ? 'private' : 'public'}`}
                      className="transition-colors"
                    >
                      <StatusBadge variant={doc.visibility === 'public' ? 'success' : 'neutral'}>
                        {doc.visibility === 'public' ? <Globe size={11} /> : <Lock size={11} />}
                        {doc.visibility}
                      </StatusBadge>
                    </button>
                  </div>

                  {/* Date */}
                  <div className="w-24 text-[13px] text-muted-fg">{formatDate(doc.uploaded_at)}</div>

                  {/* Delete */}
                  <div className="w-20 flex justify-end">
                    <button
                      type="button"
                      onClick={() => handleDeleteClick(doc.source_id)}
                      onBlur={() => { if (isConfirming) setPendingDelete(null); }}
                      title={isConfirming ? 'Click again to confirm' : 'Delete'}
                      className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors
                        ${isConfirming
                          ? 'bg-red-950/40 text-red-400 border border-red-800/40'
                          : 'text-muted-fg hover:text-red-400 hover:bg-red-950/30'}`}
                    >
                      <Trash2 size={14} />
                      {isConfirming ? 'Confirm' : 'Delete'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
