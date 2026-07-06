import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';

import { ApiError, DocumentUpload } from '../core/models/document-extraction.models';
import { ExtractionApiService } from '../features/extraction/data-access/extraction-api.service';
import { ExtractionResultComponent } from '../features/extraction/extraction-result/extraction-result.component';
import { ExtractionResponse } from '../features/extraction/models/extraction-response.models';
import { UploadPanelComponent } from '../features/upload/upload-panel/upload-panel.component';

/** Coordinates document upload, extraction state and result rendering. */
@Component({
  selector: 'app-root',
  imports: [UploadPanelComponent, ExtractionResultComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent {
  private readonly api = inject(ExtractionApiService);
  readonly loading = signal(false);
  readonly filename = signal('');
  readonly result = signal<ExtractionResponse | null>(null);
  readonly error = signal<string | null>(null);
  readonly workflowStep = signal<1 | 2 | 3>(1);

  /**
   * Validates and submits a document selected by the user.
   *
   * @param upload - File and explicitly selected document type.
   */
  extract(upload: DocumentUpload): void {
    if (this.loading()) return;

    const { file, documentType } = upload;
    this.result.set(null);
    this.error.set(null);
    // Mirror server limits for immediate feedback; the API remains authoritative.
    const supportedTypes = new Set([
      'application/pdf', 'image/bmp', 'image/jpeg', 'image/png', 'image/tiff', 'image/webp',
    ]);
    if (!supportedTypes.has(file.type)) {
      this.workflowStep.set(1);
      this.error.set('Select a supported PDF or image.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      this.workflowStep.set(1);
      this.error.set('The file exceeds the 10 MB limit.');
      return;
    }

    this.filename.set(file.name);
    this.workflowStep.set(2);
    this.loading.set(true);
    this.api.extract(file, documentType).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (response) => {
        this.result.set(response);
        this.workflowStep.set(3);
      },
      error: (response: HttpErrorResponse) => {
        const payload = response.error as ApiError | null;
        const message = payload?.detail?.message;
        const correlationId = payload?.detail?.correlation_id;
        const userMessage =
          typeof message === 'string'
            ? message
            : 'The service is unavailable. Please try again.';
        this.error.set(
          correlationId ? `${userMessage} Reference: ${correlationId}` : userMessage,
        );
      },
    });
  }
}
