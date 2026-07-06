import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from '../../../core/config/api-base-url';
import { SupportedDocumentType } from '../../../core/models/document-extraction.models';
import { ExtractionResponse } from '../models/extraction-response.models';

/** Sends document-extraction requests to the configured API origin. */
@Injectable({ providedIn: 'root' })
export class ExtractionApiService {
  private readonly http = inject(HttpClient);
  private readonly apiBaseUrl = inject(API_BASE_URL);

  /**
   * Uploads one document with its explicitly selected type.
   *
   * @param file - PDF or image selected by the user.
   * @param documentType - Enabled extraction strategy.
   * @returns The observable document-specific extraction response.
   */
  extract(file: File, documentType: SupportedDocumentType): Observable<ExtractionResponse> {
    const body = new FormData();
    body.append('file', file);
    body.append('document_type', documentType);
    return this.http.post<ExtractionResponse>(`${this.apiBaseUrl}/api/extractions`, body);
  }
}
