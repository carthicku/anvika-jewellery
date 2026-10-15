/**
 * Razorpay Checkout.js loader. The pop-up collects card/UPI/netbanking details on Razorpay's own
 * pages — our site never sees them. Its "success" callback is only a hint: the backend verifies
 * the signature and fetches the payment from Razorpay before an order is marked paid.
 */
const SCRIPT_URL = 'https://checkout.razorpay.com/v1/checkout.js';

export interface PaymentSession {
  provider: 'razorpay' | 'simulator';
  key_id: string;
  provider_order_id: string;
  amount_paise: number;
  currency: string;
  store_name: string;
  description: string;
  prefill: { name: string; email: string; contact: string };
}

export interface PaymentSuccess {
  provider_order_id: string;
  provider_payment_id: string;
  signature: string;
}

interface RazorpayResponse {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

interface RazorpayFailure {
  error?: { description?: string; metadata?: { payment_id?: string; order_id?: string } };
}

interface RazorpayInstance {
  open: () => void;
  on: (event: 'payment.failed', handler: (response: RazorpayFailure) => void) => void;
}

type RazorpayConstructor = new (options: Record<string, unknown>) => RazorpayInstance;

declare global {
  interface Window {
    Razorpay?: RazorpayConstructor;
  }
}

let loading: Promise<RazorpayConstructor> | null = null;

export function loadRazorpay(): Promise<RazorpayConstructor> {
  if (window.Razorpay) return Promise.resolve(window.Razorpay);
  loading ??= new Promise<RazorpayConstructor>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = SCRIPT_URL;
    script.async = true;
    script.onload = () => {
      if (window.Razorpay) resolve(window.Razorpay);
      else reject(new Error('Razorpay did not load'));
    };
    script.onerror = () => {
      loading = null;
      script.remove();
      reject(new Error('Razorpay did not load'));
    };
    document.head.appendChild(script);
  });
  return loading;
}

export async function openRazorpay(
  session: PaymentSession,
  handlers: {
    onSuccess: (result: PaymentSuccess) => void;
    onFailure: (paymentId: string | null, description: string | null) => void;
    onDismiss: () => void;
  },
): Promise<void> {
  const Razorpay = await loadRazorpay();
  const instance = new Razorpay({
    key: session.key_id,
    amount: session.amount_paise,
    currency: session.currency,
    name: session.store_name,
    description: session.description,
    order_id: session.provider_order_id,
    prefill: session.prefill,
    theme: { color: '#1F1D1A' },
    handler: (response: RazorpayResponse) => {
      handlers.onSuccess({
        provider_order_id: response.razorpay_order_id,
        provider_payment_id: response.razorpay_payment_id,
        signature: response.razorpay_signature,
      });
    },
    modal: { ondismiss: handlers.onDismiss, confirm_close: true },
  });
  instance.on('payment.failed', (response) => {
    handlers.onFailure(
      response.error?.metadata?.payment_id ?? null,
      response.error?.description ?? null,
    );
  });
  instance.open();
}
