import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { InvoiceResultComponent } from '../../invoice/invoice-result/invoice-result.component';
import { PurchaseOrderResultComponent } from '../../purchase-order/purchase-order-result/purchase-order-result.component';
import { ExtractionResponse } from '../models/extraction-response.models';

/** Selects a document-specific result without coupling the app shell to it. */
@Component({
  selector: 'app-extraction-result',
  imports: [InvoiceResultComponent, PurchaseOrderResultComponent],
  templateUrl: './extraction-result.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExtractionResultComponent {
  readonly result = input.required<ExtractionResponse>();
  readonly invoiceResult = computed(() => {
    const result = this.result();
    return result.document_type === 'invoice' ? result : null;
  });
  readonly purchaseOrderResult = computed(() => {
    const result = this.result();
    return result.document_type === 'purchase_order' ? result : null;
  });
}
