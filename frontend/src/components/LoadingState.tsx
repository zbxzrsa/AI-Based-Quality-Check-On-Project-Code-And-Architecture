/**
 * LoadingState Component
 * 
 * Features:
 * - Provide unified loading status display
 * - Support multiple loading styles (spinner, skeleton, dots)
 * - Customizable size and color
 * - Optional loading text hint
 * 
 * Verification Requirement: 12.3
 */

import React, { CSSProperties } from 'react';

export type LoadingVariant = 'spinner' | 'skeleton' | 'dots';
export type LoadingSize = 'small' | 'medium' | 'large';

export interface LoadingStateProps {
  /** Loading status variant */
  variant?: LoadingVariant;
  /** Size */
  size?: LoadingSize;
  /** Loading text */
  text?: string;
  /** Whether to show fullscreen */
  fullscreen?: boolean;
  /** Custom class name */
  className?: string;
  /** Custom color */
  color?: string;
  /** Number of skeleton lines (only effective when variant='skeleton') */
  skeletonLines?: number;
}

const sizeMap: Record<LoadingSize, number> = {
  small: 24,
  medium: 40,
  large: 64,
};

/**
 * Spinner loading animation
 */
const Spinner: React.FC<{ size: number; color: string }> = ({ size, color }) => {
  const spinnerStyle: CSSProperties = {
    width: `${size}px`,
    height: `${size}px`,
    border: `${Math.max(2, size / 10)}px solid rgba(0, 0, 0, 0.1)`,
    borderTop: `${Math.max(2, size / 10)}px solid ${color}`,
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  };

  return (
    <>
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
      <div style={spinnerStyle} data-testid="loading-spinner" />
    </>
  );
};

/**
 * Dots loading animation
 */
const Dots: React.FC<{ size: number; color: string }> = ({ size, color }) => {
  const dotSize = size / 4;
  const containerStyle: CSSProperties = {
    display: 'flex',
    gap: `${dotSize / 2}px`,
    alignItems: 'center',
  };

  const dotStyle: CSSProperties = {
    width: `${dotSize}px`,
    height: `${dotSize}px`,
    backgroundColor: color,
    borderRadius: '50%',
    animation: 'bounce 1.4s infinite ease-in-out both',
  };

  return (
    <>
      <style>
        {`
          @keyframes bounce {
            0%, 80%, 100% { 
              transform: scale(0);
              opacity: 0.5;
            }
            40% { 
              transform: scale(1);
              opacity: 1;
            }
          }
        `}
      </style>
      <div style={containerStyle} data-testid="loading-dots">
        <div style={{ ...dotStyle, animationDelay: '-0.32s' }} />
        <div style={{ ...dotStyle, animationDelay: '-0.16s' }} />
        <div style={dotStyle} />
      </div>
    </>
  );
};

/**
 * Skeleton loading placeholder
 */
const Skeleton: React.FC<{ lines: number; color: string }> = ({ lines, color }) => {
  const containerStyle: CSSProperties = {
    width: '100%',
    maxWidth: '600px',
  };

  const lineStyle: CSSProperties = {
    height: '16px',
    backgroundColor: color,
    borderRadius: '4px',
    marginBottom: '12px',
    animation: 'pulse 1.5s ease-in-out infinite',
  };

  return (
    <>
      <style>
        {`
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }
        `}
      </style>
      <div style={containerStyle} data-testid="loading-skeleton">
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            style={{
              ...lineStyle,
              width: index === lines - 1 ? '70%' : '100%',
            }}
          />
        ))}
      </div>
    </>
  );
};

/**
 * LoadingState Component
 * Provides unified loading status display
 */
export const LoadingState: React.FC<LoadingStateProps> = ({
  variant = 'spinner',
  size = 'medium',
  text,
  fullscreen = false,
  className = '',
  color = '#0066cc',
  skeletonLines = 3,
}) => {
  const sizeValue = sizeMap[size];

  const containerStyle: CSSProperties = fullscreen
    ? {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        zIndex: 9999,
      }
    : {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      };

  const textStyle: CSSProperties = {
    marginTop: '16px',
    fontSize: size === 'small' ? '14px' : size === 'medium' ? '16px' : '18px',
    color: '#666',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  };

  const renderLoadingIndicator = () => {
    switch (variant) {
      case 'spinner':
        return <Spinner size={sizeValue} color={color} />;
      case 'dots':
        return <Dots size={sizeValue} color={color} />;
      case 'skeleton':
        return <Skeleton lines={skeletonLines} color={color} />;
      default:
        return <Spinner size={sizeValue} color={color} />;
    }
  };

  return (
    <div
      className={className}
      style={containerStyle}
      data-testid="loading-state"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      {renderLoadingIndicator()}
      {text && (
        <div style={textStyle} data-testid="loading-text">
          {text}
        </div>
      )}
    </div>
  );
};

export default LoadingState;
