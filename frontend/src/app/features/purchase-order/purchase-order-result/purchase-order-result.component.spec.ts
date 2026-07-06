import { TestBed } from '@angular/core/testing';
import { describe, expect, it } from 'vitest';

import { PurchaseOrderExtractionResponse } from '../models/purchase-order-extraction.models';
import { PurchaseOrderResultComponent } from './purchase-order-result.component';

describe('PurchaseOrderResultComponent', () => {
  it('renders order fields and SKU line items', async () => {
    await TestBed.configureTestingModule({ imports: [PurchaseOrderResultComponent] }).compileComponents();
    const fixture = TestBed.createComponent(PurchaseOrderResultComponent);
    const response: PurchaseOrderExtractionResponse = {
      status: 'completed', document_type: 'purchase_order',
      acquisition_method: 'embedded_text', extraction_method: 'rule_based',
      fields: {
        order_number: { label: 'Purchase order number', value: 'PO-42', confidence: 0.94, missing: false, extraction_method: 'rule_based' },
      },
      line_items: [{ description: 'Monitor', sku: 'MON-27', quantity: 2, unit_price: 250, line_total: 500, confidence: 0.86, extraction_method: 'rule_based' }],
      warnings: [], errors: [],
    };
    fixture.componentRef.setInput('result', response);
    fixture.detectChanges();

    const element = fixture.nativeElement as HTMLElement;
    expect(element.textContent).toContain('Purchase order data');
    expect(element.textContent).toContain('PO-42');
    expect(element.textContent).toContain('MON-27');
    expect(element.querySelector('caption')?.textContent).toContain('purchase order line items');
  });
});
