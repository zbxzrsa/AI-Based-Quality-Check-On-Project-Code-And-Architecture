declare module 'msw' {
  export function setupServer(...handlers: unknown[]): unknown;
  export const rest: Record<string, unknown>;
}
