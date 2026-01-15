'use client';

/**
 * Architecture Evolution Timeline using D3.js
 */
import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface TimelineDataPoint {
    date: Date;
    coupling: number;
    complexity: number;
    coverage: number;
    loc: number;
}

interface TimelineEvent {
    date: Date;
    label: string;
    type: 'release' | 'refactor' | 'migration';
}

interface ArchitectureTimelineProps {
    data: TimelineDataPoint[];
    events?: TimelineEvent[];
    width?: number;
    height?: number;
}

export default function ArchitectureTimeline({
    data,
    events = [],
    width = 1000,
    height = 400,
}: ArchitectureTimelineProps) {
    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!svgRef.current || data.length === 0) return;

        // Clear previous content
        d3.select(svgRef.current).selectAll('*').remove();

        const margin = { top: 20, right: 120, bottom: 60, left: 60 };
        const innerWidth = width - margin.left - margin.right;
        const innerHeight = height - margin.top - margin.bottom;

        const svg = d3
            .select(svgRef.current)
            .attr('width', width)
            .attr('height', height)
            .attr('viewBox', `0 0 ${width} ${height}`)
            .attr('preserveAspectRatio', 'xMidYMid meet');

        const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

        // Scales
        const xScale = d3
            .scaleTime()
            .domain(d3.extent(data, (d) => d.date) as [Date, Date])
            .range([0, innerWidth]);

        const yScale = d3
            .scaleLinear()
            .domain([0, d3.max(data, (d) => Math.max(d.complexity, d.coupling, d.coverage, d.loc / 100)) || 100])
            .nice()
            .range([innerHeight, 0]);

        // Axes
        const xAxis = d3.axisBottom(xScale).ticks(6).tickFormat(d3.timeFormat('%b %Y') as any);
        const yAxis = d3.axisLeft(yScale);

        g.append('g')
            .attr('class', 'x-axis')
            .attr('transform', `translate(0,${innerHeight})`)
            .call(xAxis)
            .selectAll('text')
            .style('fill', 'currentColor');

        g.append('g').attr('class', 'y-axis').call(yAxis).selectAll('text').style('fill', 'currentColor');

        // Grid lines
        g.append('g')
            .attr('class', 'grid')
            .attr('opacity', 0.1)
            .call(d3.axisLeft(yScale).tickSize(-innerWidth).tickFormat('' as any));

        // Line generators
        const lineGenerators = {
            coupling: d3
                .line<TimelineDataPoint>()
                .x((d) => xScale(d.date))
                .y((d) => yScale(d.coupling))
                .curve(d3.curveMonotoneX),
            complexity: d3
                .line<TimelineDataPoint>()
                .x((d) => xScale(d.date))
                .y((d) => yScale(d.complexity))
                .curve(d3.curveMonotoneX),
            coverage: d3
                .line<TimelineDataPoint>()
                .x((d) => xScale(d.date))
                .y((d) => yScale(d.coverage))
                .curve(d3.curveMonotoneX),
            loc: d3
                .line<TimelineDataPoint>()
                .x((d) => xScale(d.date))
                .y((d) => yScale(d.loc / 100))
                .curve(d3.curveMonotoneX),
        };

        const metrics = [
            { key: 'coupling', color: '#ef4444', label: 'Coupling Score' },
            { key: 'complexity', color: '#f59e0b', label: 'Complexity' },
            { key: 'coverage', color: '#10b981', label: 'Test Coverage' },
            { key: 'loc', color: '#3b82f6', label: 'LOC (÷100)' },
        ];

        // Draw lines
        metrics.forEach((metric) => {
            g.append('path')
                .datum(data)
                .attr('class', `line-${metric.key}`)
                .attr('fill', 'none')
                .attr('stroke', metric.color)
                .attr('stroke-width', 2)
                .attr('d', lineGenerators[metric.key as keyof typeof lineGenerators]);
        });

        // Add dots
        metrics.forEach((metric) => {
            g.selectAll(`.dot-${metric.key}`)
                .data(data)
                .enter()
                .append('circle')
                .attr('class', `dot-${metric.key}`)
                .attr('cx', (d) => xScale(d.date))
                .attr('cy', (d) => yScale(d[metric.key as keyof TimelineDataPoint] as number || 0))
                .attr('r', 3)
                .attr('fill', metric.color)
                .style('cursor', 'pointer')
                .on('mouseover', function (event, d: any) {
                    d3.select(this).attr('r', 5);

                    // Tooltip
                    const tooltip = g
                        .append('g')
                        .attr('class', 'tooltip')
                        .attr('transform', `translate(${xScale(d.date)},${yScale(d[metric.key]) - 40})`);

                    tooltip
                        .append('rect')
                        .attr('x', -60)
                        .attr('y', -25)
                        .attr('width', 120)
                        .attr('height', 30)
                        .attr('fill', 'rgba(0,0,0,0.8)')
                        .attr('rx', 4);

                    tooltip
                        .append('text')
                        .attr('text-anchor', 'middle')
                        .attr('fill', 'white')
                        .attr('font-size', '12px')
                        .text(`${metric.label}: ${d[metric.key]}`);
                })
                .on('mouseout', function () {
                    d3.select(this).attr('r', 3);
                    g.selectAll('.tooltip').remove();
                });
        });

        // Event markers
        events.forEach((event) => {
            const x = xScale(event.date);

            g.append('line')
                .attr('x1', x)
                .attr('x2', x)
                .attr('y1', 0)
                .attr('y2', innerHeight)
                .attr('stroke', event.type === 'release' ? '#8b5cf6' : '#6366f1')
                .attr('stroke-width', 2)
                .attr('stroke-dasharray', '4,4')
                .attr('opacity', 0.5);

            g.append('text')
                .attr('x', x)
                .attr('y', -5)
                .attr('text-anchor', 'middle')
                .attr('font-size', '10px')
                .attr('fill', 'currentColor')
                .text(event.label);
        });

        // Legend
        const legend = g
            .append('g')
            .attr('class', 'legend')
            .attr('transform', `translate(${innerWidth + 10}, 0)`);

        metrics.forEach((metric, i) => {
            const legendRow = legend.append('g').attr('transform', `translate(0, ${i * 20})`);

            legendRow.append('line').attr('x1', 0).attr('x2', 20).attr('stroke', metric.color).attr('stroke-width', 2);

            legendRow
                .append('text')
                .attr('x', 25)
                .attr('y', 4)
                .attr('font-size', '12px')
                .attr('fill', 'currentColor')
                .text(metric.label);
        });

        // Brush for date range selection
        const brush = d3
            .brushX()
            .extent([
                [0, 0],
                [innerWidth, innerHeight],
            ])
            .on('end', (event) => {
                if (event.selection) {
                    const [x0, x1] = event.selection;
                    const dateRange = [xScale.invert(x0), xScale.invert(x1)];
                    console.log('Selected date range:', dateRange);
                }
            });

        g.append('g').attr('class', 'brush').call(brush);
    }, [data, events, width, height]);

    return (
        <div ref={containerRef} className="w-full overflow-x-auto">
            <svg ref={svgRef} className="text-gray-700 dark:text-gray-300" />
        </div>
    );
}
