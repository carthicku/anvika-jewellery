import { FlaskConical } from 'lucide-react';
import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router';

import {
  useReportPaymentFailure,
  useRetryPayment,
  useSimulatorPay,
  useVerifyPayment,
} from '@/api/queries/orders';
import { Button } from '@/components/ui/Button';
import { DialogContent, DialogRoot } from '@/components/ui/Dialog';
import { formatMoney } from '@/lib/format';
import { errorMessage } from '@/lib/forms';
import { openRazorpay, type PaymentSession, type PaymentSuccess } from '@/lib/razorpay';

type Phase = 'idle' | 'opening' | 'verifying' | 'failed';

/**
 * Opens the payment pop-up (Razorpay, or the development simulator) for an order and hands the
 * result to the backend. Only the backend decides whether the order is paid.
 */
export function usePaymentFlow(reference: string | null, grandTotal: string | null) {
  const navigate = useNavigate();
  const verify = useVerifyPayment();
  const reportFailure = useReportPaymentFailure();
  const retry = useRetryPayment();
  const simulatorPay = useSimulatorPay();
  const [phase, setPhase] = useState<Phase>('idle');
  const [message, setMessage] = useState<string | null>(null);
  const [simulated, setSimulated] = useState<{ session: PaymentSession; ref: string } | null>(null);

  const finish = useCallback(
    (ref: string, result: PaymentSuccess) => {
      setPhase('verifying');
      verify.mutate(
        { reference: ref, ...result },
        {
          onSuccess: (data) => {
            if (data.outcome === 'failed') {
              setPhase('failed');
              setMessage(data.message);
              return;
            }
            setPhase('idle');
            void navigate(`/order-confirmation/${ref}`);
          },
          onError: (error) => {
            setPhase('failed');
            setMessage(errorMessage(error));
          },
        },
      );
    },
    [navigate, verify],
  );

  const failed = useCallback(
    (
      ref: string,
      session: PaymentSession,
      paymentId: string | null,
      description: string | null,
    ) => {
      setPhase('failed');
      setMessage(description ?? 'The payment didn’t go through. You can try again.');
      reportFailure.mutate({
        reference: ref,
        provider_order_id: session.provider_order_id,
        provider_payment_id: paymentId,
      });
    },
    [reportFailure],
  );

  const start = useCallback(
    (session: PaymentSession, ref = reference) => {
      if (!ref) return;
      setMessage(null);
      if (session.provider === 'simulator') {
        setSimulated({ session, ref });
        return;
      }
      setPhase('opening');
      openRazorpay(session, {
        onSuccess: (result) => {
          finish(ref, result);
        },
        onFailure: (paymentId, description) => {
          failed(ref, session, paymentId, description);
        },
        onDismiss: () => {
          setPhase('idle');
          setMessage(
            'Payment window closed. Your pieces stay reserved until the payment time runs out.',
          );
        },
      }).catch(() => {
        setPhase('failed');
        setMessage('We couldn’t open the payment window. Check your connection and try again.');
      });
    },
    [failed, finish, reference],
  );

  /** A new payment for the same order (after a failure, or when the provider was down). */
  const payAgain = useCallback(
    (ref = reference) => {
      if (!ref) return;
      setMessage(null);
      retry.mutate(ref, {
        onSuccess: (data) => {
          start(data.payment, ref);
        },
        onError: (error) => {
          setPhase('failed');
          setMessage(errorMessage(error));
        },
      });
    },
    [reference, retry, start],
  );

  const simulatedDialog = (
    <DialogRoot
      open={simulated !== null}
      onOpenChange={(open) => {
        if (!open) {
          setSimulated(null);
          setMessage(
            'Payment window closed. Your pieces stay reserved until the payment time runs out.',
          );
        }
      }}
    >
      <DialogContent
        title="Simulated payment"
        description="Development mode — no money moves. This window stands in for the Razorpay payment pop-up."
      >
        <div className="space-y-5">
          <p className="flex items-start gap-3 rounded-sm border border-warning/30 bg-warning-soft p-3 text-sm text-warning">
            <FlaskConical className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            The store is running with the payment simulator. Real customers never see this window.
          </p>
          {grandTotal && (
            <p className="text-sm">
              Amount: <span className="tabular font-medium">{formatMoney(grandTotal)}</span>
            </p>
          )}
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button
              loading={simulatorPay.isPending || verify.isPending}
              onClick={() => {
                if (!simulated) return;
                const { session, ref } = simulated;
                simulatorPay.mutate(
                  {
                    reference: ref,
                    provider_order_id: session.provider_order_id,
                    outcome: 'success',
                  },
                  {
                    onSuccess: (result) => {
                      setSimulated(null);
                      finish(ref, {
                        provider_order_id: result.provider_order_id,
                        provider_payment_id: result.provider_payment_id,
                        signature: result.signature ?? '',
                      });
                    },
                  },
                );
              }}
            >
              Pay (simulated)
            </Button>
            <Button
              variant="secondary"
              disabled={simulatorPay.isPending}
              onClick={() => {
                if (!simulated) return;
                const { session, ref } = simulated;
                simulatorPay.mutate(
                  {
                    reference: ref,
                    provider_order_id: session.provider_order_id,
                    outcome: 'failure',
                  },
                  {
                    onSuccess: (result) => {
                      setSimulated(null);
                      failed(
                        ref,
                        session,
                        result.provider_payment_id,
                        'The simulated payment was declined.',
                      );
                    },
                  },
                );
              }}
            >
              Simulate a failed payment
            </Button>
          </div>
          {simulatorPay.isError && (
            <p className="text-sm text-danger" role="alert">
              {errorMessage(simulatorPay.error)}
            </p>
          )}
        </div>
      </DialogContent>
    </DialogRoot>
  );

  return {
    start,
    payAgain,
    phase,
    message,
    busy: phase === 'opening' || phase === 'verifying' || retry.isPending,
    verifying: phase === 'verifying',
    simulatedDialog,
  };
}
