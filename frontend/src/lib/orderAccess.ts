/**
 * Guest order access tokens.
 *
 * A guest can view (and pay for / cancel) their order with a private token returned by checkout
 * and included in the confirmation email link (`/order-confirmation/REF#token=…` — the fragment is
 * never sent to servers or logged). We keep it in sessionStorage only for this tab, so a refresh of
 * the confirmation page still works. It grants access to ONE order, not to an account.
 */
const PREFIX = 'anvika:order-access:';

export function saveOrderToken(reference: string, token: string): void {
  try {
    window.sessionStorage.setItem(PREFIX + reference, token);
  } catch {
    /* storage unavailable: the page still works until it is closed */
  }
}

export function readOrderToken(reference: string): string | null {
  try {
    return window.sessionStorage.getItem(PREFIX + reference);
  } catch {
    return null;
  }
}

/** Read `#token=…` from the email link, remember it, and remove it from the address bar. */
export function captureTokenFromHash(reference: string): void {
  const match = /(?:^#|&)token=([A-Za-z0-9_-]{20,100})/.exec(window.location.hash);
  if (!match?.[1]) return;
  saveOrderToken(reference, match[1]);
  window.history.replaceState(
    window.history.state,
    '',
    window.location.pathname + window.location.search,
  );
}

export function orderTokenHeaders(reference: string): Record<string, string> {
  const token = readOrderToken(reference);
  return token ? { 'X-Order-Access-Token': token } : {};
}
