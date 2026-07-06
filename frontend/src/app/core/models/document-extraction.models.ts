/** Overall outcome reported by the extraction API. */
export type ExtractionStatus = 'completed' | 'partial' | 'failed';

/** Method used to obtain readable text from a document. */
export type ContentAcquisitionMethod = 'embedded_text' | 'ocr';

/** Method used to convert document text into structured data. */
export type DataExtractionMethod = 'rule_based' | 'llm' | 'hybrid';

/** Document types currently enabled by the product. */
export const SUPPORTED_DOCUMENT_TYPES = ['invoice', 'purchase_order'] as const;

/** Document type accepted by the extraction workflow. */
export type SupportedDocumentType = (typeof SUPPORTED_DOCUMENT_TYPES)[number];

/**
 * Checks whether an arbitrary string is an enabled document type.
 *
 * @param value - Candidate document type.
 * @returns Whether the value is a supported document type.
 */
export function isSupportedDocumentType(value: string): value is SupportedDocumentType {
  return SUPPORTED_DOCUMENT_TYPES.some((documentType) => documentType === value);
}

/** File and document type submitted for extraction. */
export interface DocumentUpload {
  file: File;
  documentType: SupportedDocumentType;
}

/** Generic field returned by a document extraction. */
export interface ExtractedField {
  label: string;
  value: string | number | boolean | null;
  confidence: number;
  missing: boolean;
  extraction_method: DataExtractionMethod | null;
}

/** Controlled processing error returned by the API. */
export interface ProcessingError {
  code: string;
  message: string;
}

/** Fields shared by every document-specific extraction response. */
export interface ExtractionResponseBase<TDocumentType extends SupportedDocumentType> {
  status: ExtractionStatus;
  document_type: TDocumentType;
  acquisition_method: ContentAcquisitionMethod | null;
  extraction_method: DataExtractionMethod | null;
  fields: Record<string, ExtractedField>;
  warnings: string[];
  errors: ProcessingError[];
}

/** Error envelope returned for rejected API requests. */
export interface ApiError {
  detail?: { code?: string; message?: string; correlation_id?: string };
}
