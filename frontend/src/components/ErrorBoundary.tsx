/**
 * ErrorBoundary Component
 * 
 * Features:
 * - Captures errors in React component tree
 * - Shows fallback UI
 * - Integrates with ErrorMonitor for error reporting
 * - Provides "reload" and "report issue" functionality
 * 
 * Verification Requirement: 1.3
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { getErrorMonitor } from '../services/ErrorMonitor';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, errorInfo: ErrorInfo, reset: () => void) => ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  onReset?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * ErrorBoundary class component
 * Catches JavaScript errors in child component tree, records error, and shows fallback UI
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  /**
   * Called when a child component throws an error
   */
  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  /**
   * Captures error and reports to monitoring service
   */
  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Update state to contain errorInfo
    this.setState({
      errorInfo,
    });

    // Report to ErrorMonitor
    try {
      const errorMonitor = getErrorMonitor();
      errorMonitor.captureError(error, {
        url: window.location.href,
        userAgent: navigator.userAgent,
        timestamp: new Date(),
        additionalData: {
          componentStack: errorInfo.componentStack,
          errorBoundary: true,
        },
      });
    } catch (monitorError) {
      // If ErrorMonitor is not initialized or fails, at least output to console
      console.error('Failed to report error to ErrorMonitor:', monitorError);
      console.error('Original error:', error, errorInfo);
    }

    // Call custom error handler
    if (this.props.onError) {
      try {
        this.props.onError(error, errorInfo);
      } catch (handlerError) {
        console.error('Error in onError handler:', handlerError);
      }
    }
  }

  /**
   * Reset error state and try to re-render
   */
  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });

    // Call custom reset handler
    if (this.props.onReset) {
      try {
        this.props.onReset();
      } catch (resetError) {
        console.error('Error in onReset handler:', resetError);
      }
    }
  };

  /**
   * Reload the page
   */
  handleReload = (): void => {
    window.location.reload();
  };

  /**
   * Report issue (open feedback form or email)
   */
  handleReportIssue = (): void => {
    const { error, errorInfo } = this.state;
    
    // Build issue report content
    const issueBody = encodeURIComponent(
      `## Error Report\n\n` +
      `**Error Message:** ${error?.message || 'Unknown error'}\n\n` +
      `**Stack Trace:**\n\`\`\`\n${error?.stack || 'No stack trace'}\n\`\`\`\n\n` +
      `**Component Stack:**\n\`\`\`\n${errorInfo?.componentStack || 'No component stack'}\n\`\`\`\n\n` +
      `**URL:** ${window.location.href}\n` +
      `**User Agent:** ${navigator.userAgent}\n` +
      `**Timestamp:** ${new Date().toISOString()}\n`
    );

    // In a real application, this could:
    // 1. Open internal issue tracking system
    // 2. Send to support email
    // 3. Open feedback form
    // Here we use mailto as an example
    const mailtoLink = `mailto:support@example.com?subject=${encodeURIComponent('Error Report')}&body=${issueBody}`;
    window.location.href = mailtoLink;
  };

  render(): ReactNode {
    const { hasError, error, errorInfo } = this.state;
    const { children, fallback } = this.props;

    if (hasError && error) {
      // If custom fallback is provided, use it
      if (fallback && errorInfo) {
        return fallback(error, errorInfo, this.handleReset);
      }

      // Default fallback UI
      return (
        <div
          style={{
            padding: '40px 20px',
            maxWidth: '800px',
            margin: '0 auto',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
          }}
        >
          <div
            style={{
              backgroundColor: '#fee',
              border: '1px solid #fcc',
              borderRadius: '8px',
              padding: '24px',
            }}
          >
            <h1
              style={{
                color: '#c33',
                fontSize: '24px',
                marginTop: 0,
                marginBottom: '16px',
              }}
            >
              ⚠️ Something went wrong
            </h1>
            
            <p
              style={{
                color: '#666',
                fontSize: '16px',
                lineHeight: '1.5',
                marginBottom: '24px',
              }}
            >
              We&apos;re sorry, but something unexpected happened. The error has been reported to our team.
            </p>

            {process.env.NODE_ENV === 'development' && (
              <details
                style={{
                  marginBottom: '24px',
                  padding: '16px',
                  backgroundColor: '#fff',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                }}
              >
                <summary
                  style={{
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    marginBottom: '8px',
                  }}
                >
                  Error Details (Development Only)
                </summary>
                <div
                  style={{
                    marginTop: '12px',
                    fontSize: '14px',
                    fontFamily: 'monospace',
                  }}
                >
                  <p style={{ color: '#c33', fontWeight: 'bold' }}>
                    {error.message}
                  </p>
                  <pre
                    style={{
                      overflow: 'auto',
                      padding: '12px',
                      backgroundColor: '#f5f5f5',
                      borderRadius: '4px',
                      fontSize: '12px',
                      lineHeight: '1.4',
                    }}
                  >
                    {error.stack}
                  </pre>
                  {errorInfo?.componentStack && (
                    <>
                      <p style={{ fontWeight: 'bold', marginTop: '16px' }}>
                        Component Stack:
                      </p>
                      <pre
                        style={{
                          overflow: 'auto',
                          padding: '12px',
                          backgroundColor: '#f5f5f5',
                          borderRadius: '4px',
                          fontSize: '12px',
                          lineHeight: '1.4',
                        }}
                      >
                        {errorInfo.componentStack}
                      </pre>
                    </>
                  )}
                </div>
              </details>
            )}

            <div
              style={{
                display: 'flex',
                gap: '12px',
                flexWrap: 'wrap',
              }}
            >
              <button
                onClick={this.handleReset}
                style={{
                  padding: '12px 24px',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  color: '#fff',
                  backgroundColor: '#0066cc',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.backgroundColor = '#0052a3';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.backgroundColor = '#0066cc';
                }}
              >
                Try Again
              </button>

              <button
                onClick={this.handleReload}
                style={{
                  padding: '12px 24px',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  color: '#333',
                  backgroundColor: '#f0f0f0',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.backgroundColor = '#e0e0e0';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.backgroundColor = '#f0f0f0';
                }}
              >
                Reload Page
              </button>

              <button
                onClick={this.handleReportIssue}
                style={{
                  padding: '12px 24px',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  color: '#333',
                  backgroundColor: '#f0f0f0',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.backgroundColor = '#e0e0e0';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.backgroundColor = '#f0f0f0';
                }}
              >
                Report Issue
              </button>
            </div>
          </div>
        </div>
      );
    }

    return children;
  }
}

export default ErrorBoundary;
