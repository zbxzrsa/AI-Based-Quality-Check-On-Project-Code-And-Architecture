import { useState, useCallback, useRef } from 'react';

interface AnalysisResult {
  repositoryUrl: string;
  analysisId: string;
  status: 'pending' | 'analyzing' | 'completed' | 'failed';
  architectureSummary: {
    totalFiles: number;
    totalClasses: number;
    totalFunctions: number;
    architecturalPurpose: string;
    detectedPatterns: string[];
    potentialIssues: string[];
  };
  codeHierarchy: {
    files: Array<{
      path: string;
      type: 'python' | 'javascript' | 'typescript' | 'unknown';
      classes: Array<{
        name: string;
        line: number;
        methods: Array<{
          name: string;
          line: number;
          complexity: number;
        }>;
      }>;
      functions: Array<{
        name: string;
        line: number;
        complexity: number;
      }>;
    }>;
  };
  metrics: {
    cyclomaticComplexity: number;
    coupling: number;
    cohesion: number;
    codeSmells: number;
  };
}

interface AnalysisProgress {
  stage: string;
  progress: number;
  message: string;
}

export default function ProjectAnalysisDashboard() {
  const [repositoryUrl, setRepositoryUrl] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState<AnalysisProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const validateRepositoryUrl = (url: string): boolean => {
    // Basic GitHub URL validation
    const githubRegex = /^(https?:\/\/)?(www\.)?github\.com\/[a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+(\/)?$|^git@github\.com:[a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+\.git$/;
    return githubRegex.test(url.trim());
  };

  const handleAnalysis = async () => {
    if (!validateRepositoryUrl(repositoryUrl)) {
      setError('Please enter a valid GitHub repository URL');
      return;
    }

    setError(null);
    setIsAnalyzing(true);
    setAnalysisResult(null);
    setAnalysisProgress({ stage: 'initializing', progress: 0, message: 'Initializing analysis...' });
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repositoryUrl: repositoryUrl.trim(),
          includeArchitectureAnalysis: true,
          includeComplexityMetrics: true,
          includeDependencyAnalysis: true
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') break;

              try {
                const event = JSON.parse(data);
                handleServerSentEvent(event);
              } catch (e) {
                console.warn('Failed to parse SSE event:', e);
              }
            }
          }
        }
      }

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        console.log('Analysis cancelled by user');
      } else {
        setError(err instanceof Error ? err.message : 'Analysis failed');
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleServerSentEvent = useCallback((event: any) => {
    switch (event.type) {
      case 'progress':
        setAnalysisProgress(event.data);
        break;
      case 'result':
        setAnalysisResult(event.data);
        setAnalysisProgress(null);
        console.log('Analysis complete');
        break;
      case 'error':
        setError(event.data.message);
        setIsAnalyzing(false);
        break;
    }
  }, []);

  const handleCancelAnalysis = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsAnalyzing(false);
    setAnalysisProgress(null);
  };

  const getArchitectureComplexityColor = (complexity: number) => {
    if (complexity < 5) return '#10b981'; // green
    if (complexity < 10) return '#f59e0b'; // yellow
    return '#ef4444'; // red
  };

  const getArchitectureComplexityLabel = (complexity: number) => {
    if (complexity < 5) return 'Low';
    if (complexity < 10) return 'Medium';
    return 'High';
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '8px' }}>
          Architecture Analysis Dashboard
        </h1>
        <p style={{ color: '#6b7280' }}>
          Upload a GitHub repository to analyze its architecture, code structure, and identify potential issues.
        </p>
      </div>

      {/* Repository Analysis Form */}
      <div style={{ 
        border: '1px solid #e5e7eb', 
        borderRadius: '8px', 
        padding: '24px', 
        marginBottom: '24px',
        backgroundColor: '#ffffff'
      }}>
        <div style={{ marginBottom: '16px' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '8px' }}>
            📁 Repository Analysis
          </h2>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
              GitHub Repository URL
            </label>
            <input
              type="text"
              placeholder="https://github.com/username/repository"
              value={repositoryUrl}
              onChange={(e) => setRepositoryUrl(e.target.value)}
              disabled={isAnalyzing}
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '14px'
              }}
            />
            <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
              Enter the URL of a public GitHub repository to analyze its architecture.
            </p>
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
              Analysis Options
            </label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>💻</span>
                <span style={{ fontSize: '14px' }}>Architecture Analysis</span>
                <span style={{ 
                  padding: '2px 8px', 
                  backgroundColor: '#e5e7eb', 
                  borderRadius: '999px', 
                  fontSize: '12px' 
                }}>
                  Enabled
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>📊</span>
                <span style={{ fontSize: '14px' }}>Complexity Metrics</span>
                <span style={{ 
                  padding: '2px 8px', 
                  backgroundColor: '#e5e7eb', 
                  borderRadius: '999px', 
                  fontSize: '12px' 
                }}>
                  Enabled
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>🔗</span>
                <span style={{ fontSize: '14px' }}>Dependency Analysis</span>
                <span style={{ 
                  padding: '2px 8px', 
                  backgroundColor: '#e5e7eb', 
                  borderRadius: '999px', 
                  fontSize: '12px' 
                }}>
                  Enabled
                </span>
              </div>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '16px', display: 'flex', gap: '8px' }}>
          <button 
            onClick={handleAnalysis} 
            disabled={isAnalyzing || !repositoryUrl.trim()}
            style={{
              padding: '12px 24px',
              backgroundColor: isAnalyzing || !repositoryUrl.trim() ? '#9ca3af' : '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: '500',
              cursor: isAnalyzing || !repositoryUrl.trim() ? 'not-allowed' : 'pointer'
            }}
          >
            {isAnalyzing ? (
              <>
                <span style={{ marginRight: '8px' }}>⏳</span>
                Analyzing...
              </>
            ) : (
              <>
                <span style={{ marginRight: '8px' }}>🚀</span>
                Start Analysis
              </>
            )}
          </button>
          {isAnalyzing && (
            <button 
              onClick={handleCancelAnalysis}
              style={{
                padding: '12px 24px',
                backgroundColor: '#ef4444',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Analysis Progress */}
      {analysisProgress && (
        <div style={{ 
          border: '1px solid #e5e7eb', 
          borderRadius: '8px', 
          padding: '24px', 
          marginBottom: '24px',
          backgroundColor: '#ffffff'
        }}>
          <div style={{ marginBottom: '16px' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '8px' }}>
              ⏳ Analysis in Progress
            </h2>
          </div>
          <div style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span>{analysisProgress.stage}</span>
              <span>{analysisProgress.progress}%</span>
            </div>
            <div style={{ 
              width: '100%', 
              height: '8px', 
              backgroundColor: '#e5e7eb', 
              borderRadius: '4px',
              overflow: 'hidden'
            }}>
              <div style={{ 
                width: `${analysisProgress.progress}%`, 
                height: '100%', 
                backgroundColor: '#2563eb',
                transition: 'width 0.3s ease'
              }} />
            </div>
            <p style={{ fontSize: '14px', color: '#6b7280', marginTop: '8px' }}>
              {analysisProgress.message}
            </p>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div style={{ 
          border: '1px solid #fecaca', 
          borderRadius: '8px', 
          padding: '16px', 
          marginBottom: '24px',
          backgroundColor: '#fef2f2',
          color: '#dc2626'
        }}>
          <div style={{ fontWeight: '600', marginBottom: '4px' }}>Error</div>
          <div>{error}</div>
        </div>
      )}

      {/* Analysis Results */}
      {analysisResult && (
        <div style={{ display: 'grid', gap: '24px' }}>
          
          {/* Architecture Summary */}
          <div style={{ 
            border: '1px solid #e5e7eb', 
            borderRadius: '8px', 
            padding: '24px',
            backgroundColor: '#ffffff'
          }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '16px' }}>
              📄 Architecture Summary
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Total Files</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '700' }}>
                  {analysisResult.architectureSummary.totalFiles}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Classes</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '700' }}>
                  {analysisResult.architectureSummary.totalClasses}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Functions</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '700' }}>
                  {analysisResult.architectureSummary.totalFunctions}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Architectural Purpose</div>
                <div style={{ fontSize: '14px', color: '#374151' }}>
                  {analysisResult.architectureSummary.architecturalPurpose}
                </div>
              </div>
            </div>
          </div>

          {/* Detected Patterns and Issues */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div style={{ 
              border: '1px solid #e5e7eb', 
              borderRadius: '8px', 
              padding: '24px',
              backgroundColor: '#ffffff'
            }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '16px' }}>
                ✅ Detected Patterns
              </h2>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {analysisResult.architectureSummary.detectedPatterns.map((pattern, index) => (
                  <span key={index} style={{ 
                    padding: '4px 8px', 
                    backgroundColor: '#dcfce7', 
                    color: '#166534',
                    borderRadius: '999px', 
                    fontSize: '12px' 
                  }}>
                    {pattern}
                  </span>
                ))}
              </div>
            </div>

            <div style={{ 
              border: '1px solid #e5e7eb', 
              borderRadius: '8px', 
              padding: '24px',
              backgroundColor: '#ffffff'
            }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '16px' }}>
                ⚠️ Potential Issues
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {analysisResult.architectureSummary.potentialIssues.map((issue, index) => (
                  <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}>
                    <span>⚠️</span>
                    {issue}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Code Metrics */}
          <div style={{ 
            border: '1px solid #e5e7eb', 
            borderRadius: '8px', 
            padding: '24px',
            backgroundColor: '#ffffff'
          }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '16px' }}>
              📊 Code Metrics
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Cyclomatic Complexity</div>
                <div style={{ 
                  width: '100%', 
                  height: '8px', 
                  backgroundColor: '#e5e7eb', 
                  borderRadius: '4px',
                  marginBottom: '8px'
                }}>
                  <div style={{ 
                    width: '60%', 
                    height: '100%', 
                    backgroundColor: getArchitectureComplexityColor(analysisResult.metrics.cyclomaticComplexity),
                    borderRadius: '4px'
                  }} />
                </div>
                <div style={{ fontSize: '14px', fontWeight: '600', color: getArchitectureComplexityColor(analysisResult.metrics.cyclomaticComplexity) }}>
                  {getArchitectureComplexityLabel(analysisResult.metrics.cyclomaticComplexity)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Coupling</div>
                <div style={{ 
                  width: '100%', 
                  height: '8px', 
                  backgroundColor: '#e5e7eb', 
                  borderRadius: '4px',
                  marginBottom: '8px'
                }}>
                  <div style={{ 
                    width: `${analysisResult.metrics.coupling}%`, 
                    height: '100%', 
                    backgroundColor: '#3b82f6',
                    borderRadius: '4px'
                  }} />
                </div>
                <div style={{ fontSize: '14px', fontWeight: '600' }}>
                  {analysisResult.metrics.coupling.toFixed(1)}/100
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Cohesion</div>
                <div style={{ 
                  width: '100%', 
                  height: '8px', 
                  backgroundColor: '#e5e7eb', 
                  borderRadius: '4px',
                  marginBottom: '8px'
                }}>
                  <div style={{ 
                    width: `${analysisResult.metrics.cohesion}%`, 
                    height: '100%', 
                    backgroundColor: '#10b981',
                    borderRadius: '4px'
                  }} />
                </div>
                <div style={{ fontSize: '14px', fontWeight: '600' }}>
                  {analysisResult.metrics.cohesion.toFixed(1)}/100
                </div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Code Smells</div>
                <div style={{ fontSize: '1.5rem', fontWeight: '700', color: '#ef4444' }}>
                  {analysisResult.metrics.codeSmells}
                </div>
              </div>
            </div>
          </div>

          {/* Code Hierarchy */}
          <div style={{ 
            border: '1px solid #e5e7eb', 
            borderRadius: '8px', 
            padding: '24px',
            backgroundColor: '#ffffff'
          }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '16px' }}>
              🔗 Code Hierarchy
            </h2>
            <div style={{ display: 'grid', gap: '16px' }}>
              {analysisResult.codeHierarchy.files.map((file, fileIndex) => (
                <div key={fileIndex} style={{ 
                  border: '1px solid #e5e7eb', 
                  borderRadius: '8px', 
                  padding: '16px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ 
                        padding: '2px 8px', 
                        backgroundColor: '#e5e7eb', 
                        borderRadius: '999px', 
                        fontSize: '12px' 
                      }}>
                        {file.type}
                      </span>
                      <span style={{ fontFamily: 'monospace', fontSize: '14px', color: '#374151' }}>
                        {file.path}
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: '#6b7280' }}>
                      {file.classes.length} classes, {file.functions.length} functions
                    </div>
                  </div>
                  
                  <hr style={{ border: 'none', borderTop: '1px solid #e5e7eb', margin: '12px 0' }} />
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    {file.classes.length > 0 && (
                      <div>
                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>Classes</h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {file.classes.map((cls, clsIndex) => (
                            <div key={clsIndex} style={{ borderLeft: '3px solid #3b82f6', paddingLeft: '8px' }}>
                              <div style={{ fontFamily: 'monospace', fontSize: '14px', color: '#374151' }}>
                                {cls.name} (line {cls.line})
                              </div>
                              {cls.methods.length > 0 && (
                                <div style={{ marginLeft: '12px', marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                  {cls.methods.map((method, methodIndex) => (
                                    <div key={methodIndex} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#6b7280' }}>
                                      <span>{method.name}</span>
                                      <span>Complexity: {method.complexity}</span>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {file.functions.length > 0 && (
                      <div>
                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>Functions</h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {file.functions.map((func, funcIndex) => (
                            <div key={funcIndex} style={{ borderLeft: '3px solid #10b981', paddingLeft: '8px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'monospace', fontSize: '14px', color: '#374151' }}>
                                <span>{func.name} (line {func.line})</span>
                                <span>Complexity: {func.complexity}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
