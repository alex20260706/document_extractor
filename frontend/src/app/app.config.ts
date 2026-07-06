import { provideHttpClient } from '@angular/common/http';
import { ApplicationConfig } from '@angular/core';

/** Root providers used to bootstrap the standalone Angular application. */
export const appConfig: ApplicationConfig = {
  providers: [provideHttpClient()],
};
