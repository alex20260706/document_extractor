import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { ExtractionResponse } from '../features/extraction/models/extraction-response.models';
import { AppComponent } from './app.component';

const RESPONSE: ExtractionResponse = {
  status: 'completed',
  document_type: 'invoice',
  acquisition_method: 'embedded_text',
  extraction_method: 'rule_based',
  fields: {},
  line_items: [],
  warnings: [],
  errors: [],
};

describe('AppComponent', () => {
  let fixture: ComponentFixture<AppComponent>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(AppComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('creates the application', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('requires a document type before enabling file selection', () => {
    const element = fixture.nativeElement as HTMLElement;
    const select = element.querySelector<HTMLSelectElement>('#document-type')!;
    const input = element.querySelector<HTMLInputElement>('input[type="file"]')!;

    expect(input.disabled).toBe(true);

    select.value = 'invoice';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    expect(input.disabled).toBe(false);
  });

  it('rejects unsupported files without calling the API', () => {
    fixture.componentInstance.extract({
      file: new File(['plain text'], 'notes.txt', { type: 'text/plain' }),
      documentType: 'invoice',
    });

    expect(fixture.componentInstance.error()).toBe('Select a supported PDF or image.');
    http.expectNone('/api/extractions');
  });

  it('uploads multipart data and renders the successful response', () => {
    const file = new File(['pdf'], 'invoice.pdf', { type: 'application/pdf' });

    fixture.componentInstance.extract({ file, documentType: 'invoice' });

    expect(fixture.componentInstance.loading()).toBe(true);
    expect(fixture.componentInstance.workflowStep()).toBe(2);
    const request = http.expectOne('/api/extractions');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toBeInstanceOf(FormData);
    expect((request.request.body as FormData).get('file')).toBe(file);
    expect((request.request.body as FormData).get('document_type')).toBe('invoice');

    request.flush(RESPONSE);

    expect(fixture.componentInstance.loading()).toBe(false);
    expect(fixture.componentInstance.result()).toEqual(RESPONSE);
    expect(fixture.componentInstance.workflowStep()).toBe(3);
  });

  it('ignores another extraction while one is running', () => {
    const first = new File(['first'], 'first.pdf', { type: 'application/pdf' });
    const second = new File(['second'], 'second.pdf', { type: 'application/pdf' });

    fixture.componentInstance.extract({ file: first, documentType: 'invoice' });
    fixture.componentInstance.extract({ file: second, documentType: 'invoice' });

    const requests = http.match('/api/extractions');
    expect(requests).toHaveLength(1);
    expect((requests[0].request.body as FormData).get('file')).toBe(first);
    requests[0].flush(RESPONSE);
  });

  it('shows the API error message and leaves the loading state', () => {
    const file = new File(['pdf'], 'invoice.pdf', { type: 'application/pdf' });
    fixture.componentInstance.extract({ file, documentType: 'invoice' });

    http.expectOne('/api/extractions').flush(
      { detail: { code: 'unsupported_file', message: 'The file is not valid.' } },
      { status: 415, statusText: 'Unsupported Media Type' },
    );

    expect(fixture.componentInstance.loading()).toBe(false);
    expect(fixture.componentInstance.error()).toBe('The file is not valid.');
  });

  it('shows the correlation reference for an unexpected API error', () => {
    const file = new File(['pdf'], 'invoice.pdf', { type: 'application/pdf' });
    fixture.componentInstance.extract({ file, documentType: 'invoice' });

    http.expectOne('/api/extractions').flush(
      {
        detail: {
          code: 'internal_error',
          message: 'An unexpected error occurred.',
          correlation_id: 'error-reference',
        },
      },
      { status: 500, statusText: 'Internal Server Error' },
    );

    expect(fixture.componentInstance.error()).toBe(
      'An unexpected error occurred. Reference: error-reference',
    );
  });
});
