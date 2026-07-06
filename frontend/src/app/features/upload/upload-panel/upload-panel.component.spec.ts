import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';

import { DocumentUpload } from '../../../core/models/document-extraction.models';
import { UploadPanelComponent } from './upload-panel.component';

describe('UploadPanelComponent', () => {
  it('emits a selected file and clears the native input for retries', async () => {
    await TestBed.configureTestingModule({ imports: [UploadPanelComponent] }).compileComponents();
    const fixture = TestBed.createComponent(UploadPanelComponent);
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;
    const select = element.querySelector<HTMLSelectElement>('#document-type')!;
    const input = element.querySelector<HTMLInputElement>('input[type="file"]')!;
    const file = new File(['pdf'], 'invoice.pdf', { type: 'application/pdf' });
    let emitted: DocumentUpload | undefined;
    fixture.componentInstance.extractionRequested.subscribe((upload) => (emitted = upload));

    select.value = 'invoice';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    Object.defineProperty(input, 'files', { value: { item: () => file }, configurable: true });
    input.dispatchEvent(new Event('change'));

    expect(emitted).toEqual({ file, documentType: 'invoice' });
    expect(input.value).toBe('');
  });
});
