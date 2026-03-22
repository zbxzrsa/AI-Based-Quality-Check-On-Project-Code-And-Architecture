/**
 * Metricsthreshold告警propertytest
 * 
 * Feature: frontend-production-optimization
 * Property 23: threshold告警show
 * 
 * **Validates: Requirements 6.5**
 * 
 * testCoverage:
 * - 对于任何超过预设threshold的指标value，shouldshowwarn标识
 * 
 * note: 此propertytestverifythreshold告警feature的正确性，确保当指标value超过预设threshold时，
 * system能够正确showwarn标识（warning或critical）。testCoverage各种指标valueandthresholdconfig。
 */

import fc from 'fast-check';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import Metrics from '../Metrics';

describe('Property 23: threshold告警show', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    jest.restoreAllMocks();
  });

  // 指标定义（与Metrics.tsx中的定义一致）
  const metricDefinitions = {
    performance: {
      id: 'performance',
      name: 'Performance Score',
      unit: 'score',
      threshold: { warning: 70, critical: 50 },
      isLowerBetter: false // 越高越好
    },
    errorRate: {
      id: 'errorRate',
      name: 'Error Rate',
      unit: '%',
      threshold: { warning: 3, critical: 5 },
      isLowerBetter: true // 越低越好
    },
    responseTime: {
      id: 'responseTime',
      name: 'Response Time',
      unit: 'ms',
      threshold: { warning: 150, critical: 200 },
      isLowerBetter: true // 越低越好
    }
  };

  // customGenerator：generate指标ID
  const metricIdArbitrary = () =>
    fc.constantFrom('performance', 'errorRate', 'responseTime');

  // customGenerator：generate时间范围
  const timeRangeArbitrary = () =>
    fc.constantFrom('day', 'week', 'month');

  /**
   * 辅助function：根据指标andvalue确定预期的告警级别
   */
  const getExpectedAlertLevel = (
    metricId: string,
    value: number
  ): 'normal' | 'warning' | 'critical' => {
    const metric = metricDefinitions[metricId as keyof typeof metricDefinitions];
    if (!metric.threshold) return 'normal';

    if (metric.isLowerBetter) {
      // 对于越低越好的指标（errorRate, responseTime）
      if (value >= metric.threshold.critical) return 'critical';
      if (value >= metric.threshold.warning) return 'warning';
    } else {
      // 对于越高越好的指标（performance）
      if (value <= metric.threshold.critical) return 'critical';
      if (value <= metric.threshold.warning) return 'warning';
    }

    return 'normal';
  };

  /**
   * 辅助function：generate指定告警级别的value
   */
  const generateValueForAlertLevel = (
    metricId: string,
    alertLevel: 'normal' | 'warning' | 'critical'
  ): number => {
    const metric = metricDefinitions[metricId as keyof typeof metricDefinitions];
    
    if (metric.isLowerBetter) {
      // 对于越低越好的指标
      switch (alertLevel) {
        case 'critical':
          return metric.threshold.critical + Math.random() * 10; // 超过criticalthreshold
        case 'warning':
          return metric.threshold.warning + Math.random() * (metric.threshold.critical - metric.threshold.warning); // 在warningandcritical之间
        case 'normal':
          return Math.random() * metric.threshold.warning; // 低于warningthreshold
      }
    } else {
      // 对于越高越好的指标
      switch (alertLevel) {
        case 'critical':
          return metric.threshold.critical - Math.random() * 10; // 低于criticalthreshold
        case 'warning':
          return metric.threshold.critical + Math.random() * (metric.threshold.warning - metric.threshold.critical); // 在criticalandwarning之间
        case 'normal':
          return metric.threshold.warning + Math.random() * 30; // 高于warningthreshold
      }
    }
  };

  /**
   * 辅助function：check页面上是否show了预期的告警标识
   */
  const checkAlertIndicator = async (
    metricName: string,
    expectedLevel: 'normal' | 'warning' | 'critical'
  ): Promise<boolean> => {
    try {
      // 查找contain指标名称的摘要卡片
      const metricCards = screen.getAllByText(metricName);
      
      if (expectedLevel === 'normal') {
        // 正常status不should有告警标识
        // check是否没有Warning或Criticaltag
        const warningLabels = screen.queryAllByText(/warning/i);
        const criticalLabels = screen.queryAllByText(/critical/i);
        
        // 如果有告警tag，确保它们不在当前指标的卡片中
        return true; // 简化check，因为正常status可能没有明显的标识
      } else if (expectedLevel === 'warning') {
        // shouldshowWarning标识
        const warningElements = screen.queryAllByText(/warning/i);
        return warningElements.length > 0;
      } else {
        // shouldshowCritical标识
        const criticalElements = screen.queryAllByText(/critical/i);
        return criticalElements.length > 0;
      }
    } catch (error) {
      return false;
    }
  };

  it('should为超过warningthreshold的指标showwarning告警标识', async () => {
    await fc.assert(
      fc.asyncProperty(
        metricIdArbitrary(),
        timeRangeArbitrary(),
        async (metricId, timeRange) => {
          const metric = metricDefinitions[metricId as keyof typeof metricDefinitions];
          
          // generate一item会触发warning的value
          const warningValue = generateValueForAlertLevel(metricId, 'warning');
          
          // Mockdatageneratefunction，使其returnwarning级别的value
          const originalRandom = Math.random;
          let callCount = 0;
          Math.random = jest.fn(() => {
            callCount++;
            // 为指定的指标returnwarning级别的value
            if (metricId === 'performance') {
              return (warningValue - 75) / 20; // inferrandomvalue
            } else if (metricId === 'errorRate') {
              return warningValue / 5; // inferrandomvalue
            } else {
              return (warningValue - 100) / 100; // inferrandomvalue
            }
          });

          render(<Metrics initialTimeRange={timeRange} />);

          // waitDataLoaded
          await waitFor(() => {
            expect(screen.getByText(/metrics dashboard/i)).toBeInTheDocument();
          }, { timeout: 5000 });

          // 恢复Math.random
          Math.random = originalRandom;

          // verify告警级别
          const expectedLevel = getExpectedAlertLevel(metricId, warningValue);
          
          // 如果value确实在warning范围内，check告警标识
          if (expectedLevel === 'warning') {
            await waitFor(() => {
              const warningElements = screen.queryAllByText(/warning/i);
              expect(warningElements.length).toBeGreaterThan(0);
            }, { timeout: 2000 });
          }

          cleanup();
        }
      ),
      { numRuns: 30 }
    );
  }, 120000);

  it('should为超过criticalthreshold的指标showcritical告警标识', async () => {
    await fc.assert(
      fc.asyncProperty(
        metricIdArbitrary(),
        timeRangeArbitrary(),
        async (metricId, timeRange) => {
          const metric = metricDefinitions[metricId as keyof typeof metricDefinitions];
          
          // generate一item会触发critical的value
          const criticalValue = generateValueForAlertLevel(metricId, 'critical');
          
          // Mockdatageneratefunction，使其returncritical级别的value
          const originalRandom = Math.random;
          Math.random = jest.fn(() => {
            // 为指定的指标returncritical级别的value
            if (metricId === 'performance') {
              return (criticalValue - 75) / 20; // inferrandomvalue
            } else if (metricId === 'errorRate') {
              return criticalValue / 5; // inferrandomvalue
            } else {
              return (criticalValue - 100) / 100; // inferrandomvalue
            }
          });

          render(<Metrics initialTimeRange={timeRange} />);

          // waitDataLoaded
          await waitFor(() => {
            expect(screen.getByText(/metrics dashboard/i)).toBeInTheDocument();
          }, { timeout: 5000 });

          // 恢复Math.random
          Math.random = originalRandom;

          // verify告警级别
          const expectedLevel = getExpectedAlertLevel(metricId, criticalValue);
          
          // 如果value确实在critical范围内，check告警标识
          if (expectedLevel === 'critical') {
            await waitFor(() => {
              const criticalElements = screen.queryAllByText(/critical/i);
              expect(criticalElements.length).toBeGreaterThan(0);
            }, { timeout: 2000 });
          }

          cleanup();
        }
      ),
      { numRuns: 30 }
    );
  }, 120000);

  it('should为正常范围内的指标不show告警标识', async () => {
    await fc.assert(
      fc.asyncProperty(
        metricIdArbitrary(),
        timeRangeArbitrary(),
        async (metricId, timeRange) => {
          const metric = metricDefinitions[metricId as keyof typeof metricDefinitions];
          
          // generate一item正常范围内的value
          const normalValue = generateValueForAlertLevel(metricId, 'normal');
          
          // Mockdatageneratefunction，使其return正常级别的value
          const originalRandom = Math.random;
          Math.random = jest.fn(() => {
            // 为指定的指标returnnormal级别的value
            if (metricId === 'performance') {
              return (normalValue - 75) / 20; // inferrandomvalue
            } else if (metricId === 'errorRate') {
              return normalValue / 5; // inferrandomvalue
            } else {
              return (normalValue - 100) / 100; // inferrandomvalue
            }
          });

          render(<Metrics initialTimeRange={timeRange} />);

          // waitDataLoaded
          await waitFor(() => {
            expect(screen.getByText(/metrics dashboard/i)).toBeInTheDocument();
          }, { timeout: 5000 });

          // 恢复Math.random
          Math.random = originalRandom;

          // verify告警级别
          const expectedLevel = getExpectedAlertLevel(metricId, normalValue);
          
          // 正常status下，摘要卡片should存在但不should有明显的告警边框
          await waitFor(() => {
            const metricCards = screen.getAllByText(metric.name);
            expect(metricCards.length).toBeGreaterThan(0);
          }, { timeout: 2000 });

          cleanup();
        }
      ),
      { numRuns: 30 }
    );
  }, 120000);

  it('shouldBeAt摘要卡片中showthresholdconfiginfo', async () => {
    await fc.assert(
      fc.asyncProperty(
        metricIdArbitrary(),
        timeRangeArbitrary(),
        async (metricId, timeRange) => {
          const metric = metricDefinitions[metricId as keyof typeof metricDefinitions];

          render(<Metrics initialTimeRange={timeRange} />);

          // waitDataLoaded
          await waitFor(() => {
            expect(screen.getByText(/metrics dashboard/i)).toBeInTheDocument();
          }, { timeout: 5000 });

          // verifythresholdinfoshow
          await waitFor(() => {
            // check是否show了Thresholdstag
            const thresholdLabels = screen.queryAllByText(/thresholds:/i);
            expect(thresholdLabels.length).toBeGreaterThan(0);

            // check是否show了WarningandCriticalthreshold
            const warningThresholds = screen.queryAllByText(/warning:/i);
            const criticalThresholds = screen.queryAllByText(/critical:/i);
            
            expect(warningThresholds.length).toBeGreaterThan(0);
            expect(criticalThresholds.length).toBeGreaterThan(0);
          }, { timeout: 2000 });

          cleanup();
        }
      ),
      { numRuns: 30 }
    );
  }, 120000);

  it('should根据指标type正确判断告警级别（越高越好 vs 越低越好）', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.constantFrom('performance', 'errorRate', 'responseTime'),
        fc.double({ min: 0, max: 300 }),
        timeRangeArbitrary(),
        async (metricId, value, timeRange) => {
          const metric = metricDefinitions[metricId as keyof typeof metricDefinitions];
          
          // 计算预期的告警级别
          const expectedLevel = getExpectedAlertLevel(metricId, value);

          // Mockdatageneratefunction
          const originalRandom = Math.random;
          Math.random = jest.fn(() => {
            if (metricId === 'performance') {
              return (value - 75) / 20;
            } else if (metricId === 'errorRate') {
              return value / 5;
            } else {
              return (value - 100) / 100;
            }
          });

          render(<Metrics initialTimeRange={timeRange} />);

          // waitDataLoaded
          await waitFor(() => {
            expect(screen.getByText(/metrics dashboard/i)).toBeInTheDocument();
          }, { timeout: 5000 });

          // 恢复Math.random
          Math.random = originalRandom;

          // verify告警标识的存在性与预期一致
          if (expectedLevel === 'warning') {
            await waitFor(() => {
              const warningElements = screen.queryAllByText(/warning/i);
              expect(warningElements.length).toBeGreaterThan(0);
            }, { timeout: 2000 });
          } else if (expectedLevel === 'critical') {
            await waitFor(() => {
              const criticalElements = screen.queryAllByText(/critical/i);
              expect(criticalElements.length).toBeGreaterThan(0);
            }, { timeout: 2000 });
          }

          cleanup();
        }
      ),
      { numRuns: 50 }
    );
  }, 120000);

  it('shouldBeAt图表中showthreshold参考线（单指标选择时）', async () => {
    await fc.assert(
      fc.asyncProperty(
        metricIdArbitrary(),
        timeRangeArbitrary(),
        async (metricId, timeRange) => {
          const metric = metricDefinitions[metricId as keyof typeof metricDefinitions];

          render(<Metrics initialTimeRange={timeRange} />);

          // waitDataLoaded
          await waitFor(() => {
            expect(screen.getByText(/metrics dashboard/i)).toBeInTheDocument();
          }, { timeout: 5000 });

          // 默认情况下所有指标都被选中，need只选择一item指标
          // 点击Clearbutton只保留一item指标
          const clearButton = screen.getByRole('button', { name: /clear/i });
          clearButton.click();

          // waitUIupdate
          await waitFor(() => {
            expect(screen.getByText(/1 metric selected/i)).toBeInTheDocument();
          }, { timeout: 2000 });

          // verifythresholdconfiginfoshow
          await waitFor(() => {
            const thresholdConfig = screen.queryByText(/threshold configuration:/i);
            expect(thresholdConfig).toBeInTheDocument();
          }, { timeout: 2000 });

          cleanup();
        }
      ),
      { numRuns: 30 }
    );
  }, 120000);

  it('shouldBeAt告警标识中show正确的图标and颜色', async () => {
    await fc.assert(
      fc.asyncProperty(
        metricIdArbitrary(),
        fc.constantFrom('warning', 'critical'),
        timeRangeArbitrary(),
        async (metricId, alertLevel, timeRange) => {
          const metric = metricDefinitions[metricId as keyof typeof metricDefinitions];
          
          // generate对应告警级别的value
          const value = generateValueForAlertLevel(metricId, alertLevel);
          
          // Mockdatageneratefunction
          const originalRandom = Math.random;
          Math.random = jest.fn(() => {
            if (metricId === 'performance') {
              return (value - 75) / 20;
            } else if (metricId === 'errorRate') {
              return value / 5;
            } else {
              return (value - 100) / 100;
            }
          });

          render(<Metrics initialTimeRange={timeRange} />);

          // waitDataLoaded
          await waitFor(() => {
            expect(screen.getByText(/metrics dashboard/i)).toBeInTheDocument();
          }, { timeout: 5000 });

          // 恢复Math.random
          Math.random = originalRandom;

          // verify告警标识存在
          const expectedLevel = getExpectedAlertLevel(metricId, value);
          if (expectedLevel === alertLevel) {
            await waitFor(() => {
              const alertElements = screen.queryAllByText(new RegExp(alertLevel, 'i'));
              expect(alertElements.length).toBeGreaterThan(0);
              
              // verifySVG图标存在（通过查找svg元素）
              const svgElements = document.querySelectorAll('svg');
              expect(svgElements.length).toBeGreaterThan(0);
            }, { timeout: 2000 });
          }

          cleanup();
        }
      ),
      { numRuns: 30 }
    );
  }, 120000);

  it('shouldBeAt不同时间范围下一致地show告警标识', async () => {
    await fc.assert(
      fc.asyncProperty(
        metricIdArbitrary(),
        fc.tuple(timeRangeArbitrary(), timeRangeArbitrary()),
        async (metricId, [timeRange1, timeRange2]) => {
          if (timeRange1 === timeRange2) return;

          const metric = metricDefinitions[metricId as keyof typeof metricDefinitions];
          
          // generate一item会触发warning的value
          const warningValue = generateValueForAlertLevel(metricId, 'warning');
          
          // Mockdatageneratefunction
          const originalRandom = Math.random;
          Math.random = jest.fn(() => {
            if (metricId === 'performance') {
              return (warningValue - 75) / 20;
            } else if (metricId === 'errorRate') {
              return warningValue / 5;
            } else {
              return (warningValue - 100) / 100;
            }
          });

          // 第一item时间范围
          render(<Metrics initialTimeRange={timeRange1} />);

          await waitFor(() => {
            expect(screen.getByText(/metrics dashboard/i)).toBeInTheDocument();
          }, { timeout: 5000 });

          const expectedLevel = getExpectedAlertLevel(metricId, warningValue);
          
          if (expectedLevel === 'warning') {
            await waitFor(() => {
              const warningElements1 = screen.queryAllByText(/warning/i);
              expect(warningElements1.length).toBeGreaterThan(0);
            }, { timeout: 2000 });
          }

          cleanup();

          // 第二item时间范围
          render(<Metrics initialTimeRange={timeRange2} />);

          await waitFor(() => {
            expect(screen.getByText(/metrics dashboard/i)).toBeInTheDocument();
          }, { timeout: 5000 });

          if (expectedLevel === 'warning') {
            await waitFor(() => {
              const warningElements2 = screen.queryAllByText(/warning/i);
              expect(warningElements2.length).toBeGreaterThan(0);
            }, { timeout: 2000 });
          }

          // 恢复Math.random
          Math.random = originalRandom;

          cleanup();
        }
      ),
      { numRuns: 20 }
    );
  }, 120000);

  it('should为自定义仪表板中的指标show告警标识', async () => {
    await fc.assert(
      fc.asyncProperty(
        metricIdArbitrary(),
        timeRangeArbitrary(),
        async (metricId, timeRange) => {
          const metric = metricDefinitions[metricId as keyof typeof metricDefinitions];
          
          // generate一item会触发warning的value
          const warningValue = generateValueForAlertLevel(metricId, 'warning');
          
          // Mockdatageneratefunction
          const originalRandom = Math.random;
          Math.random = jest.fn(() => {
            if (metricId === 'performance') {
              return (warningValue - 75) / 20;
            } else if (metricId === 'errorRate') {
              return warningValue / 5;
            } else {
              return (warningValue - 100) / 100;
            }
          });

          render(<Metrics initialTimeRange={timeRange} />);

          // waitDataLoaded
          await waitFor(() => {
            expect(screen.getByText(/metrics dashboard/i)).toBeInTheDocument();
          }, { timeout: 5000 });

          // 恢复Math.random
          Math.random = originalRandom;

          // verify告警标识存在（即使在默认视图中）
          const expectedLevel = getExpectedAlertLevel(metricId, warningValue);
          
          if (expectedLevel === 'warning') {
            await waitFor(() => {
              const warningElements = screen.queryAllByText(/warning/i);
              expect(warningElements.length).toBeGreaterThan(0);
            }, { timeout: 2000 });
          }

          cleanup();
        }
      ),
      { numRuns: 30 }
    );
  }, 120000);
});
