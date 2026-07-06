import { DecimalPipe, PercentPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import {
  ContentAcquisitionMethod,
  DataExtractionMethod,
  ExtractedField,
} from '../../../core/models/document-extraction.models';
import { PurchaseOrderExtractionResponse } from '../models/purchase-order-extraction.models';

/** Presents purchase-order fields, line items and processing metadata. */
@Component({
  selector: 'app-purchase-order-result',
  imports: [DecimalPipe, PercentPipe],
  templateUrl: './purchase-order-result.component.html',
  styleUrl: './purchase-order-result.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PurchaseOrderResultComponent {
  readonly result = input.required<PurchaseOrderExtractionResponse>();
  readonly fieldEntries = computed(() => Object.entries(this.result().fields));

  /**
   * Converts an extracted field to a user-facing value.
   *
   * @param field - Field returned by the extraction API.
   * @returns A displayable value with explicit missing and boolean labels.
   */
  displayFieldValue(field: ExtractedField): string | number {
    if (field.missing || field.value === null) return 'Not found';
    if (typeof field.value === 'boolean') return field.value ? 'Yes' : 'No';
    return field.value;
  }

  /**
   * Converts an extraction status to its user-facing label.
   *
   * @param status - Purchase-order extraction status.
   * @returns The corresponding English label.
   */
  statusLabel(status: PurchaseOrderExtractionResponse['status']): string {
    return { completed: 'Completed', partial: 'Review needed', failed: 'Failed' }[status];
  }

  /**
   * Converts an acquisition or extraction method to a readable label.
   *
   * @param method - Method reported by the extraction API.
   * @returns The corresponding English label.
   */
  methodLabel(method: ContentAcquisitionMethod | DataExtractionMethod | null): string {
    if (method === null) return 'Not available';
    return {
      embedded_text: 'Embedded text', ocr: 'OCR', rule_based: 'Rules',
      llm: 'AI enrichment', hybrid: 'Hybrid',
    }[method];
  }
}
