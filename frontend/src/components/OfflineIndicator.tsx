/**
 * OfflineIndicatorcomponent
 * 
 * feature:
 * - 检测user在线/离线status
 * - show离线statushint
 * - 自动检测网络恢复
 * - 可自定义位置andstyle
 * 
 * verifyRequirement: 12.3
 */

import React, { useState, useEffect, CSSProperties } from 'react';

export type IndicatorPosition = 'top' | 'bottom';

export interface OfflineIndicatorProps {
  /** 指示器位置 */
  position?: IndicatorPosition;
  /** 离线时show的消息 */
  offlineMessage?: string;
  /** 在线时show的消息 */
  onlineMessage?: string;
  /** 在线消息show时长（ms），0表示不自动hide */
  onlineMessageDuration?: number;
  /** 自定义class名 */
  className?: string;
  /** 离线时的回调 */
  onOffline?: () => void;
  /** 在线时的回调 */
  onOnline?: () => void;
  /** 是否showretrybutton */
  showRetryButton?: boolean;
  /** retrybutton点击回调 */
  onRetry?: () => void;
}

/**
 * OfflineIndicatorcomponent
 * 监听网络status并show离线hint
 */
export const OfflineIndicator: React.FC<OfflineIndicatorProps> = ({
  position = 'top',
  offlineMessage = 'You are currently offline. Some features may be unavailable.',
  onlineMessage = 'Connection restored',
  onlineMessageDuration = 3000,
  className = '',
  onOffline,
  onOnline,
  showRetryButton = true,
  onRetry,
}) => {
  const [isOnline, setIsOnline] = useState<boolean>(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );
  const [showOnlineMessage, setShowOnlineMessage] = useState<boolean>(false);
  const [wasOffline, setWasOffline] = useState<boolean>(false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      
      // 只有在之前离线的情况下才show恢复消息
      if (wasOffline) {
        setShowOnlineMessage(true);
        
        // 自动hide在线消息
        if (onlineMessageDuration > 0) {
          setTimeout(() => {
            setShowOnlineMessage(false);
            setWasOffline(false);
          }, onlineMessageDuration);
        }
      }
      
      onOnline?.();
    };

    const handleOffline = () => {
      setIsOnline(false);
      setWasOffline(true);
      setShowOnlineMessage(false);
      onOffline?.();
    };

    // add事件监听器
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // cleanupfunction
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [onOffline, onOnline, onlineMessageDuration, wasOffline]);

  const handleRetry = () => {
    if (onRetry) {
      onRetry();
    } else {
      // 默认行为：重新load页面
      window.location.reload();
    }
  };

  // 如果在线且不show在线消息，则不render任何content
  if (isOnline && !showOnlineMessage) {
    return null;
  }

  const isOfflineState = !isOnline;
  const message = isOfflineState ? offlineMessage : onlineMessage;
  const backgroundColor = isOfflineState ? '#ff6b6b' : '#51cf66';

  const containerStyle: CSSProperties = {
    position: 'fixed',
    left: 0,
    right: 0,
    [position]: 0,
    backgroundColor,
    color: '#fff',
    padding: '12px 20px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
    zIndex: 10000,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    fontSize: '14px',
    fontWeight: 500,
    animation: 'slideIn 0.3s ease-out',
  };

  const iconStyle: CSSProperties = {
    fontSize: '18px',
    display: 'flex',
    alignItems: 'center',
  };

  const buttonStyle: CSSProperties = {
    padding: '6px 16px',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    border: '1px solid rgba(255, 255, 255, 0.3)',
    borderRadius: '4px',
    color: '#fff',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  };

  return (
    <>
      <style>
        {`
          @keyframes slideIn {
            from {
              transform: translateY(${position === 'top' ? '-100%' : '100%'});
              opacity: 0;
            }
            to {
              transform: translateY(0);
              opacity: 1;
            }
          }
        `}
      </style>
      <div
        className={className}
        style={containerStyle}
        data-testid="offline-indicator"
        role="alert"
        aria-live="assertive"
      >
        <span style={iconStyle} data-testid="indicator-icon">
          {isOfflineState ? '⚠️' : '✓'}
        </span>
        <span data-testid="indicator-message">{message}</span>
        {isOfflineState && showRetryButton && (
          <button
            onClick={handleRetry}
            style={buttonStyle}
            data-testid="retry-button"
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.3)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
            }}
          >
            Retry
          </button>
        )}
      </div>
    </>
  );
};

export default OfflineIndicator;
