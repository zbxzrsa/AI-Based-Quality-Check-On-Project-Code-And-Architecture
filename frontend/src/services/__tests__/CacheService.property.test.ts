import * as fc from 'fast-check';
import { CacheService } from '../CacheService';

describe('Property 24: GETrequestcache', () => {
  describe('cache基本property', () => {
    it('对于任何键value对，set后立即getshouldreturn相同的data', () => {
      fc.assert(
        fc.property(
          fc.string({ minLength: 1 }),
          fc.anything(),
          (key: string, data: any) => {
            const cache = new CacheService();
            cache.set(key, data);
            const retrieved = cache.get(key);
            expect(retrieved).toEqual(data);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('对于任何键，在5min内的duplicategetshouldreturncachedata', () => {
      fc.assert(
        fc.property(
          fc.string({ minLength: 1 }),
          fc.anything(),
          fc.integer({ min: 1, max: 10 }),
          (key: string, data: any, repeatCount: number) => {
            const cache = new CacheService(5 * 60 * 1000);
            cache.set(key, data);
            for (let i = 0; i < repeatCount; i++) {
              const retrieved = cache.get(key);
              expect(retrieved).toEqual(data);
              expect(cache.has(key)).toBe(true);
            }
          }
        ),
        { numRuns: 100 }
      );
    });

    it('对于任何键，在TTL过期后getshouldreturnnull', async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.string({ minLength: 1 }),
          fc.anything(),
          fc.integer({ min: 50, max: 200 }),
          async (key: string, data: any, ttl: number) => {
            const cache = new CacheService();
            cache.set(key, data, ttl);
            await new Promise(resolve => setTimeout(resolve, ttl + 50));
            const retrieved = cache.get(key);
            expect(retrieved).toBeNull();
          }
        ),
        { numRuns: 50 }
      );
    });
  });

  describe('cache隔离property', () => {
    it('对于任何不同的键，cacheshould独立存储data', () => {
      fc.assert(
        fc.property(
          fc.array(
            fc.record({
              key: fc.string({ minLength: 1 }),
              data: fc.anything()
            }),
            { minLength: 2, maxLength: 20 }
          ),
          (entries: Array<{ key: string; data: any }>) => {
            const cache = new CacheService();
            const uniqueEntries = new Map(entries.map(e => [e.key, e.data]));
            uniqueEntries.forEach((data, key) => {
              cache.set(key, data);
            });
            uniqueEntries.forEach((expectedData, key) => {
              const retrieved = cache.get(key);
              expect(retrieved).toEqual(expectedData);
            });
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  describe('cache统计property', () => {
    it('对于任何操作序列，命中数and未命中数之andshould等于总request数', () => {
      fc.assert(
        fc.property(
          fc.array(
            fc.record({
              operation: fc.constantFrom('set', 'get'),
              key: fc.string({ minLength: 1, maxLength: 10 }),
              data: fc.anything()
            }),
            { minLength: 1, maxLength: 50 }
          ),
          (operations: Array<{ operation: 'set' | 'get'; key: string; data: any }>) => {
            const cache = new CacheService();
            let expectedGets = 0;
            operations.forEach(op => {
              if (op.operation === 'set') {
                cache.set(op.key, op.data);
              } else {
                cache.get(op.key);
                expectedGets++;
              }
            });
            const stats = cache.getStats();
            expect(stats.hits + stats.misses).toBe(expectedGets);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('对于任何cachestatus，命中率shouldBeAt0到100之间', () => {
      fc.assert(
        fc.property(
          fc.array(
            fc.record({
              operation: fc.constantFrom('set', 'get'),
              key: fc.string({ minLength: 1, maxLength: 10 }),
              data: fc.anything()
            }),
            { minLength: 1, maxLength: 50 }
          ),
          (operations: Array<{ operation: 'set' | 'get'; key: string; data: any }>) => {
            const cache = new CacheService();
            operations.forEach(op => {
              if (op.operation === 'set') {
                cache.set(op.key, op.data);
              } else {
                cache.get(op.key);
              }
            });
            const stats = cache.getStats();
            expect(stats.hitRate).toBeGreaterThanOrEqual(0);
            expect(stats.hitRate).toBeLessThanOrEqual(100);
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  describe('cachecleanupproperty', () => {
    it('对于任何cachestatus，clear()should清空所有cache', () => {
      fc.assert(
        fc.property(
          fc.array(
            fc.record({
              key: fc.string({ minLength: 1 }),
              data: fc.anything()
            }),
            { minLength: 1, maxLength: 30 }
          ),
          (entries: Array<{ key: string; data: any }>) => {
            const cache = new CacheService();
            entries.forEach(({ key, data }) => {
              cache.set(key, data);
            });
            cache.clear();
            const stats = cache.getStats();
            expect(stats.size).toBe(0);
            expect(stats.keys.length).toBe(0);
            entries.forEach(({ key }) => {
              expect(cache.get(key)).toBeNull();
            });
          }
        ),
        { numRuns: 100 }
      );
    });

    it('对于任何模式，clear(pattern)should只清除匹配的键', () => {
      fc.assert(
        fc.property(
          fc.string({ minLength: 1, maxLength: 5 }),
          fc.array(
            fc.record({
              key: fc.string({ minLength: 1, maxLength: 20 }),
              data: fc.anything()
            }),
            { minLength: 1, maxLength: 20 }
          ),
          (pattern: string, entries: Array<{ key: string; data: any }>) => {
            const cache = new CacheService();
            const uniqueEntries = new Map(entries.map(e => [e.key, e.data]));
            uniqueEntries.forEach((data, key) => {
              cache.set(key, data);
            });
            cache.clear(pattern);
            uniqueEntries.forEach((data, key) => {
              const retrieved = cache.get(key);
              if (key.includes(pattern)) {
                expect(retrieved).toBeNull();
              } else {
                expect(retrieved).toEqual(data);
              }
            });
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
