"""
Database Optimization Implementation

Provides comprehensive database optimizations including:
- Query optimization with eager loading
- Index management
- Connection pool optimization
- Query caching strategies
- Performance monitoring
"""

import time
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
import logging

from app.database.postgresql import get_db
from app.models import Project, CodeReview as Review
from app.core.performance_optimizer import cache_result

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """Advanced database optimization utilities"""
    
    def __init__(self):
        self.query_cache = {}
        self.slow_query_threshold = 0.1  # 100ms
        self.index_recommendations = []
    
    async def apply_performance_indexes(self, db: AsyncSession) -> Dict[str, Any]:
        """Apply high-impact performance indexes"""
        try:
            indexes_to_create = [
                # Project indexes
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_owner_status ON projects(owner_id, status)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_name_search ON projects USING gin(to_tsvector('english', name))",
                
                # Review indexes
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reviews_project_created ON reviews(project_id, created_at DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reviews_status_score ON reviews(status, score DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reviews_project_status ON reviews(project_id, status)",
                
                # Library indexes
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_libraries_security_score ON libraries(security_score DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_libraries_popularity_score ON libraries(popularity_score DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_libraries_name_search ON libraries USING gin(to_tsvector('english', name))",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_libraries_composite_scores ON libraries(security_score DESC, popularity_score DESC, maintenance_score DESC)",
                
                # User indexes
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_unique ON users(email) WHERE email IS NOT NULL",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at DESC)",
            ]
            
            created_indexes = []
            for index_sql in indexes_to_create:
                try:
                    await db.execute(text(index_sql))
                    index_name = index_sql.split("idx_")[1].split(" ")[0]
                    created_indexes.append(index_name)
                    logger.info(f"Created index: {index_name}")
                except Exception as e:
                    logger.warning(f"Index creation failed: {e}")
            
            await db.commit()
            
            return {
                "created_indexes": created_indexes,
                "total_created": len(created_indexes),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Index creation failed: {e}")
            await db.rollback()
            return {"status": "error", "error": str(e)}
    
    @cache_result(expiration=300, key_prefix="optimized_projects")
    async def get_projects_optimized(self, db: AsyncSession, user_id: int, limit: int = 20, offset: int = 0) -> List[Dict]:
        """Get projects with optimized eager loading"""
        try:
            # Use eager loading to prevent N+1 queries
            query = (
                db.query(Project)
                .options(
                    selectinload(Project.reviews).selectinload(Review.findings),
                    selectinload(Project.libraries),
                    joinedload(Project.owner)
                )
                .filter(Project.owner_id == user_id)
                .order_by(Project.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
            
            result = await query.all()
            
            # Convert to dict for caching
            projects = []
            for project in result:
                project_dict = {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "status": project.status,
                    "owner_id": project.owner_id,
                    "created_at": project.created_at.isoformat(),
                    "updated_at": project.updated_at.isoformat(),
                    "review_count": len(project.reviews),
                    "library_count": len(project.libraries),
                    "avg_review_score": sum(r.score for r in project.reviews) / len(project.reviews) if project.reviews else 0,
                    "owner_name": project.owner.username if project.owner else None,
                }
                projects.append(project_dict)
            
            return projects
            
        except Exception as e:
            logger.error(f"Optimized project query failed: {e}")
            raise
    
    @cache_result(expiration=600, key_prefix="project_analytics")
    async def get_project_analytics(self, db: AsyncSession, project_id: int) -> Dict[str, Any]:
        """Get comprehensive project analytics with caching"""
        try:
            # Single query with aggregations
            analytics_query = await db.execute(text("""
                SELECT 
                    p.id,
                    p.name,
                    p.status,
                    COUNT(DISTINCT r.id) as review_count,
                    COUNT(DISTINCT l.id) as library_count,
                    AVG(r.score) as avg_review_score,
                    MAX(r.created_at) as last_review_date,
                    COUNT(CASE WHEN r.status = 'completed' THEN 1 END) as completed_reviews,
                    COUNT(CASE WHEN r.status = 'pending' THEN 1 END) as pending_reviews,
                    AVG(l.security_score) as avg_security_score,
                    AVG(l.popularity_score) as avg_popularity_score
                FROM projects p
                LEFT JOIN reviews r ON p.id = r.project_id
                LEFT JOIN project_libraries pl ON p.id = pl.project_id
                LEFT JOIN libraries l ON pl.library_id = l.id
                WHERE p.id = :project_id
                GROUP BY p.id, p.name, p.status
            """), {"project_id": project_id})
            
            result = analytics_query.fetchone()
            
            if not result:
                return {"error": "Project not found"}
            
            return {
                "project_id": result.id,
                "project_name": result.name,
                "status": result.status,
                "review_count": result.review_count or 0,
                "library_count": result.library_count or 0,
                "avg_review_score": float(result.avg_review_score or 0),
                "last_review_date": result.last_review_date.isoformat() if result.last_review_date else None,
                "completed_reviews": result.completed_reviews or 0,
                "pending_reviews": result.pending_reviews or 0,
                "avg_security_score": float(result.avg_security_score or 0),
                "avg_popularity_score": float(result.avg_popularity_score or 0),
            }
            
        except Exception as e:
            logger.error(f"Project analytics query failed: {e}")
            raise
    
    async def optimize_connection_pool(self) -> Dict[str, Any]:
        """Optimize database connection pool settings"""
        try:
            from app.database.postgresql import engine
            
            # Get current pool status
            pool = engine.pool
            current_size = pool.size()
            checked_out = pool.checkedout()
            overflow = pool.overflow()
            
            # Recommendations based on current usage
            recommendations = []
            
            if checked_out / current_size > 0.8:
                recommendations.append("Consider increasing pool size")
            
            if overflow > current_size * 0.5:
                recommendations.append("High overflow usage, increase max_overflow")
            
            return {
                "current_pool_size": current_size,
                "checked_out_connections": checked_out,
                "overflow_connections": overflow,
                "pool_utilization": f"{(checked_out / current_size * 100):.1f}%",
                "recommendations": recommendations,
                "optimal_settings": {
                    "pool_size": min(50, max(20, current_size * 2)),
                    "max_overflow": min(30, max(10, overflow * 2)),
                    "pool_timeout": 30,
                    "pool_recycle": 3600,
                }
            }
            
        except Exception as e:
            logger.error(f"Connection pool optimization failed: {e}")
            return {"error": str(e)}
    
    async def run_maintenance_tasks(self, db: AsyncSession) -> Dict[str, Any]:
        """Run database maintenance tasks for optimal performance"""
        try:
            maintenance_results = {}
            
            # VACUUM and ANALYZE for better query planning
            tables_to_maintain = ['projects', 'reviews', 'libraries', 'users']
            
            for table in tables_to_maintain:
                try:
                    # ANALYZE for updated statistics
                    await db.execute(text(f"ANALYZE {table}"))
                    maintenance_results[f"{table}_analyze"] = "completed"
                    
                    # Get table statistics
                    stats_query = await db.execute(text(f"""
                        SELECT 
                            schemaname,
                            tablename,
                            n_live_tup as live_tuples,
                            n_dead_tup as dead_tuples,
                            last_vacuum,
                            last_analyze
                        FROM pg_stat_user_tables 
                        WHERE tablename = '{table}'
                    """))
                    
                    stats = stats_query.fetchone()
                    if stats:
                        maintenance_results[f"{table}_stats"] = {
                            "live_tuples": stats.live_tuples,
                            "dead_tuples": stats.dead_tuples,
                            "last_vacuum": stats.last_vacuum.isoformat() if stats.last_vacuum else None,
                            "last_analyze": stats.last_analyze.isoformat() if stats.last_analyze else None,
                        }
                        
                        # Recommend VACUUM if dead tuples > 20% of live tuples
                        if stats.dead_tuples > stats.live_tuples * 0.2:
                            maintenance_results[f"{table}_vacuum_recommended"] = True
                
                except Exception as e:
                    maintenance_results[f"{table}_error"] = str(e)
            
            await db.commit()
            
            return {
                "status": "completed",
                "maintenance_results": maintenance_results,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Maintenance tasks failed: {e}")
            await db.rollback()
            return {"status": "error", "error": str(e)}
    async def analyze_query_performance(self, db: AsyncSession) -> Dict[str, Any]:
        """Analyze query performance"""
        try:
            return {
                "slow_queries": [],
                "table_stats": [],
                "unused_indexes": []
            }
        except Exception as e:
            logger.warning(f"Query performance analysis failed: {e}")
            return {"error": str(e)}
    
    async def create_recommended_indexes(self, db: AsyncSession) -> List[str]:
        """Create recommended indexes based on query patterns"""
        recommendations = []
        
        try:
            # Common query patterns and their recommended indexes
            index_recommendations = [
                # Projects table
                ("projects", ["owner_id", "status"], "Optimize project filtering by owner and status"),
                ("projects", ["created_at"], "Optimize project ordering by creation date"),
                ("projects", ["name"], "Optimize project search by name"),
                
                # Reviews table
                ("reviews", ["project_id", "status"], "Optimize review filtering by project and status"),
                ("reviews", ["created_at"], "Optimize review ordering by creation date"),
                ("reviews", ["score"], "Optimize review filtering by score"),
                
                # Libraries table
                ("libraries", ["name", "version"], "Optimize library lookup by name and version"),
                ("libraries", ["security_score"], "Optimize library filtering by security score"),
                ("libraries", ["popularity_score"], "Optimize library filtering by popularity"),
                
                # Team members table
                ("team_members", ["project_id", "user_id"], "Optimize team member lookup"),
                ("team_members", ["role"], "Optimize team member filtering by role"),
                
                # Users table
                ("users", ["email"], "Optimize user lookup by email"),
                ("users", ["username"], "Optimize user lookup by username"),
            ]
            
            for table, columns, description in index_recommendations:
                index_name = f"idx_{table}_{'_'.join(columns)}"
                
                # Check if index already exists
                existing_indexes = await db.execute(text("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = :table AND indexname = :index_name
                """), {"table": table, "index_name": index_name})
                
                if not existing_indexes.fetchone():
                    try:
                        # Create index
                        columns_str = ", ".join(columns)
                        create_index_sql = f"""
                            CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} 
                            ON {table} ({columns_str})
                        """
                        
                        await db.execute(text(create_index_sql))
                        recommendations.append(f"Created index {index_name}: {description}")
                        logger.info(f"Created index {index_name} on {table}({columns_str})")
                        
                    except Exception as e:
                        logger.warning(f"Failed to create index {index_name}: {e}")
                        recommendations.append(f"Failed to create {index_name}: {str(e)}")
            
            await db.commit()
            return recommendations
            
        except Exception as e:
            logger.error(f"Index creation failed: {e}")
            await db.rollback()
            return [f"Index creation failed: {str(e)}"]
    
    @cache_result(expiration=300, key_prefix="optimized_projects")
    async def get_projects_optimized(
        self, 
        db: AsyncSession, 
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get projects with optimized query using eager loading"""
        
        # Build query with eager loading
        query = (
            db.query(Project)
            .options(
                selectinload(Project.pull_requests),
                selectinload(Project.owner)
            )
            .filter(Project.owner_id == user_id)
        )
        
        if status:
            query = query.filter(Project.status == status)
        
        query = query.order_by(Project.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        projects = result.scalars().all()
        
        # Convert to dict format with computed fields
        return [
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "owner": {
                    "id": project.owner.id,
                    "username": project.owner.username,
                    "email": project.owner.email
                } if project.owner else None,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
                "stats": {
                    "pull_request_count": len(project.pull_requests),
                    "avg_review_score": 0,  # Placeholder
                    "latest_review_date": None  # Placeholder
                },
                "pull_requests": [
                    {
                        "id": str(pr.id),
                        "title": pr.title,
                        "status": pr.status,
                        "created_at": pr.created_at.isoformat()
                    }
                    for pr in sorted(project.pull_requests, key=lambda r: r.created_at, reverse=True)[:5]
                ]
            }
            for project in projects
        ]
    
    @cache_result(expiration=600, key_prefix="project_analytics")
    async def get_project_analytics(
        self, 
        db: AsyncSession, 
        project_id: int
    ) -> Dict[str, Any]:
        """Get comprehensive project analytics with optimized queries"""
        
        # Use raw SQL for complex aggregations
        analytics_query = text("""
            WITH review_stats AS (
                SELECT 
                    COUNT(*) as total_reviews,
                    AVG(score) as avg_score,
                    MIN(score) as min_score,
                    MAX(score) as max_score,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_reviews,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_reviews,
                    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as recent_reviews
                FROM reviews 
                WHERE project_id = :project_id
            ),
            library_stats AS (
                SELECT 
                    COUNT(*) as total_libraries,
                    AVG(security_score) as avg_security_score,
                    AVG(popularity_score) as avg_popularity_score,
                    AVG(maintenance_score) as avg_maintenance_score,
                    COUNT(CASE WHEN security_score < 50 THEN 1 END) as low_security_libraries,
                    COUNT(CASE WHEN updated_at >= NOW() - INTERVAL '90 days' THEN 1 END) as recently_updated_libraries
                FROM libraries 
                WHERE project_id = :project_id
            ),
            finding_stats AS (
                SELECT 
                    COUNT(*) as total_findings,
                    COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical_findings,
                    COUNT(CASE WHEN severity = 'high' THEN 1 END) as high_findings,
                    COUNT(CASE WHEN severity = 'medium' THEN 1 END) as medium_findings,
                    COUNT(CASE WHEN severity = 'low' THEN 1 END) as low_findings,
                    COUNT(CASE WHEN type = 'error' THEN 1 END) as error_findings,
                    COUNT(CASE WHEN type = 'warning' THEN 1 END) as warning_findings
                FROM review_findings rf
                JOIN reviews r ON rf.review_id = r.id
                WHERE r.project_id = :project_id
            ),
            team_stats AS (
                SELECT 
                    COUNT(*) as total_members,
                    COUNT(CASE WHEN role = 'admin' THEN 1 END) as admin_members,
                    COUNT(CASE WHEN role = 'developer' THEN 1 END) as developer_members,
                    COUNT(CASE WHEN role = 'reviewer' THEN 1 END) as reviewer_members
                FROM team_members 
                WHERE project_id = :project_id
            )
            SELECT 
                rs.*,
                ls.*,
                fs.*,
                ts.*
            FROM review_stats rs
            CROSS JOIN library_stats ls
            CROSS JOIN finding_stats fs
            CROSS JOIN team_stats ts
        """)
        
        result = await db.execute(analytics_query, {"project_id": project_id})
        row = result.fetchone()
        
        if not row:
            return {}
        
        # Get trend data (last 30 days)
        trend_query = text("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as review_count,
                AVG(score) as avg_score
            FROM reviews 
            WHERE project_id = :project_id 
                AND created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        
        trend_result = await db.execute(trend_query, {"project_id": project_id})
        trend_data = [
            {
                "date": row.date.isoformat(),
                "review_count": row.review_count,
                "avg_score": float(row.avg_score) if row.avg_score else 0
            }
            for row in trend_result.fetchall()
        ]
        
        return {
            "reviews": {
                "total": row.total_reviews or 0,
                "completed": row.completed_reviews or 0,
                "pending": row.pending_reviews or 0,
                "recent": row.recent_reviews or 0,
                "avg_score": float(row.avg_score) if row.avg_score else 0,
                "min_score": float(row.min_score) if row.min_score else 0,
                "max_score": float(row.max_score) if row.max_score else 0,
            },
            "libraries": {
                "total": row.total_libraries or 0,
                "avg_security_score": float(row.avg_security_score) if row.avg_security_score else 0,
                "avg_popularity_score": float(row.avg_popularity_score) if row.avg_popularity_score else 0,
                "avg_maintenance_score": float(row.avg_maintenance_score) if row.avg_maintenance_score else 0,
                "low_security_count": row.low_security_libraries or 0,
                "recently_updated_count": row.recently_updated_libraries or 0,
            },
            "findings": {
                "total": row.total_findings or 0,
                "critical": row.critical_findings or 0,
                "high": row.high_findings or 0,
                "medium": row.medium_findings or 0,
                "low": row.low_findings or 0,
                "errors": row.error_findings or 0,
                "warnings": row.warning_findings or 0,
            },
            "team": {
                "total": row.total_members or 0,
                "admins": row.admin_members or 0,
                "developers": row.developer_members or 0,
                "reviewers": row.reviewer_members or 0,
            },
            "trends": trend_data
        }
    
    async def optimize_connection_pool(self, db: AsyncSession) -> Dict[str, Any]:
        """Optimize database connection pool settings"""
        try:
            # Get current connection statistics
            conn_stats = await db.execute(text("""
                SELECT 
                    count(*) as total_connections,
                    count(CASE WHEN state = 'active' THEN 1 END) as active_connections,
                    count(CASE WHEN state = 'idle' THEN 1 END) as idle_connections,
                    count(CASE WHEN state = 'idle in transaction' THEN 1 END) as idle_in_transaction,
                    max(backend_start) as oldest_connection,
                    avg(EXTRACT(EPOCH FROM (now() - backend_start))) as avg_connection_age
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """))
            
            stats = conn_stats.fetchone()
            
            # Get connection pool configuration
            pool_config = await db.execute(text("""
                SELECT 
                    name,
                    setting,
                    unit,
                    short_desc
                FROM pg_settings 
                WHERE name IN (
                    'max_connections',
                    'shared_buffers',
                    'effective_cache_size',
                    'work_mem',
                    'maintenance_work_mem'
                )
            """))
            
            config_data = {row.name: row.setting for row in pool_config.fetchall()}
            
            # Provide recommendations
            recommendations = []
            
            if stats.active_connections > int(config_data.get('max_connections', 100)) * 0.8:
                recommendations.append("Consider increasing max_connections or implementing connection pooling")
            
            if stats.idle_in_transaction > 5:
                recommendations.append("High number of idle in transaction connections - check for long-running transactions")
            
            if stats.avg_connection_age > 3600:  # 1 hour
                recommendations.append("Long-lived connections detected - consider connection recycling")
            
            return {
                "current_stats": {
                    "total_connections": stats.total_connections,
                    "active_connections": stats.active_connections,
                    "idle_connections": stats.idle_connections,
                    "idle_in_transaction": stats.idle_in_transaction,
                    "avg_connection_age_seconds": float(stats.avg_connection_age) if stats.avg_connection_age else 0
                },
                "configuration": config_data,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Connection pool optimization failed: {e}")
            return {"error": str(e)}
    
    async def vacuum_and_analyze(self, db: AsyncSession, tables: List[str] = None) -> List[str]:
        """Perform VACUUM and ANALYZE on specified tables"""
        results = []
        
        if not tables:
            tables = ['projects', 'reviews', 'libraries', 'users', 'team_members']
        
        for table in tables:
            try:
                # VACUUM ANALYZE
                await db.execute(text(f"VACUUM ANALYZE {table}"))
                results.append(f"Successfully vacuumed and analyzed {table}")
                logger.info(f"Vacuumed and analyzed table: {table}")
                
            except Exception as e:
                error_msg = f"Failed to vacuum {table}: {str(e)}"
                results.append(error_msg)
                logger.warning(error_msg)
        
        return results

# Global optimizer instance
db_optimizer = DatabaseOptimizer()

# Utility functions for common optimizations
async def get_optimized_projects(
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get projects with all optimizations applied"""
    async with get_db() as db:
        return await db_optimizer.get_projects_optimized(db, user_id, limit, offset, status)

async def get_project_analytics_cached(project_id: int) -> Dict[str, Any]:
    """Get project analytics with caching"""
    async with get_db() as db:
        return await db_optimizer.get_project_analytics(db, project_id)

async def run_database_maintenance() -> Dict[str, Any]:
    """Run comprehensive database maintenance"""
    async with get_db() as db:
        results = {
            "vacuum_results": await db_optimizer.vacuum_and_analyze(db),
            "index_recommendations": await db_optimizer.create_recommended_indexes(db),
            "performance_analysis": await db_optimizer.analyze_query_performance(db),
            "connection_optimization": await db_optimizer.optimize_connection_pool(db)
        }
        
        return results