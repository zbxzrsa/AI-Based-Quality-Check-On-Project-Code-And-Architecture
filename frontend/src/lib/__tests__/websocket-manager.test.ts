/**
 * Unit tests for WebSocketManager
 * Tests connection management, reconnection logic, and event handling
 */

import { WebSocketManager } from '../websocket-manager';
import { io, Socket } from 'socket.io-client';

// Mock socket.io-client
jest.mock('socket.io-client');

const mockIo = io as jest.MockedFunction<typeof io>;

describe('WebSocketManager', () => {
  let mockSocket: Partial<Socket>;
  let manager: WebSocketManager;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();

    // Create mock socket
    mockSocket = {
      on: jest.fn(),
      emit: jest.fn(),
      disconnect: jest.fn(),
      onAny: jest.fn(),
    };

    mockIo.mockReturnValue(mockSocket as Socket);
  });

  afterEach(() => {
    jest.useRealTimers();
    if (manager) {
      manager.disconnect();
    }
  });

  describe('Initialization', () => {
    it('should create WebSocket connection with autoConnect', () => {
      manager = new WebSocketManager({
        url: 'http://localhost:8000',
        autoConnect: true,
      });

      expect(mockIo).toHaveBeenCalledWith(
        'http://localhost:8000',
        expect.objectContaining({
          timeout: 20000,
          reconnection: false,
          transports: ['websocket', 'polling'],
        })
      );
    });

    it('should not connect when autoConnect is false', () => {
      manager = new WebSocketManager({
        url: 'http://localhost:8000',
        autoConnect: false,
      });

      expect(mockIo).not.toHaveBeenCalled();
    });

    it('should use custom timeout', () => {
      manager = new WebSocketManager({
        url: 'http://localhost:8000',
        timeout: 30000,
      });

      expect(mockIo).toHaveBeenCalledWith(
        'http://localhost:8000',
        expect.objectContaining({
          timeout: 30000,
        })
      );
    });
  });

  describe('Connection Events', () => {
    beforeEach(() => {
      manager = new WebSocketManager({
        url: 'http://localhost:8000',
        autoConnect: false,
      });
    });

    it('should emit connecting event when connecting', () => {
      const connectingHandler = jest.fn();
      manager.on('connecting', connectingHandler);

      manager.connect();

      expect(connectingHandler).toHaveBeenCalled();
    });

    it('should emit connected event on successful connection', () => {
      const connectedHandler = jest.fn();
      manager.on('connected', connectedHandler);

      manager.connect();

      // Simulate connection
      const connectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'connect'
      )?.[1];
      connectHandler?.();

      expect(connectedHandler).toHaveBeenCalled();
      expect(manager.isConnected()).toBe(true);
    });

    it('should emit disconnected event on disconnect', () => {
      const disconnectedHandler = jest.fn();
      manager.on('disconnected', disconnectedHandler);

      manager.connect();

      // Simulate connection then disconnection
      const connectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'connect'
      )?.[1];
      connectHandler?.();

      const disconnectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'disconnect'
      )?.[1];
      disconnectHandler?.('transport close');

      expect(disconnectedHandler).toHaveBeenCalledWith('transport close');
      expect(manager.isConnected()).toBe(false);
    });

    it('should emit error event on connection error', () => {
      const errorHandler = jest.fn();
      manager.on('error', errorHandler);

      manager.connect();

      const error = new Error('Connection failed');
      const errorEventHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'connect_error'
      )?.[1];
      errorEventHandler?.(error);

      expect(errorHandler).toHaveBeenCalledWith(error);
    });
  });

  describe('Reconnection Logic', () => {
    beforeEach(() => {
      manager = new WebSocketManager({
        url: 'http://localhost:8000',
        autoConnect: false,
        reconnection: true,
        reconnectionAttempts: 3,
        reconnectionDelay: 1000,
      });
    });

    it('should attempt reconnection after disconnect', () => {
      const reconnectingHandler = jest.fn();
      manager.on('reconnecting', reconnectingHandler);

      manager.connect();

      // Simulate disconnect
      const disconnectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'disconnect'
      )?.[1];
      disconnectHandler?.('transport close');

      // Fast-forward time to trigger reconnection
      jest.advanceTimersByTime(1000);

      expect(reconnectingHandler).toHaveBeenCalled();
    });

    it('should use exponential backoff for reconnection', () => {
      manager.connect();

      // Simulate multiple disconnections
      const disconnectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'disconnect'
      )?.[1];

      // First reconnection: 1000ms
      disconnectHandler?.('transport close');
      jest.advanceTimersByTime(1000);

      // Second reconnection: 2000ms
      disconnectHandler?.('transport close');
      jest.advanceTimersByTime(2000);

      // Third reconnection: 4000ms
      disconnectHandler?.('transport close');
      jest.advanceTimersByTime(4000);

      expect(mockIo).toHaveBeenCalledTimes(4); // Initial + 3 reconnections
    });

    it('should stop reconnecting after max attempts', () => {
      const maxAttemptsHandler = jest.fn();
      manager.on('maxReconnectAttemptsReached', maxAttemptsHandler);

      manager.connect();

      const disconnectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'disconnect'
      )?.[1];

      // Exceed max attempts
      for (let i = 0; i < 3; i++) {
        disconnectHandler?.('transport close');
        jest.advanceTimersByTime(10000);
      }

      disconnectHandler?.('transport close');
      jest.advanceTimersByTime(10000);

      expect(maxAttemptsHandler).toHaveBeenCalled();
    });

    it('should not reconnect on manual disconnect', () => {
      manager.connect();

      const disconnectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'disconnect'
      )?.[1];
      disconnectHandler?.('io client disconnect');

      jest.advanceTimersByTime(10000);

      // Should only be called once (initial connection)
      expect(mockIo).toHaveBeenCalledTimes(1);
    });
  });

  describe('Message Sending', () => {
    beforeEach(() => {
      manager = new WebSocketManager({
        url: 'http://localhost:8000',
        autoConnect: false,
      });
    });

    it('should send message when connected', () => {
      manager.connect();

      // Simulate connection
      const connectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'connect'
      )?.[1];
      connectHandler?.();

      const result = manager.send('test:event', { data: 'test' });

      expect(result).toBe(true);
      expect(mockSocket.emit).toHaveBeenCalledWith('test:event', { data: 'test' });
    });

    it('should not send message when disconnected', () => {
      const result = manager.send('test:event', { data: 'test' });

      expect(result).toBe(false);
      expect(mockSocket.emit).not.toHaveBeenCalled();
    });

    it('should handle send errors gracefully', () => {
      manager.connect();

      const connectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'connect'
      )?.[1];
      connectHandler?.();

      (mockSocket.emit as jest.Mock).mockImplementation(() => {
        throw new Error('Send failed');
      });

      const errorHandler = jest.fn();
      manager.on('error', errorHandler);

      const result = manager.send('test:event', { data: 'test' });

      expect(result).toBe(false);
      expect(errorHandler).toHaveBeenCalled();
    });
  });

  describe('Heartbeat', () => {
    beforeEach(() => {
      manager = new WebSocketManager({
        url: 'http://localhost:8000',
        autoConnect: false,
      });
    });

    it('should send ping messages periodically when connected', () => {
      manager.connect();

      const connectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'connect'
      )?.[1];
      connectHandler?.();

      // Fast-forward 30 seconds
      jest.advanceTimersByTime(30000);

      expect(mockSocket.emit).toHaveBeenCalledWith('ping');
    });

    it('should stop heartbeat on disconnect', () => {
      manager.connect();

      const connectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'connect'
      )?.[1];
      connectHandler?.();

      const disconnectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'disconnect'
      )?.[1];
      disconnectHandler?.('transport close');

      (mockSocket.emit as jest.Mock).mockClear();

      // Fast-forward time
      jest.advanceTimersByTime(60000);

      expect(mockSocket.emit).not.toHaveBeenCalledWith('ping');
    });
  });

  describe('Metrics', () => {
    beforeEach(() => {
      manager = new WebSocketManager({
        url: 'http://localhost:8000',
        autoConnect: false,
      });
    });

    it('should track connection metrics', () => {
      manager.connect();

      const connectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'connect'
      )?.[1];
      connectHandler?.();

      const metrics = manager.getMetrics();

      expect(metrics.connectTime).toBeGreaterThan(0);
      expect(metrics.reconnectAttempts).toBe(0);
      expect(metrics.totalMessages).toBe(0);
    });

    it('should track message count', () => {
      manager.connect();

      const connectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'connect'
      )?.[1];
      connectHandler?.();

      // Simulate receiving messages
      const onAnyHandler = (mockSocket.onAny as jest.Mock).mock.calls[0]?.[0];
      onAnyHandler?.('test:event', { data: 'test' });
      onAnyHandler?.('test:event2', { data: 'test2' });

      const metrics = manager.getMetrics();
      expect(metrics.totalMessages).toBe(2);
    });

    it('should track latency from pong events', () => {
      manager.connect();

      const connectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'connect'
      )?.[1];
      connectHandler?.();

      const pongHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'pong'
      )?.[1];
      pongHandler?.(50);

      const metrics = manager.getMetrics();
      expect(metrics.latency).toBe(50);
    });
  });

  describe('Convenience Methods', () => {
    beforeEach(() => {
      manager = new WebSocketManager({
        url: 'http://localhost:8000',
        autoConnect: false,
      });
      manager.connect();

      const connectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'connect'
      )?.[1];
      connectHandler?.();
    });

    it('should subscribe to project updates', () => {
      manager.subscribeToProject(123);

      expect(mockSocket.emit).toHaveBeenCalledWith('subscribe:project', { projectId: 123 });
    });

    it('should unsubscribe from project updates', () => {
      manager.unsubscribeFromProject(123);

      expect(mockSocket.emit).toHaveBeenCalledWith('unsubscribe:project', { projectId: 123 });
    });

    it('should subscribe to performance updates', () => {
      manager.subscribeToPerformanceUpdates();

      expect(mockSocket.emit).toHaveBeenCalledWith('subscribe:performance', undefined);
    });

    it('should handle project update events', () => {
      const callback = jest.fn();
      manager.onProjectUpdate(callback);

      const onAnyHandler = (mockSocket.onAny as jest.Mock).mock.calls[0]?.[0];
      onAnyHandler?.('project:updated', { id: 123 });

      expect(callback).toHaveBeenCalledWith({ id: 123 });
    });
  });

  describe('Connection State', () => {
    beforeEach(() => {
      manager = new WebSocketManager({
        url: 'http://localhost:8000',
        autoConnect: false,
      });
    });

    it('should return correct connection state', () => {
      expect(manager.getConnectionState()).toBe('disconnected');

      manager.connect();
      expect(manager.getConnectionState()).toBe('connecting');

      const connectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'connect'
      )?.[1];
      connectHandler?.();
      expect(manager.getConnectionState()).toBe('connected');
    });

    it('should return correct isConnected status', () => {
      expect(manager.isConnected()).toBe(false);

      manager.connect();
      const connectHandler = (mockSocket.on as jest.Mock).mock.calls.find(
        call => call[0] === 'connect'
      )?.[1];
      connectHandler?.();

      expect(manager.isConnected()).toBe(true);
    });
  });
});
