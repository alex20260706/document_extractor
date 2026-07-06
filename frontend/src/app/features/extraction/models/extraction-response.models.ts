import { InvoiceExtractionResponse } from '../../invoice/models/invoice-extraction.models';
import { PurchaseOrderExtractionResponse } from '../../purchase-order/models/purchase-order-extraction.models';

/** Add each future document response to this discriminated union. */
export type ExtractionResponse = InvoiceExtractionResponse | PurchaseOrderExtractionResponse;
