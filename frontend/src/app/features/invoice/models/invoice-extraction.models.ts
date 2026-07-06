import {
  DataExtractionMethod,
  ExtractionResponseBase,
} from '../../../core/models/document-extraction.models';

/** One invoice product or service row returned by the API. */
export interface InvoiceLine {
  description: string;
  quantity: number | null;
  unit_price: number | null;
  line_total: number | null;
  confidence: number;
  extraction_method: DataExtractionMethod | null;
}

/** Complete API response for an invoice extraction. */
export interface InvoiceExtractionResponse extends ExtractionResponseBase<'invoice'> {
  line_items: InvoiceLine[];
}
