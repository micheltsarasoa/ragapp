import { createRoot } from 'react-dom/client';
import App from './app/App.tsx';
import { IdentityProvider } from './context/IdentityContext.tsx';
import './styles/index.css';

createRoot(document.getElementById('root')!).render(
  <IdentityProvider>
    <App />
  </IdentityProvider>
);
