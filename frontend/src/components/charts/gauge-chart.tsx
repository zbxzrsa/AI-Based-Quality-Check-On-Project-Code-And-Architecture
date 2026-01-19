'use client';

import { Card } from '@/components/ui/card';

interface GaugeChartProps {
  value: number;
  max?: number;
  title: string;
  subtitle?: string;
  color?: string;
}

export default function GaugeChart({
  value,
  max = 100,
  title,
  subtitle,
  color = '#3b82f6',
}: GaugeChartProps) {
  const percentage = (value / max) * 100;
  const circumference = 2 * Math.PI * 40;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  const getColor = () => {
    if (percentage >= 80) return '#22c55e'; // green
    if (percentage >= 60) return '#eab308'; // yellow
    if (percentage >= 40) return '#f97316'; // orange
    return '#ef4444'; // red
  };

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <div className="flex flex-col items-center">
        <div className="relative w-40 h-40">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
            {/* Background circle */}
            <circle
              cx="50"
              cy="50"
              r="40"
              fill="none"
              stroke="currentColor"
              strokeWidth="8"
              className="text-muted opacity-20"
            />
            {/* Progress circle */}
            <circle
              cx="50"
              cy="50"
              r="40"
              fill="none"
              stroke={getColor()}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className="transition-all duration-1000 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-4xl font-bold">{value}</span>
            <span className="text-sm text-muted-foreground">/ {max}</span>
          </div>
        </div>
        {subtitle && (
          <p className="text-sm text-muted-foreground mt-4 text-center">
            {subtitle}
          </p>
        )}
      </div>
    </Card>
  );
}
