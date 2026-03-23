'use client';

import React, { useRef, useState, useEffect, useCallback, CSSProperties } from 'react';

export interface VirtualListProps<T> {
  items: T[];
  height: number;
  itemHeight?: number | ((item: T, index: number) => number);
  overscan?: number;
  renderItem: (item: T, index: number) => React.ReactNode;
  className?: string;
  onScroll?: (scrollTop: number) => void;
}

interface ItemPosition {
  index: number;
  top: number;
  height: number;
}

export function VirtualList<T>({
  items,
  height,
  itemHeight = 50,
  overscan = 3,
  renderItem,
  className = '',
  onScroll,
}: VirtualListProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [measuredHeights, setMeasuredHeights] = useState<Map<number, number>>(new Map());

  // Calculate item positions based on measured or estimated heights
  const itemPositions = React.useMemo<ItemPosition[]>(() => {
    const positions: ItemPosition[] = [];
    let currentTop = 0;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      let itemHeightValue: number;

      // Get the base height estimate
      const baseHeight = typeof itemHeight === 'function' ? itemHeight(item, i) : itemHeight;
      
      // Use measured height if available and valid, otherwise use base height
      const measured = measuredHeights.get(i);
      itemHeightValue = (measured && measured > 0) ? measured : baseHeight;

      positions.push({
        index: i,
        top: currentTop,
        height: itemHeightValue,
      });

      currentTop += itemHeightValue;
    }

    return positions;
  }, [items, itemHeight, measuredHeights]);

  const totalHeight = itemPositions.length > 0 
    ? itemPositions[itemPositions.length - 1].top + itemPositions[itemPositions.length - 1].height 
    : 0;

  // Binary search to find the first visible item
  const findStartIndex = useCallback((scrollTop: number): number => {
    if (itemPositions.length === 0) return 0;
    
    let left = 0;
    let right = itemPositions.length - 1;

    while (left < right) {
      const mid = Math.floor((left + right) / 2);
      if (itemPositions[mid].top + itemPositions[mid].height <= scrollTop) {
        left = mid + 1;
      } else {
        right = mid;
      }
    }

    return Math.max(0, left - overscan);
  }, [itemPositions, overscan]);

  // Find the last visible item
  const findEndIndex = useCallback((scrollTop: number, viewportHeight: number): number => {
    if (itemPositions.length === 0) return 0;
    
    const scrollBottom = scrollTop + viewportHeight;
    
    // Find the last item whose top is less than scrollBottom
    for (let i = itemPositions.length - 1; i >= 0; i--) {
      if (itemPositions[i].top < scrollBottom) {
        return Math.min(itemPositions.length - 1, i + overscan);
      }
    }
    
    return Math.min(itemPositions.length - 1, overscan);
  }, [itemPositions, overscan]);

  const startIndex = itemPositions.length > 0 ? findStartIndex(scrollTop) : 0;
  const endIndex = itemPositions.length > 0 ? findEndIndex(scrollTop, height) : 0;

  const visibleItems = itemPositions.length > 0 ? itemPositions.slice(startIndex, endIndex + 1) : [];

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const newScrollTop = e.currentTarget.scrollTop;
    setScrollTop(newScrollTop);
    onScroll?.(newScrollTop);
  }, [onScroll]);

  // Measure item heights for dynamic sizing
  const measureItem = useCallback((index: number, element: HTMLElement | null) => {
    if (!element) return;

    const rect = element.getBoundingClientRect();
    const measuredHeight = rect.height;
    
    // Only update if we got a valid measurement
    if (measuredHeight > 0) {
      setMeasuredHeights(prev => {
        if (prev.get(index) === measuredHeight) return prev;
        const next = new Map(prev);
        next.set(index, measuredHeight);
        return next;
      });
    }
  }, []);

  const containerStyle: CSSProperties = {
    height: `${height}px`,
    overflow: 'auto',
    position: 'relative',
  };

  const innerStyle: CSSProperties = {
    height: `${totalHeight}px`,
    position: 'relative',
  };

  return (
    <div
      ref={containerRef}
      className={className}
      style={containerStyle}
      onScroll={handleScroll}
      data-testid="virtual-list-container"
    >
      <div style={innerStyle} data-testid="virtual-list-inner">
        {visibleItems.map(({ index, top, height: estimatedHeight }) => {
          const item = items[index];
          return (
            <div
              key={index}
              ref={el => measureItem(index, el)}
              style={{
                position: 'absolute',
                top: `${top}px`,
                left: 0,
                right: 0,
                minHeight: `${estimatedHeight}px`,
              }}
              data-index={index}
            >
              {renderItem(item, index)}
            </div>
          );
        })}
      </div>
    </div>
  );
}
