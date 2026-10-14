import { CheckCircle2, Info, X, XCircle } from 'lucide-react';
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import { cn } from '@/lib/cn';

type ToastTone = 'success' | 'info' | 'error';

interface Toast {
  id: number;
  tone: ToastTone;
  message: string;
}

interface ToastApi {
  notify: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const icons = { success: CheckCircle2, info: Info, error: XCircle };

/**
 * Lightweight toasts announced through a polite live region (errors use an assertive region).
 * Toasts never carry essential information that isn't also shown on the page.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const notify = useCallback(
    (message: string, tone: ToastTone = 'success') => {
      const id = nextId.current++;
      setToasts((current) => [...current.slice(-2), { id, tone, message }]);
      window.setTimeout(() => {
        dismiss(id);
      }, 5000);
    },
    [dismiss],
  );

  const api = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-4 z-[60] flex flex-col items-center gap-2 px-4 sm:right-4 sm:left-auto sm:items-end">
        <div aria-live="polite" className="contents">
          {toasts
            .filter((t) => t.tone !== 'error')
            .map((t) => (
              <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
            ))}
        </div>
        <div aria-live="assertive" className="contents">
          {toasts
            .filter((t) => t.tone === 'error')
            .map((t) => (
              <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
            ))}
        </div>
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
  const Icon = icons[toast.tone];
  return (
    <div
      className={cn(
        'pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-md bg-noir px-4 py-3 text-sm text-noir-ink shadow-lift',
      )}
    >
      <Icon
        className={cn(
          'mt-0.5 size-4 shrink-0',
          toast.tone === 'error' ? 'text-danger-on-dark' : 'text-gold',
        )}
        aria-hidden="true"
      />
      <p className="flex-1">{toast.message}</p>
      <button
        type="button"
        onClick={() => {
          onDismiss(toast.id);
        }}
        className="-m-1 rounded-sm p-1 text-noir-muted hover:text-noir-ink"
        aria-label="Dismiss notification"
      >
        <X className="size-4" aria-hidden="true" />
      </button>
    </div>
  );
}

export function useToast(): ToastApi {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used inside <ToastProvider>');
  return context;
}
