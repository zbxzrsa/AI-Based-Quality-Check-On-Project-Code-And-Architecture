import { apiFetch, streamApiFetch } from '../api-client';
import { ReadableStream } from 'stream/web';
import { TextDecoder, TextEncoder } from 'util';

const createJsonResponse = (data: unknown, options: { ok?: boolean; status?: number } = {}) => ({
  ok: options.ok ?? true,
  status: options.status ?? 200,
  headers: {
    get: (header: string) => (header.toLowerCase() === 'content-type' ? 'application/json' : null),
  },
  json: async () => data,
  text: async () => JSON.stringify(data),
});

const createEventStream = (chunks: string[]) => {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
};

describe('api-client streaming helpers', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();
    (global as typeof globalThis & { TextDecoder?: typeof TextDecoder; TextEncoder?: typeof TextEncoder }).TextDecoder = TextDecoder;
    (global as typeof globalThis & { TextDecoder?: typeof TextDecoder; TextEncoder?: typeof TextEncoder }).TextEncoder = TextEncoder;
  });

  it('streamApiFetch parses SSE messages and stops at the done token', async () => {
    const onMessage = jest.fn();

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        get: (header: string) => (header.toLowerCase() === 'content-type' ? 'text/event-stream' : null),
      },
      body: createEventStream([
        'data: {"type":"progress","data":{"progress":25}}\n\n',
        'data: {"type":"result","data":{"status":"completed"}}\n\n',
        'data: [DONE]\n\n',
      ]),
    });

    await streamApiFetch('/api/analyze', {
      method: 'POST',
      body: { repositoryUrl: 'https://github.com/example/repo' },
      onMessage,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/analyze',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify({ repositoryUrl: 'https://github.com/example/repo' }),
        headers: expect.any(Headers),
      })
    );
    expect(onMessage).toHaveBeenCalledTimes(2);
    expect(onMessage).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        data: { type: 'progress', data: { progress: 25 } },
        rawData: '{"type":"progress","data":{"progress":25}}',
      })
    );
    expect(onMessage).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        data: { type: 'result', data: { status: 'completed' } },
      })
    );
  });

  it('apiFetch respects an external abort signal', async () => {
    const controller = new AbortController();
    let requestSignal: AbortSignal | undefined;

    (global.fetch as jest.Mock).mockImplementation(async (_url, init: RequestInit | undefined) => {
      requestSignal = init?.signal as AbortSignal | undefined;
      if (requestSignal?.aborted) {
        throw new DOMException('The operation was aborted.', 'AbortError');
      }
      return createJsonResponse({ ok: true });
    });

    controller.abort();

    await expect(
      apiFetch('/api/test', {
        method: 'GET',
        signal: controller.signal,
      })
    ).rejects.toThrow();

    expect(requestSignal?.aborted).toBe(true);
  });
});
