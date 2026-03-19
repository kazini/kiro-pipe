/**
 * lib/awsq-adapter/errors.ts
 *
 * Typed errors thrown by the awsq-adapter library.
 * Callers (AWSQAdapter) catch these and convert to appropriate responses.
 */

export class TranslationError extends Error {
  constructor(
    message: string,
    public readonly context?: Record<string, unknown>,
    public override readonly cause?: unknown,
  ) {
    super(message)
    this.name = 'TranslationError'
  }
}

export class EncodingError extends Error {
  constructor(
    message: string,
    public readonly context?: Record<string, unknown>,
    public override readonly cause?: unknown,
  ) {
    super(message)
    this.name = 'EncodingError'
  }
}
