import { useEffect, useState } from 'react';
import {
  Home, Users, ChevronDown, ChevronUp, ChevronRight,
  Settings, RotateCcw, FileText, Eye, EyeOff, Check, Loader2,
} from 'lucide-react';
import { useIdentity } from '../../hooks/useIdentity';
import { useLlmConfig } from '../../hooks/useLlmConfig';
import { SectionLabel } from './ui/SectionLabel';
import type { Document } from '../../api/documents';

const PROVIDERS = ['Ollama (local)', 'OpenAI', 'Anthropic', 'Groq', 'Azure OpenAI'];

interface LeftSidebarProps {
  documents: Document[];
  docsLoading: boolean;
}

function InlineLabel({ children }: { children: React.ReactNode }) {
  return <label className="block mb-1 text-[11px] font-medium text-muted-fg">{children}</label>;
}

export function LeftSidebar({ documents, docsLoading }: LeftSidebarProps) {
  const { identity, setAccessKey } = useIdentity();
  const { config, loading: llmLoading, save } = useLlmConfig();

  // Knowledge base expand/collapse
  const [expanded, setExpanded] = useState<string[]>(['🔒 Private', '🌐 Public']);

  // Access key
  const [keyPanelOpen, setKeyPanelOpen] = useState(false);
  const [keyOpen,      setKeyOpen]      = useState(false);
  const [editKey,      setEditKey]      = useState('');

  // LLM panel
  const [llmOpen,        setLlmOpen]        = useState(false);
  const [provider,       setProvider]       = useState(PROVIDERS[0]);
  const [showProviders,  setShowProviders]  = useState(false);
  const [model,          setModel]          = useState('');
  const [baseUrl,        setBaseUrl]        = useState('');
  const [apiKey,         setApiKey]         = useState('');
  const [showKey,        setShowKey]        = useState(false);
  const [saving,         setSaving]         = useState(false);
  const [showSuccess,    setShowSuccess]    = useState(false);
  const [saveError,      setSaveError]      = useState<string | null>(null);

  const groups = [
    { label: '🔒 Private', files: documents.filter((d) => d.visibility === 'private') },
    { label: '🌐 Public',  files: documents.filter((d) => d.visibility === 'public') },
  ].filter((g) => g.files.length > 0);

  const displayKey = identity?.access_key ?? '········';
  const initials   = identity ? identity.access_key.slice(0, 2).toUpperCase() : 'RA';

  const toggleGroup = (label: string) =>
    setExpanded((prev) => prev.includes(label) ? prev.filter((l) => l !== label) : [...prev, label]);

  const handleKeySave = () => {
    const trimmed = editKey.trim();
    if (trimmed) setAccessKey(trimmed);
    setKeyOpen(false);
    setEditKey('');
    setKeyPanelOpen(false);
  };

  useEffect(() => {
    if (config && llmOpen) {
      setModel(config.model);
      setBaseUrl(config.base_url);
      setApiKey('');
    }
  }, [config, llmOpen]);

  const handleLlmApply = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      await save({
        model:    model.trim()    || undefined,
        base_url: baseUrl.trim() || undefined,
        api_key:  apiKey.trim()  || undefined,
      });
      setShowSuccess(true);
      setTimeout(() => {
        setShowSuccess(false);
        setLlmOpen(false);
      }, 1800);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="w-[280px] h-screen flex-shrink-0 flex flex-col bg-surface-1">

      {/* ── User identity ─────────────────────────────────────── */}
      <div className="px-4 pt-5 pb-4 border-b border-border-subtle">
        <div className="flex items-center gap-3 cursor-pointer opacity-100 hover:opacity-80 transition-opacity">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-600 to-indigo-600 flex items-center justify-center text-white text-sm font-medium shrink-0">
            {initials}
          </div>
          <span className="flex-1 text-sm font-medium text-primary">RAG Assistant</span>
          <ChevronDown size={16} className="text-secondary" />
        </div>
      </div>

      {/* ── Scrollable nav ────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">

        {/* WORKSPACE */}
        <div>
          <SectionLabel>Workspace</SectionLabel>
          <div className="space-y-1">
            <div className="flex items-center gap-3 h-9 px-3 rounded-lg bg-accent text-white cursor-pointer">
              <Home size={16} />
              <span className="text-sm">Home</span>
            </div>
            <div className="flex items-center gap-3 h-9 px-3 rounded-lg text-primary cursor-pointer hover:bg-surface-2 transition-colors">
              <Users size={16} />
              <span className="text-sm">Team</span>
            </div>
          </div>
        </div>

        {/* KNOWLEDGE BASE */}
        <div>
          <SectionLabel>Knowledge Base</SectionLabel>
          <div className="space-y-1">
            {docsLoading && (
              <p className="px-3 py-2 text-xs text-muted-fg">Loading...</p>
            )}
            {!docsLoading && groups.length === 0 && (
              <p className="px-3 py-2 text-xs text-muted-fg">No documents yet.</p>
            )}
            {groups.map(({ label, files }) => (
              <div key={label}>
                <button
                  type="button"
                  onClick={() => toggleGroup(label)}
                  className="w-full flex items-center gap-2 h-9 px-3 rounded-lg text-primary hover:bg-surface-2 transition-colors"
                >
                  {expanded.includes(label)
                    ? <ChevronDown size={14}  className="text-muted-fg shrink-0" />
                    : <ChevronRight size={14} className="text-muted-fg shrink-0" />}
                  <span className="flex-1 text-sm text-left">{label}</span>
                  <span className="text-[11px] text-muted-fg bg-surface-3 px-1.5 py-0.5 rounded">
                    {files.length}
                  </span>
                </button>
                {expanded.includes(label) && (
                  <div className="ml-6 mt-0.5 space-y-0.5">
                    {files.map((doc) => (
                      <div
                        key={doc.source_id}
                        className="h-8 px-3 rounded-lg flex items-center gap-2 text-xs text-secondary cursor-default hover:bg-surface-2 transition-colors"
                        title={doc.filename}
                      >
                        <FileText size={12} className="text-muted-fg shrink-0" />
                        <span className="truncate">{doc.filename}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="h-px bg-border-subtle" />

        {/* ACCESS KEY */}
        <div>
          <button
            type="button"
            onClick={() => {
              setKeyPanelOpen((o) => !o);
              setKeyOpen(false);
              setEditKey('');
            }}
            className="w-full flex items-center gap-2 h-9 px-3 rounded-lg text-primary hover:bg-surface-2 transition-colors"
          >
            <span className="text-sm shrink-0">🔑</span>
            <span className="flex-1 text-sm text-left">Access Key</span>
            {!keyPanelOpen && identity && (
              <span className="text-[10px] text-muted-fg mr-1" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                {identity.access_key.slice(0, 6)}…
              </span>
            )}
            {keyPanelOpen
              ? <ChevronUp size={14} className="text-muted-fg shrink-0" />
              : <ChevronDown size={14} className="text-muted-fg shrink-0" />}
          </button>

          {keyPanelOpen && (
            <div className="mt-2 px-1 animate-fade-up">
              {!keyOpen ? (
                <div className="px-3 py-3 rounded-lg bg-surface-2 space-y-2">
                  <div
                    className="text-sm text-primary break-all"
                    style={{ fontFamily: 'JetBrains Mono, monospace' }}
                  >
                    {displayKey}
                  </div>
                  <p className="text-[11px] text-muted-fg leading-relaxed">
                    Same key = same private documents, across sessions and devices.
                  </p>
                  <button
                    type="button"
                    onClick={() => { setKeyOpen(true); setEditKey(''); }}
                    className="w-full h-8 rounded-lg flex items-center justify-between px-3 text-xs text-secondary bg-surface-3 hover:bg-surface-3/80 transition-colors"
                  >
                    <span className="flex items-center gap-2">
                      <RotateCcw size={13} />
                      Change / restore key
                    </span>
                    <ChevronRight size={13} />
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <input
                    type="text"
                    value={editKey}
                    onChange={(e) => setEditKey(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleKeySave()}
                    placeholder="Enter your key…"
                    autoFocus
                    className="w-full h-9 px-3 rounded-lg text-sm text-primary bg-background border border-border-default outline-none focus:border-accent transition-colors"
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={handleKeySave}
                      className="flex-1 h-9 rounded-lg text-xs font-medium text-white bg-accent hover:bg-accent-hover transition-colors"
                    >
                      Save
                    </button>
                    <button
                      type="button"
                      onClick={() => { setKeyOpen(false); setEditKey(''); }}
                      className="flex-1 h-9 rounded-lg text-xs text-secondary bg-surface-3 hover:bg-surface-3/80 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="h-px bg-border-subtle" />

        {/* LLM PROVIDER */}
        <div>
          <button
            type="button"
            onClick={() => { setLlmOpen((o) => !o); setShowProviders(false); setSaveError(null); }}
            className="w-full flex items-center gap-2 h-9 px-3 rounded-lg text-primary hover:bg-surface-2 transition-colors"
          >
            <Settings size={14} className="text-muted-fg shrink-0" />
            <span className="flex-1 text-sm text-left">LLM Provider</span>
            {llmOpen
              ? <ChevronUp size={14} className="text-muted-fg" />
              : <ChevronDown size={14} className="text-muted-fg" />}
          </button>

          {llmOpen && (
            <div className="mt-2 px-1 space-y-3 animate-fade-up">
              {llmLoading ? (
                <div className="flex items-center gap-2 py-4 text-xs text-muted-fg">
                  <Loader2 size={14} className="animate-spin" /> Loading...
                </div>
              ) : (
                <>
                  {/* Provider */}
                  <div>
                    <InlineLabel>Provider</InlineLabel>
                    <button
                      type="button"
                      onClick={() => setShowProviders((v) => !v)}
                      className="w-full h-9 px-3 rounded-lg flex items-center justify-between text-sm text-primary bg-background border border-border-default hover:border-border-strong transition-colors"
                    >
                      <span>{provider}</span>
                      <ChevronDown size={14} className="text-muted-fg" />
                    </button>
                    {showProviders && (
                      <div className="mt-1 rounded-lg overflow-hidden border border-border-default bg-background">
                        {PROVIDERS.map((p) => (
                          <button
                            key={p}
                            type="button"
                            onClick={() => { setProvider(p); setShowProviders(false); }}
                            className="w-full h-9 px-3 flex items-center justify-between text-sm text-primary hover:bg-surface-2 transition-colors"
                          >
                            <span>{p}</span>
                            {p === provider && <Check size={13} className="text-accent" />}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Model */}
                  <div>
                    <InlineLabel>Model</InlineLabel>
                    <input
                      type="text"
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      className="w-full h-9 px-3 rounded-lg text-sm text-primary bg-background border border-border-default outline-none focus:border-accent transition-colors"
                    />
                  </div>

                  {/* Base URL */}
                  <div>
                    <InlineLabel>Base URL</InlineLabel>
                    <input
                      type="text"
                      value={baseUrl}
                      onChange={(e) => setBaseUrl(e.target.value)}
                      className="w-full h-9 px-3 rounded-lg text-sm text-primary bg-background border border-border-default outline-none focus:border-accent transition-colors"
                    />
                  </div>

                  {/* API Key */}
                  <div>
                    <InlineLabel>
                      API Key{' '}
                      {config?.api_key_set && (
                        <span className="text-success font-normal">(set)</span>
                      )}
                    </InlineLabel>
                    <div className="relative">
                      <input
                        type={showKey ? 'text' : 'password'}
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder={config?.api_key_set ? 'leave blank to keep' : 'not required'}
                        className="w-full h-9 px-3 pr-9 rounded-lg text-sm text-primary bg-background border border-border-default outline-none focus:border-accent transition-colors"
                      />
                      <button
                        type="button"
                        onClick={() => setShowKey((v) => !v)}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-fg hover:text-secondary transition-colors"
                      >
                        {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                    </div>
                  </div>

                  {/* Apply */}
                  <button
                    type="button"
                    onClick={handleLlmApply}
                    disabled={saving}
                    className="w-full h-9 rounded-lg flex items-center justify-center gap-2 text-sm font-semibold text-white bg-accent hover:bg-accent-hover disabled:opacity-60 transition-colors"
                  >
                    {saving && <Loader2 size={14} className="animate-spin" />}
                    {saving ? 'Saving…' : 'Apply'}
                  </button>

                  {saveError && (
                    <div className="px-3 py-2 rounded-lg text-xs text-red-400 bg-red-950/40 border border-red-800/40 animate-fade-up">
                      {saveError}
                    </div>
                  )}

                  {showSuccess && (
                    <div className="px-3 py-2 rounded-lg flex items-center gap-2 bg-success-dark border border-success/30 animate-fade-up">
                      <Check size={12} className="text-success shrink-0" />
                      <span className="text-xs text-primary">
                        Switched to <strong className="text-success">{model}</strong>
                      </span>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        {/* Bottom padding so content isn't flush against the footer */}
        <div className="h-2" />
      </div>

      {/* ── Footer ────────────────────────────────────────────── */}
      <div className="px-4 py-3 border-t border-border-subtle">
        <p className="text-[10px] text-muted-fg text-center">
          ⚡ Powered by Qdrant · Inngest · Groq
        </p>
      </div>
    </div>
  );
}
