import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';

import { API_BASE_URL } from '../../../core/config/api-base-url';
import { ExtractionApiService } from './extraction-api.service';

describe('ExtractionApiService', () => {
  it('uses the configured hosted API base URL', () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: API_BASE_URL, useValue: 'https://api.example.test' },
      ],
    });
    const service = TestBed.inject(ExtractionApiService);
    const http = TestBed.inject(HttpTestingController);

    service
      .extract(new File(['pdf'], 'invoice.pdf', { type: 'application/pdf' }), 'invoice')
      .subscribe();

    const request = http.expectOne('https://api.example.test/api/extractions');
    expect(request.request.method).toBe('POST');
    request.flush({});
    http.verify();
  });
});
