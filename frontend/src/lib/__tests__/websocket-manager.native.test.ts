import { NativeWebSocketManager } from '../websocket-manager';

class MockNativeWebSocket {
  static instances: MockNativeWebSocket[] = [];

  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  sentMessages: string[] = [];

  constructor(public url: string) {
    MockNativeWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sentMessages.push(data);
  }

  close() {
    this.onclose?.({ code: 1000, reason: 'closed', wasClean: true } as CloseEvent);
  }
}

describe('NativeWebSocketManager', () => {
  let manager: NativeWebSocketManager;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    MockNativeWebSocket.instances = [];
    (global as typeof globalThis & { WebSocket?: typeof MockNativeWebSocket }).WebSocket = MockNativeWebSocket as unknown as typeof WebSocket;
  });

  afterEach(() => {
    if (manager) {
      manager.disconnect();
    }
    jest.useRealTimers();
  });

  it('connects and emits connected for native websocket connections', () => {
    const connectedHandler = jest.fn();

    manager = new NativeWebSocketManager({
      url: 'ws://localhost:8000/ws/analysis/1',
      autoConnect: false,
    });
    manager.on('connected', connectedHandler);

    manager.connect();
    MockNativeWebSocket.instances[0].onopen?.();

    expect(connectedHandler).toHaveBeenCalled();
    expect(manager.isConnected()).toBe(true);
  });

  it('emits message events for incoming websocket payloads', () => {
    const messageHandler = jest.fn();

    manager = new NativeWebSocketManager({
      url: 'ws://localhost:8000/ws/analysis/1',
      autoConnect: false,
    });
    manager.on('message', messageHandler);

    manager.connect();
    MockNativeWebSocket.instances[0].onmessage?.({ data: '{"type":"analysis_progress"}' } as MessageEvent);

    expect(messageHandler).toHaveBeenCalledWith('{"type":"analysis_progress"}');
  });

  it('reconnects after unexpected close with exponential backoff', () => {
    const reconnectingHandler = jest.fn();

    manager = new NativeWebSocketManager({
      url: 'ws://localhost:8000/ws/analysis/1',
      autoConnect: false,
      reconnectionDelay: 1000,
      reconnectionAttempts: 2,
    });
    manager.on('reconnecting', reconnectingHandler);

    manager.connect();
    MockNativeWebSocket.instances[0].onclose?.({ code: 1006, reason: 'unexpected', wasClean: false } as CloseEvent);

    expect(reconnectingHandler).toHaveBeenCalledWith(1, 1000);
    jest.advanceTimersByTime(1000);

    expect(MockNativeWebSocket.instances).toHaveLength(2);
  });

  it('does not reconnect after manual disconnect', () => {
    manager = new NativeWebSocketManager({
      url: 'ws://localhost:8000/ws/analysis/1',
      autoConnect: false,
    });

    manager.connect();
    manager.disconnect();
    jest.advanceTimersByTime(10000);

    expect(MockNativeWebSocket.instances).toHaveLength(1);
    expect(manager.getConnectionState()).toBe('disconnected');
  });
});
