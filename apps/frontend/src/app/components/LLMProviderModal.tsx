import { useEffect, useState } from 'react';
import { X, Eye, EyeOff, ChevronDown, Check, Loader2 } from 'lucide-react';
import { useLlmConfig } from '../../hooks/useLlmConfig';

interface LLMProviderModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const PROVIDERS = ['Ollama (local)', 'OpenAI', 'Anthropic', 'Groq', 'Azure OpenAI'];

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <label className="block mb-1.5 text-xs font-medium text-secondary">{children}</label>
  );
}

function TextInput({ value, onChange, type = 'text', placeholder }: {
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full h-10 px-3 rounded-lg text-sm text-primary bg-background border border-border-default outline-none focus:border-accent transition-colors"
    />
  );
}

export function LLMProviderModal({ isOpen, onClose }: LLMProviderModalProps) {
  const { config, loading, save } = useLlmConfig();

  const [provider,    setProvider]    = useState(PROVIDERS[0]);
  const [model,       setModel]       = useState('');
  const [baseUrl,     setBaseUrl]     = useState('');
  const [apiKey,      setApiKey]      = useState('');
  const [showKey,     setShowKey]     = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [saving,      setSaving]      = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [saveError,   setSaveError]   = useState<string | null>(null);

  // Populate fields from server config when the modal opens
  useEffect(() => {
    if (config && isOpen) {
      setModel(config.model);
      setBaseUrl(config.base_url);
      setApiKey('');
    }
  }, [config, isOpen]);

  const handleApply = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      await save({
        model:   model.trim()   || undefined,
        base_url: baseUrl.trim() || undefined,
        api_key:  apiKey.trim()  || undefined,
      });
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 3000);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 flex items-center justify-center z-50 animate-fade-in"
      style={{ background: 'rgba(0,0,0,0.6)' }}
      onClick={onClose}
    >
      <div
        className="rounded-2xl p-7 relative animate-scale-in"
        style={{
          width: '480px',
          background: 'var(--surface-l2)',
          border: '1px solid var(--border-strong)',
          boxShadow: '0 24px 48px rgba(0,0,0,0.6)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-1">
          <div>
            <h2 className="text-lg font-semibold text-primary">LLM Provider Management</h2>
            <p className="text-[13px] text-muted-fg mt-0.5">Configure your AI inference backend</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-muted-fg hover:bg-surface-3 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="h-px bg-border-subtle -mx-7 my-6" />

        {loading ? (
          <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-fg">
            <Loader2 size={18} className="animate-spin" /> Loading config...
          </div>
        ) : (
          <div className="space-y-4">

            {/* Provider */}
            <div>
              <FieldLabel>Provider</FieldLabel>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setShowDropdown(!showDropdown)}
                  className="w-full h-10 px-3 rounded-lg flex items-center justify-between text-sm text-primary bg-background border border-border-default hover:border-border-strong transition-colors"
                >
                  <span>{provider}</span>
                  <ChevronDown size={16} className="text-muted-fg" />
                </button>

                {showDropdown && (
                  <div className="absolute top-full left-0 right-0 mt-1 rounded-lg overflow-hidden z-10 border border-border-default bg-surface-1 shadow-lg">
                    {PROVIDERS.map((p) => (
                      <button
                        key={p}
                        type="button"
                        onClick={() => { setProvider(p); setShowDropdown(false); }}
                        className="w-full h-10 px-3 flex items-center justify-between text-sm text-primary hover:bg-surface-2 transition-colors"
                      >
                        <span>{p}</span>
                        {p === provider && <Check size={16} className="text-accent" />}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Model */}
            <div>
              <FieldLabel>Model</FieldLabel>
              <TextInput value={model} onChange={setModel} />
            </div>

            {/* Base URL */}
            <div>
              <FieldLabel>Base URL</FieldLabel>
              <TextInput value={baseUrl} onChange={setBaseUrl} />
            </div>

            {/* API Key */}
            <div>
              <FieldLabel>
                API Key{' '}
                {config?.api_key_set && <span className="text-success font-normal">(currently set)</span>}
              </FieldLabel>
              <div className="relative">
                <TextInput
                  type={showKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={setApiKey}
                  placeholder={config?.api_key_set ? 'leave blank to keep existing' : 'not required'}
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-fg hover:text-secondary transition-colors"
                >
                  {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Apply */}
            <button
              type="button"
              onClick={handleApply}
              disabled={saving}
              className="w-full h-11 rounded-lg flex items-center justify-center gap-2 text-sm font-semibold text-white bg-accent hover:bg-accent-hover disabled:opacity-60 transition-colors"
            >
              {saving && <Loader2 size={16} className="animate-spin" />}
              {saving ? 'Saving...' : 'Apply'}
            </button>

            {saveError && (
              <div className="px-4 py-2.5 rounded-lg text-sm text-red-400 bg-red-950/40 border border-red-800/40 animate-fade-up">
                {saveError}
              </div>
            )}

            {showSuccess && (
              <div className="px-4 py-2.5 rounded-lg flex items-center gap-2 bg-success-dark border border-success/30 animate-fade-up">
                <div className="w-5 h-5 rounded-full flex items-center justify-center bg-success shrink-0">
                  <Check size={12} color="white" />
                </div>
                <span className="text-sm text-primary">
                  Switched to <strong className="text-success">{model}</strong>
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
