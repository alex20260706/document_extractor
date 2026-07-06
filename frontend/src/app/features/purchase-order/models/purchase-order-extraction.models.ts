import {
  DataExtractionMethod,
  ExtractionResponseBase,
} from '../../../core/models/document-extraction.models';

/** One purchase-order row returned by the API. */
export interface PurchaseOrderLine {
  description: string;
  sku: string | null;
  quantity: number | null;
  unit_price: number | null;
  line_total: number | null;
  confidence: number;
  extraction_method: DataExtractionMethod | null;
}

/** Complete API response for a purchase-order extraction. */
export interface PurchaseOrderExtractionResponse
  extends ExtractionResponseBase<'purchase_order'> {
  line_items: PurchaseOrderLine[];
}
