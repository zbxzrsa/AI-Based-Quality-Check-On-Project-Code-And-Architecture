/**
 * Unit tests for utility functions
 * Tests: cn, formatDate, formatRelativeTime, truncate, capitalize
 */

import { cn, formatDate, formatRelativeTime, truncate, capitalize } from '../utils';

describe('cn (className merger)', () => {
  it('should merge class names correctly', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('should handle conditional classes', () => {
    expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz');
  });

  it('should handle tailwind conflicts', () => {
    const result = cn('px-2', 'px-4');
    expect(result).toBe('px-4');
  });

  it('should handle empty inputs', () => {
    expect(cn()).toBe('');
  });

  it('should handle undefined and null', () => {
    expect(cn('foo', undefined, null, 'bar')).toBe('foo bar');
  });
});

describe('formatDate', () => {
  it('should format Date object correctly', () => {
    const date = new Date('2024-01-15T10:30:00Z');
    const formatted = formatDate(date);
    expect(formatted).toMatch(/Jan 15, 2024/);
  });

  it('should format date string correctly', () => {
    const formatted = formatDate('2024-01-15T10:30:00Z');
    expect(formatted).toMatch(/Jan 15, 2024/);
  });

  it('should include time in formatted output', () => {
    const date = new Date('2024-01-15T10:30:00Z');
    const formatted = formatDate(date);
    expect(formatted).toMatch(/\d{2}:\d{2}/);
  });
});

describe('formatRelativeTime', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2024-01-15T12:00:00Z'));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should return "just now" for recent times', () => {
    const date = new Date('2024-01-15T11:59:30Z');
    expect(formatRelativeTime(date)).toBe('just now');
  });

  it('should return minutes ago for times under 1 hour', () => {
    const date = new Date('2024-01-15T11:45:00Z');
    expect(formatRelativeTime(date)).toBe('15m ago');
  });

  it('should return hours ago for times under 24 hours', () => {
    const date = new Date('2024-01-15T10:00:00Z');
    expect(formatRelativeTime(date)).toBe('2h ago');
  });

  it('should return days ago for times under 7 days', () => {
    const date = new Date('2024-01-13T12:00:00Z');
    expect(formatRelativeTime(date)).toBe('2d ago');
  });

  it('should return formatted date for times over 7 days', () => {
    const date = new Date('2024-01-01T12:00:00Z');
    const result = formatRelativeTime(date);
    expect(result).toMatch(/Jan 1, 2024/);
  });

  it('should handle string dates', () => {
    const result = formatRelativeTime('2024-01-15T11:45:00Z');
    expect(result).toBe('15m ago');
  });
});

describe('truncate', () => {
  it('should truncate long strings', () => {
    const str = 'This is a very long string that needs truncation';
    expect(truncate(str, 20)).toBe('This is a very long ...');
  });

  it('should not truncate short strings', () => {
    const str = 'Short string';
    expect(truncate(str, 20)).toBe('Short string');
  });

  it('should handle exact length', () => {
    const str = 'Exactly twenty chars';
    expect(truncate(str, 20)).toBe('Exactly twenty chars');
  });

  it('should handle empty strings', () => {
    expect(truncate('', 10)).toBe('');
  });

  it('should handle zero length', () => {
    expect(truncate('test', 0)).toBe('...');
  });
});

describe('capitalize', () => {
  it('should capitalize first letter', () => {
    expect(capitalize('hello')).toBe('Hello');
  });

  it('should not affect already capitalized strings', () => {
    expect(capitalize('Hello')).toBe('Hello');
  });

  it('should handle single character', () => {
    expect(capitalize('a')).toBe('A');
  });

  it('should handle empty string', () => {
    expect(capitalize('')).toBe('');
  });

  it('should only capitalize first letter', () => {
    expect(capitalize('hello world')).toBe('Hello world');
  });

  it('should handle strings with numbers', () => {
    expect(capitalize('123abc')).toBe('123abc');
  });
});
