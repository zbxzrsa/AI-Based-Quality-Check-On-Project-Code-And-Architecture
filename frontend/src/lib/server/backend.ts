export class BackendFetchError extends Error {
  attempted: string[];
  details: string[];

  constructor(message: string, attempted: string[], details: string[]) {
    super(message);
    this.name = 'BackendFetchError';
    this.attempted = attempted;
    this.details = details;
  }
}

const DEFAULT_BACKEND_CANDIDATES = ['http://localhost:8000', 'http://backend:8000'];

function normalizeBaseUrl(url: string): string {
  return url.trim().replace(/\/+$/, '');
}

export function getBackendBaseCandidates(): string[] {
  const rawCandidates = [
    process.env.BACKEND_URL,
    process.env.NEXT_PUBLIC_BACKEND_URL,
    process.env.NEXT_PUBLIC_API_BASE_URL,
    ...DEFAULT_BACKEND_CANDIDATES,
  ].filter((value): value is string => typeof value === 'string' && value.trim().length > 0);

  const candidates: string[] = [];
  const seen = new Set<string>();

  for (const raw of rawCandidates) {
    const normalized = normalizeBaseUrl(raw);
    if (!seen.has(normalized)) {
      candidates.push(normalized);
      seen.add(normalized);
    }

    // Works in container, but may fail when Next.js runs on host machine.
    if (normalized.includes('host.docker.internal')) {
      const localhostFallback = normalized.replace('host.docker.internal', 'localhost');
      if (!seen.has(localhostFallback)) {
        candidates.push(localhostFallback);
        seen.add(localhostFallback);
      }
    }
  }

  return candidates;
}

type BackendFetchResult = {
  response: Response;
  backendUrl: string;
};

export async function fetchBackendWithFallback(
  path: string,
  init: RequestInit = {},
  timeoutMs = 5000
): Promise<BackendFetchResult> {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const candidates = getBackendBaseCandidates();
  const errors: string[] = [];

  for (const baseUrl of candidates) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(`${baseUrl}${normalizedPath}`, {
        ...init,
        signal: controller.signal,
      });
      return { response, backendUrl: baseUrl };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      errors.push(`${baseUrl}: ${message}`);
    } finally {
      clearTimeout(timeout);
    }
  }

  throw new BackendFetchError('All backend candidates failed', candidates, errors);
}
