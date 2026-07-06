/** Inject the hosted API origin into the compiled Angular entry point. */

import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const apiBaseUrl = (process.env['PUBLIC_API_BASE_URL'] ?? '').trim().replace(/\/+$/, '');

if (apiBaseUrl) {
  const parsedUrl = new URL(apiBaseUrl);
  if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
    throw new Error('PUBLIC_API_BASE_URL must use http or https.');
  }
}

/**
 * Escapes a value before inserting it into an HTML attribute.
 *
 * @param {string} value - Untrusted configuration value.
 * @returns {string} The HTML-safe attribute value.
 */
const escapeHtmlAttribute = (value) =>
  value
    .replaceAll('&', '&amp;')
    .replaceAll('"', '&quot;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');

const indexPath = resolve('dist/zebra-document-extractor-web/browser/index.html');
const indexHtml = await readFile(indexPath, 'utf8');
const apiMetaTag = /<meta name="api-base-url" content(?:="[^"]*")?>/;

// Fail the build instead of silently shipping an unusable hosted API URL.
if (!apiMetaTag.test(indexHtml)) {
  throw new Error('The api-base-url meta tag was not found in the Angular output.');
}

const configuredHtml = indexHtml.replace(
  apiMetaTag,
  `<meta name="api-base-url" content="${escapeHtmlAttribute(apiBaseUrl)}">`,
);

await writeFile(indexPath, configuredHtml, 'utf8');
