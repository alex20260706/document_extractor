import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';

import {
  DocumentUpload,
  isSupportedDocumentType,
  SupportedDocumentType,
} from '../../../core/models/document-extraction.models';

/** Collects the document type and file before requesting extraction. */
@Component({
  selector: 'app-upload-panel',
  templateUrl: './upload-panel.component.html',
  styleUrl: './upload-panel.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadPanelComponent {
  readonly busy = input(false);
  readonly extractionRequested = output<DocumentUpload>();
  readonly dragging = signal(false);
  readonly selectedDocumentType = signal<SupportedDocumentType | null>(null);
  readonly uploadDisabled = computed(() => !this.selectedDocumentType() || this.busy());
  readonly dropTitle = computed(() => {
    if (this.busy()) return 'Processing your document';
    return this.selectedDocumentType()
      ? 'Drop your document here'
      : 'Select a document type first';
  });

  /**
   * Updates the selected document type from the native select control.
   *
   * @param event - Change event emitted by the document type selector.
   */
  onDocumentTypeChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.selectedDocumentType.set(isSupportedDocumentType(value) ? value : null);
  }

  /**
   * Enables drag feedback while the panel can accept an upload.
   *
   * @param event - Current browser drag event.
   */
  onDragOver(event: DragEvent): void {
    event.preventDefault();
    if (this.uploadDisabled()) return;
    this.dragging.set(true);
  }

  /**
   * Requests extraction for the first file dropped on the panel.
   *
   * @param event - Drop event containing the transferred files.
   */
  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragging.set(false);
    const file = event.dataTransfer?.files.item(0);
    if (file) this.emitRequest(file);
  }

  /**
   * Requests extraction for the file chosen with the file input.
   *
   * @param event - Change event emitted by the file input.
   */
  onFileInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.item(0);
    // Allow selecting the same file again after the input emits a change.
    input.value = '';
    if (file) this.emitRequest(file);
  }

  private emitRequest(file: File): void {
    const documentType = this.selectedDocumentType();
    if (documentType && !this.busy()) {
      this.extractionRequested.emit({ file, documentType });
    }
  }
}
