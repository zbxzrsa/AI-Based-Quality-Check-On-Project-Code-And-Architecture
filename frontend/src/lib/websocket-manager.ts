/**
 * WebSocket Manager for Real-time Communication
 * 
 * Provides robust WebSocket connection management with:
 * - Automatic reconnection with exponential backoff
 * - Connection state management
 * - Event-driven architecture
 * - Performance monitoring
 * - Error handling and recovery
 */

import { io, Socket } from 'socket.io-client';
import { EventEmitter } from 'events';

interface WebSocketConfig {
  url: string;
  autoConnect?: boolean;
  reconnection?: boolean;
  reconnectionAttempts?: number;
  reconnectionDelay?: number;
  maxReconnectionDelay?: number;
  timeout?: number;
}

interface ConnectionMetrics {
  connectTime: number;
  disconnectTime?: number;
  reconnectAttempts: number;
  totalMessages: number;
  lastMessageTime?: number;
  latency: number;
}

export class WebSocketManager extends EventEmitter {
  private socket: Socket | null = null;
  private config: Required<WebSocketConfig>;
  private connectionState: 'disconnected' | 'connecting' | 'connected' | 'reconnecting' = 'disconnected';
  private metrics: ConnectionMetrics;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;

  constructor(config: WebSocketConfig) {
    super();
    
    this.config = {
      url: config.url,
      autoConnect: config.autoConnect ?? true,
      reconnection: config.reconnection ?? true,
      reconnectionAttempts: config.reconnectionAttempts ?? 5,
      reconnectionDelay: config.reconnectionDelay ?? 1000,
      maxReconnectionDelay: config.maxReconnectionDelay ?? 30000,
      timeout: config.timeout ?? 20000,
    };

    this.metrics = {
      connectTime: 0,
      reconnectAttempts: 0,
      totalMessages: 0,
      latency: 0,
    };

    if (this.config.autoConnect) {
      this.connect();
    }
  }

  connect(): void {
    if (this.connectionState === 'connected' || this.connectionState === 'connecting') {
      return;
    }

    this.connectionState = 'connecting';
    this.emit('connecting');

    this.socket = io(this.config.url, {
      timeout: this.config.timeout,
      reconnection: false, // We handle reconnection manually
      transports: ['websocket', 'polling'],
      upgrade: true,
      rememberUpgrade: true,
    });

    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      this.connectionState = 'connected';
      this.metrics.connectTime = Date.now();
      this.metrics.reconnectAttempts = 0;
      
      this.emit('connected');
      this.startHeartbeat();
      
      console.log('🔗 WebSocket connected');
    });

    this.socket.on('disconnect', (reason) => {
      this.connectionState = 'disconnected';
      this.metrics.disconnectTime = Date.now();
      
      this.emit('disconnected', reason);
      this.stopHeartbeat();
      
      console.log('🔌 WebSocket disconnected:', reason);
      
      if (this.config.reconnection && reason !== 'io client disconnect') {
        this.scheduleReconnect();
      }
    });

    this.socket.on('connect_error', (error) => {
      console.error('❌ WebSocket connection error:', error);
      this.emit('error', error);
      
      if (this.config.reconnection) {
        this.scheduleReconnect();
      }
    });

    this.socket.on('reconnect', () => {
      this.emit('reconnected');
      console.log('🔄 WebSocket reconnected');
    });

    // Handle incoming messages
    this.socket.onAny((event, ...args) => {
      this.metrics.totalMessages++;
      this.metrics.lastMessageTime = Date.now();
      
      // Emit the event to listeners
      this.emit(event, ...args);
    });

    // Handle pong for latency measurement
    this.socket.on('pong', (latency) => {
      this.metrics.latency = latency;
    });
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    if (this.metrics.reconnectAttempts >= this.config.reconnectionAttempts) {
      console.error('❌ Max reconnection attempts reached');
      this.emit('maxReconnectAttemptsReached');
      return;
    }

    this.connectionState = 'reconnecting';
    this.metrics.reconnectAttempts++;

    const delay = Math.min(
      this.config.reconnectionDelay * Math.pow(2, this.metrics.reconnectAttempts - 1),
      this.config.maxReconnectionDelay
    );

    console.log(`🔄 Reconnecting in ${delay}ms (attempt ${this.metrics.reconnectAttempts}/${this.config.reconnectionAttempts})`);
    
    this.emit('reconnecting', this.metrics.reconnectAttempts, delay);

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.socket && this.connectionState === 'connected') {
        this.socket.emit('ping');
      }
    }, 30000); // Ping every 30 seconds
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  disconnect(): void {
    this.config.reconnection = false; // Disable auto-reconnection
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    this.stopHeartbeat();

    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }

    this.connectionState = 'disconnected';
    this.emit('disconnected', 'manual disconnect');
  }

  send(event: string, data?: any): boolean {
    if (!this.socket || this.connectionState !== 'connected') {
      console.warn('⚠️ Cannot send message: WebSocket not connected');
      return false;
    }

    try {
      this.socket.emit(event, data);
      return true;
    } catch (error) {
      console.error('❌ Failed to send message:', error);
      this.emit('error', error);
      return false;
    }
  }

  getConnectionState(): string {
    return this.connectionState;
  }

  getMetrics(): ConnectionMetrics {
    return { ...this.metrics };
  }

  isConnected(): boolean {
    return this.connectionState === 'connected';
  }

  // Convenience methods for common events
  onProjectUpdate(callback: (data: any) => void): void {
    this.on('project:updated', callback);
  }

  onReviewUpdate(callback: (data: any) => void): void {
    this.on('review:updated', callback);
  }

  onLibraryUpdate(callback: (data: any) => void): void {
    this.on('library:updated', callback);
  }

  onSystemAlert(callback: (data: any) => void): void {
    this.on('system:alert', callback);
  }

  onPerformanceUpdate(callback: (data: any) => void): void {
    this.on('performance:update', callback);
  }

  // Subscribe to specific project updates
  subscribeToProject(projectId: number): void {
    this.send('subscribe:project', { projectId });
  }

  unsubscribeFromProject(projectId: number): void {
    this.send('unsubscribe:project', { projectId });
  }

  // Subscribe to performance monitoring
  subscribeToPerformanceUpdates(): void {
    this.send('subscribe:performance');
  }

  unsubscribeFromPerformanceUpdates(): void {
    this.send('unsubscribe:performance');
  }
}

// Global WebSocket manager instance
let wsManager: WebSocketManager | null = null;

export function getWebSocketManager(): WebSocketManager {
  if (!wsManager) {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'http://localhost:8000';
    wsManager = new WebSocketManager({ url: wsUrl });
  }
  return wsManager;
}

// React hook for WebSocket connection
export function useWebSocket() {
  const manager = getWebSocketManager();
  
  return {
    manager,
    isConnected: manager.isConnected(),
    connectionState: manager.getConnectionState(),
    metrics: manager.getMetrics(),
    send: manager.send.bind(manager),
    subscribe: manager.on.bind(manager),
    unsubscribe: manager.off.bind(manager),
  };
}