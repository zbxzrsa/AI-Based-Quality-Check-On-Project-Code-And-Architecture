"""
Circular Dependency Detection Demo

This script demonstrates how to use the CircularDependencyDetector
to find and analyze circular dependencies in code dependency graphs.

Usage:
    python examples/circular_dependency_detection_demo.py
"""
import logging
logger = logging.getLogger(__name__)

import asyncio
from app.services.graph_builder import (
    CircularDependencyDetector,
    CycleSeverity
)


async def demo_basic_detection():
    """Demonstrate basic cycle detection"""
    logger.info("=" * 60)
    logger.info("Demo 1: Basic Cycle Detection")
    logger.info("=" * 60)
    
    detector = CircularDependencyDetector()
    
    # Detect all cycles in the graph
    result = await detector.detect_cycles()
    
    logger.info("\n📊 Detection Results:")
    logger.info("   Total cycles found: {result.total_cycles}")
    logger.info("   Detection time: {result.detection_time_ms:.2f}ms")
    logger.info("   Affected files: {len(result.affected_files)}")
    
    # Show severity breakdown
    logger.info("\n📈 Severity Breakdown:")
    for severity, count in result.severity_breakdown.items():
        emoji = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🟠",
            "critical": "🔴"
        }.get(severity, "⚪")
        logger.info("   {emoji} {severity.upper()}: {count} cycles")
    
    # List cycles
    if result.cycles:
        logger.info("\n🔄 Detected Cycles:")
        for i, cycle in enumerate(result.cycles[:5], 1):  # Show first 5
            logger.info(f"\n   Cycle {i}: {cycle.cycle_id}")
            logger.info(f"   ├─ Severity: {cycle.severity.value}")
            logger.info(f"   ├─ Depth: {cycle.depth} nodes")
            logger.info(f"   ├─ Complexity: {cycle.total_complexity} (avg: {cycle.avg_complexity})")
            path_display = f"   └─ Path: {' → '.join(cycle.nodes[:4])}"
            if len(cycle.nodes) > 4:
                path_display += " → ..."
            logger.info(path_display)
        
        if len(result.cycles) > 5:
            logger.info(f"\n   ... and {len(result.cycles) - 5} more cycles")
    else:
        logger.info("\n✅ No circular dependencies found!")


async def demo_severity_filtering():
    """Demonstrate filtering by severity"""
    logger.info("\n\n" + "=" * 60)
    logger.info("Demo 2: Severity Filtering")
    logger.info("=" * 60)
    
    detector = CircularDependencyDetector()
    
    # Only detect high and critical severity cycles
    result = await detector.detect_cycles(min_severity=CycleSeverity.HIGH)
    
    logger.info("\n🔍 High/Critical Severity Cycles:")
    logger.info(f"   Found: {result.total_cycles} cycles")
    
    for cycle in result.cycles:
        severity_emoji = "🔴" if cycle.severity == CycleSeverity.CRITICAL else "🟠"
        logger.info(f"\n   {severity_emoji} {cycle.cycle_id}")
        logger.info(f"      Severity: {cycle.severity.value}")
        nodes_display = f"      Nodes: {', '.join(cycle.nodes[:3])}"
        if len(cycle.nodes) > 3:
            nodes_display += f" + {len(cycle.nodes) - 3} more"
        logger.info(nodes_display)


async def demo_entity_specific_detection():
    """Demonstrate detecting cycles for a specific entity"""
    logger.info("\n\n" + "=" * 60)
    logger.info("Demo 3: Entity-Specific Detection")
    logger.info("=" * 60)
    
    detector = CircularDependencyDetector()
    
    # Example: Check if a specific entity is involved in cycles
    entity_name = "UserService"
    file_path = "/src/services/user_service.py"
    
    logger.info("\n🔎 Checking cycles for: {entity_name}")
    
    cycles = await detector.detect_cycles_for_entity(
        entity_name=entity_name,
        file_path=file_path
    )
    
    if cycles:
        logger.info("   ⚠️  Found {len(cycles)} cycles involving {entity_name}:")
        for cycle in cycles:
            logger.info("\n   • {cycle.cycle_id}")
            logger.info("     Severity: {cycle.severity.value}")
            logger.info("     Other nodes: {', '.join([n for n in cycle.nodes if n != entity_name][:3])}")
    else:
        logger.info("   ✅ No cycles found for {entity_name}")


async def demo_visualization_data():
    """Demonstrate getting visualization data"""
    logger.info("\n\n" + "=" * 60)
    logger.info("Demo 4: Visualization Data Generation")
    logger.info("=" * 60)
    
    detector = CircularDependencyDetector()
    
    # First, detect cycles
    result = await detector.detect_cycles()
    
    if result.cycles:
        # Get visualization data for the first cycle
        cycle = result.cycles[0]
        logger.info("\n📊 Generating visualization data for: {cycle.cycle_id}")
        
        viz_data = await detector.get_cycle_visualization_data(cycle.cycle_id)
        
        if viz_data:
            logger.info("\n   Visualization Data:")
            logger.info("   ├─ Nodes: {len(viz_data['nodes'])}")
            logger.info("   ├─ Edges: {len(viz_data['edges'])}")
            logger.info("   ├─ Severity: {viz_data['severity']}")
            logger.info("   └─ Metadata:")
            for key, value in viz_data['metadata'].items():
                logger.info("      • {key}: {value}")
            
            logger.info("\n   Node Details:")
            for node in viz_data['nodes'][:3]:
                logger.info("   • {node['label']} ({node['file_path']})")
            
            logger.info("\n   Edge Details:")
            for edge in viz_data['edges'][:3]:
                logger.info("   • {edge['source']} → {edge['target']}")
        else:
            logger.info("   ❌ Could not generate visualization data")
    else:
        logger.info("\n   ℹ️  No cycles to visualize")


async def demo_severity_calculation():
    """Demonstrate severity calculation logic"""
    logger.info("\n\n" + "=" * 60)
    logger.info("Demo 5: Severity Calculation Examples")
    logger.info("=" * 60)
    
    detector = CircularDependencyDetector()
    
    test_cases = [
        (2, 10, 5.0, "Small cycle, low complexity"),
        (5, 60, 12.0, "Medium cycle, moderate complexity"),
        (8, 120, 15.0, "Large cycle, high complexity"),
        (15, 300, 20.0, "Very large cycle, critical complexity")
    ]
    
    logger.info("\n   Severity Calculation Examples:")
    for depth, total_complexity, avg_complexity, description in test_cases:
        severity = detector._calculate_severity(depth, total_complexity, avg_complexity)
        
        emoji = {
            CycleSeverity.LOW: "🟢",
            CycleSeverity.MEDIUM: "🟡",
            CycleSeverity.HIGH: "🟠",
            CycleSeverity.CRITICAL: "🔴"
        }[severity]
        
        logger.info("\n   {emoji} {severity.value.upper()}")
        logger.info("      {description}")
        logger.info("      Depth: {depth}, Total Complexity: {total_complexity}, Avg: {avg_complexity}")


async def demo_json_serialization():
    """Demonstrate JSON serialization"""
    logger.info("\n\n" + "=" * 60)
    logger.info("Demo 6: JSON Serialization")
    logger.info("=" * 60)
    
    detector = CircularDependencyDetector()
    result = await detector.detect_cycles()
    
    # Convert to dictionary (JSON-serializable)
    result_dict = result.to_dict()
    
    logger.info("\n   Serialized Result Structure:")
    logger.info("   ├─ total_cycles: {result_dict['total_cycles']}")
    logger.info("   ├─ detection_time_ms: {result_dict['detection_time_ms']}")
    logger.info("   ├─ severity_breakdown: {result_dict['severity_breakdown']}")
    logger.info("   ├─ affected_files: {len(result_dict['affected_files'])} files")
    logger.info("   └─ cycles: {len(result_dict['cycles'])} cycle objects")
    
    if result_dict['cycles']:
        logger.info("\n   First Cycle Structure:")
        cycle = result_dict['cycles'][0]
        for key, value in cycle.items():
            if isinstance(value, list) and len(value) > 3:
                logger.info("   ├─ {key}: [{len(value)} items]")
            else:
                logger.info("   ├─ {key}: {value}")


async def main():
    """Run all demos"""
    logger.info("\n" + "=" * 60)
    logger.info("Circular Dependency Detection Demo")
    logger.info("=" * 60)
    logger.info("\nThis demo shows how to use the CircularDependencyDetector")
    logger.info("to find and analyze circular dependencies in code graphs.")
    
    try:
        await demo_basic_detection()
        await demo_severity_filtering()
        await demo_entity_specific_detection()
        await demo_visualization_data()
        await demo_severity_calculation()
        await demo_json_serialization()
        
        logger.info("\n\n" + "=" * 60)
        logger.info("Demo Complete!")
        logger.info("=" * 60)
        logger.info("\n✅ All demos executed successfully")
        logger.info("\nFor more information, see:")
        logger.info("  • backend/app/services/graph_builder/CIRCULAR_DEPENDENCY_DETECTOR_README.md")
        logger.info("  • backend/tests/test_circular_dependency_detector.py")
        
    except Exception as e:
        logger.info("\n❌ Error running demo: {str(e)}")
        logger.info("\nNote: This demo requires a running Neo4j instance with data.")
        logger.info("To run with real data:")
        logger.info("  1. Start Neo4j database")
        logger.info("  2. Build a dependency graph using GraphBuilderService")
        logger.info("  3. Run this demo")


if __name__ == "__main__":
    asyncio.run(main())
