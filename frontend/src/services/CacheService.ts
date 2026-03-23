/**
 * CacheService - requestcache管理service
 * 
 * feature:
 * - setandgetcachedata
 * - support自定义TTL (Time To Live)
 * - 自动过期checkandcleanup
 * - cache统计feature (命中率、大小等)
 * - support模式匹配的cache清除
 * 
 * 默认TTL: 5min (300000ms)
 */

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

export interface CacheStats {
  size: number;
  hits: number;
  misses: number;
  hitRate: number;
  keys: string[];
}

export class CacheService {
  private cache: Map<string, CacheEntry<any>>;
  private hits: number;
  private misses: number;
  private defaultTTL: number;

  constructor(defaultTTL: number = 5 * 60 * 1000) {
    this.cache = new Map();
    this.hits = 0;
    this.misses = 0;
    this.defaultTTL = defaultTTL;
  }

  /**
   * setcache
   * @param key cache键
   * @param data cachedata
   * @param ttl 过期时间（ms），默认use构造function中的defaultTTL
   */
  set<T>(key: string, data: T, ttl?: number): void {
    const now = Date.now();
    const expirationTime = ttl !== undefined ? ttl : this.defaultTTL;

    const entry: CacheEntry<T> = {
      data,
      timestamp: now,
      expiresAt: now + expirationTime,
    };

    this.cache.set(key, entry);
  }

  /**
   * getcache
   * @param key cache键
   * @returns cachedata，如果不存在或已过期则returnnull
   */
  get<T>(key: string): T | null {
    const entry = this.cache.get(key);

    if (!entry) {
      this.misses++;
      return null;
    }

    // check是否过期
    if (this.isExpired(key)) {
      this.cache.delete(key);
      this.misses++;
      return null;
    }

    this.hits++;
    return entry.data;
  }

  /**
   * checkcache是否过期
   * @param key cache键
   * @returns 如果过期或不存在returntrue，否则returnfalse
   */
  isExpired(key: string): boolean {
    const entry = this.cache.get(key);

    if (!entry) {
      return true;
    }

    const now = Date.now();
    return now >= entry.expiresAt;
  }

  /**
   * 清除cache
   * @param pattern 可选的模式字符串，如果provide则只清除匹配的键
   */
  clear(pattern?: string): void {
    if (!pattern) {
      this.cache.clear();
      return;
    }

    // 清除匹配模式的cache
    const keys = Array.from(this.cache.keys());
    keys.forEach((key) => {
      if (key.includes(pattern)) {
        this.cache.delete(key);
      }
    });
  }

  /**
   * cleanup所有过期的cache条目
   * @returns cleanup的条目数量
   */
  clearExpired(): number {
    const keys = Array.from(this.cache.keys());
    let clearedCount = 0;

    keys.forEach((key) => {
      if (this.isExpired(key)) {
        this.cache.delete(key);
        clearedCount++;
      }
    });

    return clearedCount;
  }

  /**
   * getcache统计info
   * @returns cache统计object
   */
  getStats(): CacheStats {
    const totalRequests = this.hits + this.misses;
    const hitRate = totalRequests > 0 ? this.hits / totalRequests : 0;

    return {
      size: this.cache.size,
      hits: this.hits,
      misses: this.misses,
      hitRate: Math.round(hitRate * 10000) / 100, // 保留两位小数的百分比
      keys: Array.from(this.cache.keys()),
    };
  }

  /**
   * checkcache中是否存在指定的键
   * @param key cache键
   * @returns 如果存在且未过期returntrue，否则returnfalse
   */
  has(key: string): boolean {
    if (!this.cache.has(key)) {
      return false;
    }

    if (this.isExpired(key)) {
      this.cache.delete(key);
      return false;
    }

    return true;
  }

  /**
   * reset统计info
   */
  resetStats(): void {
    this.hits = 0;
    this.misses = 0;
  }

  /**
   * getcache条目的剩余生存时间
   * @param key cache键
   * @returns 剩余时间（ms），如果不存在或已过期return0
   */
  getTTL(key: string): number {
    const entry = this.cache.get(key);

    if (!entry) {
      return 0;
    }

    const now = Date.now();
    const remaining = entry.expiresAt - now;

    return remaining > 0 ? remaining : 0;
  }

  /**
   * updatecache条目的过期时间
   * @param key cache键
   * @param ttl 新的过期时间（ms）
   * @returns 如果updatesuccessreturntrue，否则returnfalse
   */
  updateTTL(key: string, ttl: number): boolean {
    const entry = this.cache.get(key);

    if (!entry || this.isExpired(key)) {
      return false;
    }

    const now = Date.now();
    entry.expiresAt = now + ttl;
    this.cache.set(key, entry);

    return true;
  }
}

// create默认instance的工厂function
export function createDefaultCacheService(): CacheService {
  return new CacheService(5 * 60 * 1000); // 5min默认TTL
}

// 默认instance - 延迟初始化
let defaultInstance: CacheService | null = null;

export function getCacheService(): CacheService {
  if (!defaultInstance) {
    defaultInstance = createDefaultCacheService();
  }
  return defaultInstance;
}
