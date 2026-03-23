"""
Performance benchmarking framework
"""
import time
import asyncio
import statistics
from typing import Dict, Any, List, Callable, Optional
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """
    Framework for benchmarking and measuring performance
    """
    
    def __init__(self, name: str):
        """
        Initialize benchmark suite.
        
        Args:
            name: Name of the benchmark suite
        """
        self.name = name
        self.results: List[Dict[str, Any]] = []
    
    def benchmark(
        self,
        func: Callable,
        iterations: int = 10,
        warmup: int = 2
    ):
        """
        Decorator to benchmark a function.
        
        Args:
            func: Function to benchmark
            iterations: Number of iterations
            warmup: Number of warmup iterations
        """
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Warmup
            for _ in range(warmup):
                await func(*args, **kwargs)
            
            # Benchmark
            times = []
            for _ in range(iterations):
                start_time = time.perf_counter()
                result = await func(*args, **kwargs)
                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)  # Convert to ms
            
            # Calculate statistics
            benchmark_result = {
                "function": func.__name__,
                "name": self.name,
                "iterations": iterations,
                "times_ms": times,
                "mean_ms": statistics.mean(times),
                "median_ms": statistics.median(times),
                "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
                "min_ms": min(times),
                "max_ms": max(times),
                "p95_ms": self._percentile(times, 95),
                "p99_ms": self._percentile(times, 99)
            }
            
            self.results.append(benchmark_result)
            
            logger.info(
                f"Benchmark {self.name}.{func.__name__}: "
                f"mean={benchmark_result['mean_ms']:.2f}ms, "
                f"p95={benchmark_result['p95_ms']:.2f}ms, "
                f"p99={benchmark_result['p99_ms']:.2f}ms"
            )
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Warmup
            for _ in range(warmup):
                func(*args, **kwargs)
            
            # Benchmark
            times = []
            for _ in range(iterations):
                start_time = time.perf_counter()
                result = func(*args, **kwargs)
                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)  # Convert to ms
            
            # Calculate statistics
            benchmark_result = {
                "function": func.__name__,
                "name": self.name,
                "iterations": iterations,
                "times_ms": times,
                "mean_ms": statistics.mean(times),
                "median_ms": statistics.median(times),
                "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
                "min_ms": min(times),
                "max_ms": max(times),
                "p95_ms": self._percentile(times, 95),
                "p99_ms": self._percentile(times, 99)
            }
            
            self.results.append(benchmark_result)
            
            logger.info(
                f"Benchmark {self.name}.{func.__name__}: "
                f"mean={benchmark_result['mean_ms']:.2f}ms, "
                f"p95={benchmark_result['p95_ms']:.2f}ms, "
                f"p99={benchmark_result['p99_ms']:.2f}ms"
            )
            
            return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    @staticmethod
    def _percentile(data: List[float], percentile: float) -> float:
        """
        Calculate percentile of data.
        
        Args:
            data: List of values
            percentile: Percentile to calculate (0-100)
            
        Returns:
            Percentile value
        """
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        return sorted_data[int(index)]
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all benchmark results.
        
        Returns:
            Summary statistics
        """
        if not self.results:
            return {"message": "No benchmark results available"}
        
        summary = {
            "name": self.name,
            "total_benchmarks": len(self.results),
            "benchmarks": self.results
        }
        
        return summary
    
    def compare_with_baseline(
        self,
        baseline: Dict[str, float],
        threshold: float = 0.2
    ) -> Dict[str, Any]:
        """
        Compare benchmark results with baseline.
        
        Args:
            baseline: Baseline values to compare against
            threshold: Allowed deviation (20% by default)
            
        Returns:
            Comparison results
        """
        comparisons = []
        
        for result in self.results:
            function_name = result["function"]
            current_mean = result["mean_ms"]
            baseline_mean = baseline.get(function_name)
            
            if baseline_mean is None:
                comparisons.append({
                    "function": function_name,
                    "status": "no_baseline",
                    "message": "No baseline value for comparison"
                })
                continue
            
            deviation = (current_mean - baseline_mean) / baseline_mean
            
            if abs(deviation) <= threshold:
                status = "within_threshold"
            elif deviation > 0:
                status = "regression"
            else:
                status = "improvement"
            
            comparisons.append({
                "function": function_name,
                "status": status,
                "current_mean_ms": current_mean,
                "baseline_mean_ms": baseline_mean,
                "deviation_percent": deviation * 100
            })
        
        return {
            "name": self.name,
            "comparisons": comparisons,
            "summary": {
                "total": len(comparisons),
                "regressions": sum(1 for c in comparisons if c["status"] == "regression"),
                "improvements": sum(1 for c in comparisons if c["status"] == "improvement"),
                "within_threshold": sum(1 for c in comparisons if c["status"] == "within_threshold")
            }
        }
    
    def save_results(self, filepath: str):
        """
        Save benchmark results to file.
        
        Args:
            filepath: Path to save results
        """
        import json
        
        with open(filepath, 'w') as f:
            json.dump(self.get_summary(), f, indent=2)
        
        logger.info(f"Benchmark results saved to {filepath}")


class APIResponseTimeBenchmark:
    """
    Benchmark for API response times
    """
    
    def __init__(self):
        """Initialize API response time benchmark."""
        self.response_times: Dict[str, List[float]] = {}
    
    def record_response_time(
        self,
        endpoint: str,
        response_time_ms: float
    ):
        """
        Record API response time.
        
        Args:
            endpoint: API endpoint path
            response_time_ms: Response time in milliseconds
        """
        if endpoint not in self.response_times:
            self.response_times[endpoint] = []
        
        self.response_times[endpoint].append(response_time_ms)
    
    def get_endpoint_stats(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific endpoint.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Statistics for the endpoint
        """
        if endpoint not in self.response_times or not self.response_times[endpoint]:
            return None
        
        times = self.response_times[endpoint]
        
        return {
            "endpoint": endpoint,
            "count": len(times),
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "p95_ms": PerformanceBenchmark._percentile(times, 95),
            "p99_ms": PerformanceBenchmark._percentile(times, 99)
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all endpoints.
        
        Returns:
            Statistics for all endpoints
        """
        stats = {}
        
        for endpoint in self.response_times:
            stats[endpoint] = self.get_endpoint_stats(endpoint)
        
        return stats
    
    def get_slowest_endpoints(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get slowest endpoints by mean response time.
        
        Args:
            limit: Maximum number of endpoints to return
            
        Returns:
            List of slowest endpoints
        """
        endpoint_stats = []
        
        for endpoint in self.response_times:
            stats = self.get_endpoint_stats(endpoint)
            if stats:
                endpoint_stats.append(stats)
        
        # Sort by mean response time (descending)
        endpoint_stats.sort(key=lambda x: x["mean_ms"], reverse=True)
        
        return endpoint_stats[:limit]
    
    def clear_stats(self, endpoint: Optional[str] = None):
        """
        Clear statistics for endpoint(s).
        
        Args:
            endpoint: Specific endpoint to clear, or None to clear all
        """
        if endpoint:
            self.response_times.pop(endpoint, None)
        else:
            self.response_times.clear()


# Global API benchmark instance
api_benchmark = APIResponseTimeBenchmark()
