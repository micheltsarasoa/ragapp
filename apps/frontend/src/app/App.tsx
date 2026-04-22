import { LeftSidebar } from './components/LeftSidebar';
import { CenterPanel } from './components/CenterPanel';
import { RightPanel } from './components/RightPanel';
import { useIdentity } from '../hooks/useIdentity';
import { useDocuments } from '../hooks/useDocuments';

export default function App() {
  const { identity } = useIdentity();
  const docs = useDocuments(identity?.user_id ?? null);

  return (
    <div
      className="flex w-screen h-screen overflow-hidden"
      style={{ background: 'var(--background)' }}
    >
      <LeftSidebar
        documents={docs.documents}
        docsLoading={docs.loading}
      />
      <div style={{ width: '1px', background: 'var(--border-subtle)' }} />
      <CenterPanel
        documents={docs.documents}
        loading={docs.loading}
        error={docs.error}
        reload={docs.reload}
        updateVisibility={docs.updateVisibility}
        deleteDocument={docs.deleteDocument}
      />
      <div style={{ width: '1px', background: 'var(--border-subtle)' }} />
      <RightPanel />
    </div>
  );
}
