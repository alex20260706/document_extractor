import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';

import { InvoiceExtractionResponse } from '../models/invoice-extraction.models';
import { InvoiceResultComponent } from './invoice-result.component';

describe('InvoiceResultComponent', () => {
  it('keeps field order and renders null and boolean values clearly', async () => {
    await TestBed.configureTestingModule({ imports: [InvoiceResultComponent] }).compileComponents();
    const fixture = TestBed.createComponent(InvoiceResultComponent);
    const response: InvoiceExtractionResponse = {
      status: 'partial',
      document_type: 'invoice',
      acquisition_method: 'ocr',
      extraction_method: 'hybrid',
      fields: {
        second_field: { label: 'Second', value: true, confidence: 0.9, missing: false, extraction_method: 'llm' },
        first_field: { label: 'First', value: null, confidence: 0, missing: true, extraction_method: null },
      },
      line_items: [{ description: 'Service', quantity: null, unit_price: null, line_total: null, confidence: 0.8, extraction_method: 'rule_based' }],
      warnings: [],
      errors: [],
    };
    fixture.componentRef.setInput('result', response);
    fixture.detectChanges();

    const element = fixture.nativeElement as HTMLElement;
    const labels = [...element.querySelectorAll('.field-label')].map((item) => item.textContent?.trim());
    expect(labels).toEqual(['Second', 'First']);
    expect(element.textContent).toContain('Yes');
    expect(element.textContent).toContain('Not found');
    expect(element.querySelector('caption')?.textContent).toContain('Extracted invoice line items');
    expect([...element.querySelectorAll('tbody td')].filter((cell) => cell.textContent?.trim() === '-')).toHaveLength(3);
  });
});
