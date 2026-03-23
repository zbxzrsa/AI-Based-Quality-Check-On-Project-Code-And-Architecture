"""
Optimized Parser Service with Parallel Processing and Caching

This service implements performance optimizations for AST parsing:
- Parallel parsing for multiple files using multiprocessing
- File content caching with hash-based invalidation
- Performance monitoring to ensure 2-second per-file target

Implements Requirements 1.2, 10.2
"""
import hashlib
import time
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing

from app.services.parsers.factory import ParserFactory
from app.schemas.ast_models import ParsedFile


class FileCache:
    """
    Cache for parsed file results with hash-based invalidation
    
    Caches ParsedFile objects keyed by file path and content hash.
    Invalidates cache when file content changes.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize file cache
        
        Args:
            max_size: Maximum number of cached entries (default: 1000)
        """
        self._cache: Dict[str, Tuple[str, ParsedFile]] = {}
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def _compute_hash(self, content: str) -> str:
        """Compute SHA-256 hash of file content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get(self, file_path: str, content: str) -> Optional[ParsedFile]:
        """
        Get cached parsed file if content hasn't changed
        
        Args:
            file_path: Path to the file
            content: Current file content
        
        Returns:
            Cached ParsedFile if available and valid, None otherwise
        """
        content_hash = self._compute_hash(content)
        
        if file_path in self._cache:
            cached_hash, parsed_file = self._cache[file_path]
            if cached_hash == content_hash:
                self._hits += 1
                return parsed_file
        
        self._misses += 1
        return None
    
    def put(self, file_path: str, content: str, parsed_file: ParsedFile) -> None:
        """
        Cache a parsed file result
        
        Args:
            file_path: Path to the file
            content: File content
            parsed_file: Parsed result to cache
        """
        content_hash = self._compute_hash(content)
        
        # Implement simple LRU eviction if cache is full
        if len(self._cache) >= self._max_size and file_path not in self._cache:
            # Remove oldest entry (first key)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[file_path] = (content_hash, parsed_file)
    
    def invalidate(self, file_path: str) -> None:
        """Remove a file from cache"""
        if file_path in self._cache:
            del self._cache[file_path]
    
    def clear(self) -> None:
        """Clear entire cache"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate
        }


def _parse_single_file(file_path: str, content: Optional[str] = None) -> Tuple[str, ParsedFile, float]:
    """
    Parse a single file (used by parallel processing)
    
    This function is defined at module level to be picklable for multiprocessing.
    
    Args:
        file_path: Path to the file
        content: Optional file content
    
    Returns:
        Tuple of (file_path, ParsedFile, parse_time_seconds)
    """
    start_time = time.time()
    
    try:
        # Load content if not provided
        if content is None:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # Get parser and parse
        parser = ParserFactory.get_parser_by_filename(file_path)
        if not parser:
            from app.schemas.ast_models import ModuleNode
            from pathlib import Path
            parsed_file = ParsedFile(
                module=ModuleNode(
                    name=Path(file_path).stem,
                    file_path=file_path,
                    language="unknown"
                ),
                errors=[f"Unsupported file type: {file_path}"]
            )
        else:
            parsed_file = parser.parse_file(file_path, content)
        
        parse_time = time.time() - start_time
        return (file_path, parsed_file, parse_time)
    
    except Exception as e:
        parse_time = time.time() - start_time
        from app.schemas.ast_models import ModuleNode
        from pathlib import Path
        parsed_file = ParsedFile(
            module=ModuleNode(
                name=Path(file_path).stem,
                file_path=file_path,
                language="unknown"
            ),
            errors=[f"Parse error: {str(e)}"]
        )
        return (file_path, parsed_file, parse_time)


class OptimizedParser:
    """
    High-performance parser with parallel processing and caching
    
    Features:
    - Parallel parsing using process pool for CPU-bound parsing
    - Content-based caching with automatic invalidation
    - Performance monitoring and metrics
    - Configurable parallelism and cache size
    """
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        cache_size: int = 1000,
        enable_cache: bool = True
    ):
        """
        Initialize optimized parser
        
        Args:
            max_workers: Maximum parallel workers (default: CPU count)
            cache_size: Maximum cache entries (default: 1000)
            enable_cache: Enable caching (default: True)
        """
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.enable_cache = enable_cache
        self.cache = FileCache(max_size=cache_size) if enable_cache else None
        self._total_parse_time = 0.0
        self._total_files_parsed = 0
    
    def parse_file(
        self,
        file_path: str,
        content: Optional[str] = None,
        use_cache: bool = True
    ) -> Tuple[ParsedFile, float]:
        """
        Parse a single file with caching
        
        Args:
            file_path: Path to the file
            content: Optional file content
            use_cache: Whether to use cache (default: True)
        
        Returns:
            Tuple of (ParsedFile, parse_time_seconds)
        """
        start_time = time.time()
        
        # Load content if not provided
        if content is None:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # Check cache
        if self.enable_cache and use_cache and self.cache:
            cached_result = self.cache.get(file_path, content)
            if cached_result:
                cache_time = time.time() - start_time
                return (cached_result, cache_time)
        
        # Parse file
        _, parsed_file, parse_time = _parse_single_file(file_path, content)
        
        # Cache result
        if self.enable_cache and self.cache:
            self.cache.put(file_path, content, parsed_file)
        
        # Update metrics
        self._total_parse_time += parse_time
        self._total_files_parsed += 1
        
        return (parsed_file, parse_time)
    
    def parse_files_parallel(
        self,
        file_paths: List[str],
        use_cache: bool = True,
        use_processes: bool = True
    ) -> Dict[str, Tuple[ParsedFile, float]]:
        """
        Parse multiple files in parallel
        
        Args:
            file_paths: List of file paths to parse
            use_cache: Whether to use cache (default: True)
            use_processes: Use process pool (True) or thread pool (False)
        
        Returns:
            Dictionary mapping file_path to (ParsedFile, parse_time)
        """
        results = {}
        files_to_parse = []
        
        # Check cache for each file
        if self.enable_cache and use_cache and self.cache:
            for file_path in file_paths:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    cached_result = self.cache.get(file_path, content)
                    if cached_result:
                        results[file_path] = (cached_result, 0.0)  # Cache hit, no parse time
                    else:
                        files_to_parse.append(file_path)
                except Exception as e:
                    # If we can't read the file, add it to parse list to handle error properly
                    files_to_parse.append(file_path)
        else:
            files_to_parse = file_paths
        
        # Parse remaining files in parallel
        if files_to_parse:
            executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
            
            with executor_class(max_workers=self.max_workers) as executor:
                # Submit all parse tasks
                future_to_path = {
                    executor.submit(_parse_single_file, file_path): file_path
                    for file_path in files_to_parse
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_path):
                    file_path, parsed_file, parse_time = future.result()
                    results[file_path] = (parsed_file, parse_time)
                    
                    # Cache result
                    if self.enable_cache and self.cache:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            self.cache.put(file_path, content, parsed_file)
                        except Exception:
                            pass  # Skip caching if we can't read file
                    
                    # Update metrics
                    self._total_parse_time += parse_time
                    self._total_files_parsed += 1
        
        return results
    
    def parse_files_batch(
        self,
        file_paths: List[str],
        batch_size: int = 10,
        use_cache: bool = True
    ) -> Dict[str, Tuple[ParsedFile, float]]:
        """
        Parse files in batches for better memory management
        
        Useful for parsing large numbers of files without overwhelming memory.
        
        Args:
            file_paths: List of file paths to parse
            batch_size: Number of files to parse in each batch
            use_cache: Whether to use cache
        
        Returns:
            Dictionary mapping file_path to (ParsedFile, parse_time)
        """
        all_results = {}
        
        # Process in batches
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]
            batch_results = self.parse_files_parallel(batch, use_cache=use_cache)
            all_results.update(batch_results)
        
        return all_results
    
    def invalidate_cache(self, file_path: str) -> None:
        """Invalidate cache for a specific file"""
        if self.cache:
            self.cache.invalidate(file_path)
    
    def clear_cache(self) -> None:
        """Clear entire cache"""
        if self.cache:
            self.cache.clear()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_stats()
        return {"enabled": False}
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        avg_parse_time = (
            self._total_parse_time / self._total_files_parsed
            if self._total_files_parsed > 0
            else 0.0
        )
        
        stats = {
            "total_files_parsed": self._total_files_parsed,
            "total_parse_time": self._total_parse_time,
            "avg_parse_time": avg_parse_time,
            "max_workers": self.max_workers,
            "cache_enabled": self.enable_cache
        }
        
        if self.cache:
            stats["cache_stats"] = self.get_cache_stats()
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset performance statistics"""
        self._total_parse_time = 0.0
        self._total_files_parsed = 0
        if self.cache:
            self.cache._hits = 0
            self.cache._misses = 0
