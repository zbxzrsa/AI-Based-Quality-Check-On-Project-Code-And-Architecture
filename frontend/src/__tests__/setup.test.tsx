/**
 * Basic setup test to verify Jest configuration
 */

describe('Jest Setup Verification', () => {
  it('should have environment variables configured', () => {
    expect(process.env.NEXT_PUBLIC_API_URL).toBeDefined();
    expect(process.env.NEXT_PUBLIC_APP_ENV).toBeDefined();
  });

  it('should have localStorage mocked', () => {
    expect(localStorage.getItem).toBeDefined();
    expect(localStorage.setItem).toBeDefined();
    expect(localStorage.removeItem).toBeDefined();
    expect(localStorage.clear).toBeDefined();
  });

  it('should have window.location mocked', () => {
    expect(window.location.href).toBe('http://localhost:3000');
    expect(window.location.reload).toBeDefined();
  });

  it('should have window.matchMedia mocked', () => {
    const mq = window.matchMedia('(max-width: 600px)');
    expect(mq.matches).toBe(false);
    expect(mq.addEventListener).toBeDefined();
  });

  it('should have fetch mocked', () => {
    expect(fetch).toBeDefined();
    expect(typeof fetch).toBe('function');
  });

  it('should have custom matchers', () => {
    expect(expect).toHaveProperty('toHaveAttribute');
    expect(expect).toHaveProperty('toHaveClass');
    expect(expect).toHaveProperty('toBeVisible');
  });

  it('should have DOM mocks', () => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    expect(ctx).toBeDefined();
    expect(typeof ctx?.fillRect).toBe('function');
  });

  it('should have SVG mocks', () => {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    const bbox = svg.getBBox();
    expect(bbox).toHaveProperty('x');
    expect(bbox).toHaveProperty('y');
    expect(bbox).toHaveProperty('width');
    expect(bbox).toHaveProperty('height');
  });
});
