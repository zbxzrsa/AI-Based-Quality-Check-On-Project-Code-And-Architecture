/**
 * OfflineIndicator Component
 * 
 * Features:
 * - Detect user online/offline status
 * - Show offline status hint
 * - Auto-detect network recovery
 * - Customizable position and style
 * 
 * Verification Requirement: 12.3
 */

import React, { useState, useEffect, CSSProperties } from 'react';

export type IndicatorPosition = 'top' | 'bottom';

export interface OfflineIndicatorProps {
  /** Indicator position */
  position?: IndicatorPosition;
  /** Message to show when offline */
  offlineMessage?: string;
  /** Message to show when online */
  onlineMessage?: string;
  /** Duration to show online message (ms), 0 means don't auto-hide */
  onlineMessageDuration?: number;
  /** Custom class name */
  className?: string;
  /** Callback when going offline */
  onOffline?: () => void;
  /** Callback when going online */
  onOnline?: () => void;
  /** Whether to show retry button */
  showRetryButton?: boolean;
  /** Retry button click callback */
  onRetry?: () => void;
}

/**
 * OfflineIndicator Component
 * Monitors network status and shows offline hint
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
      
      // Only show recovery message if previously offline
      if (wasOffline) {
        setShowOnlineMessage(true);
        
        // Auto-hide online message
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

    // Add event listeners
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Cleanup function
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [onOffline, onOnline, onlineMessageDuration, wasOffline]);

  const handleRetry = () => {
    if (onRetry) {
      onRetry();
    } else {
      // Default behavior: reload page
      window.location.reload();
    }
  };

  // If online and not showing online message, don't render anything
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
