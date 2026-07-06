import { DOCUMENT } from '@angular/common';
import { inject, InjectionToken } from '@angular/core';

/**
 * Base URL of the hosted API. An empty value keeps same-origin /api requests,
 * which is correct for the local Angular proxy and Docker Nginx proxy.
 */
export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL', {
  providedIn: 'root',
  factory: () => {
    const document = inject(DOCUMENT);
    const configuredUrl = document
      .querySelector<HTMLMetaElement>('meta[name="api-base-url"]')
      ?.content.trim();

    return (configuredUrl ?? '').replace(/\/+$/, '');
  },
});
