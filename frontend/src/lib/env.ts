/** Public, build-time configuration (never secrets — see docs/development/ENVIRONMENT_VARIABLES.md). */
export const env = {
  storeName: import.meta.env.VITE_STORE_NAME ?? 'Anvika',
  siteUrl: (import.meta.env.VITE_SITE_URL ?? window.location.origin).replace(/\/$/, ''),
  isDev: import.meta.env.DEV,
};
