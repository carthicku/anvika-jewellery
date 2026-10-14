import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterEach } from 'vitest';

// Routes are lazy-loaded (code splitting); allow time for the dynamic import under a busy run.
configure({ asyncUtilTimeout: 3000 });

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  document.cookie.split('; ').forEach((cookie) => {
    const name = cookie.split('=')[0];
    if (name) document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
  });
});
