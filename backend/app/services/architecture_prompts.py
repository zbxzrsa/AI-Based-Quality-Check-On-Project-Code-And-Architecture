"""
Architecture Analysis Prompts for LLM

This module contains prompts for analyzing codebase architecture and generating
architectural summaries using AI models like qwen2.5-coder.
"""

ARCHITECTURAL_PURPOSE_PROMPT = """
Analyze the following codebase metrics and provide a concise architectural purpose summary:

Repository Information:
- Repository URL: {repository_url}
- Analysis Date: {analysis_date}

Codebase Metrics:
- Total Files: {total_files}
- Total Classes: {total_classes}
- Total Functions: {total_functions}
- Average Cyclomatic Complexity: {avg_complexity}
- Coupling Score: {coupling} (0-100, lower is better)
- Cohesion Score: {cohesion} (0-100, higher is better)
- Code Smells Detected: {code_smells}
- Primary File Types: {file_types}

Code Structure Analysis:
{code_structure_summary}

Please provide a comprehensive architectural analysis with the following sections:

1. **Architectural Purpose** (2-3 sentences):
   What does this codebase appear to be for? What is its primary function or domain?

2. **Architectural Style** (identify patterns):
   - What architectural patterns are evident?
   - Is it layered, microservices, monolithic, etc.?
   - What design principles are followed?

3. **Code Quality Assessment**:
   - Overall code quality based on metrics
   - Complexity concerns
   - Maintainability assessment

4. **Technology Stack**:
   - Primary technologies used
   - Framework choices
   - Language-specific patterns

5. **Potential Issues**:
   - Architectural anti-patterns
   - Maintainability concerns
   - Performance considerations

6. **Strengths**:
   - Good architectural decisions
   - Well-structured components
   - Best practices followed

Format your response as a structured JSON object with the following keys:
- "architectural_purpose": string
- "architectural_style": string
- "code_quality": string
- "technology_stack": string
- "potential_issues": array of strings
- "strengths": array of strings
- "confidence_score": number (1-10)

Be concise but thorough in your analysis. Focus on architectural insights rather than implementation details.

IMPORTANT: Respond with ONLY the JSON object. Do not include any additional text, explanations, or formatting before or after the JSON.
"""

ARCHITECTURAL_PATTERNS_PROMPT = """
Based on the following codebase characteristics, identify the most likely architectural patterns and design principles being used:

Codebase Characteristics:
- Total Classes: {total_classes}
- Total Functions: {total_functions}
- Average Complexity: {avg_complexity}
- Coupling: {coupling}
- Cohesion: {cohesion}
- File Types: {file_types}
- Class Distribution: {class_distribution}

Code Structure:
{code_structure}

Please identify and explain the following architectural patterns if present:
1. **Layered Architecture** - Are there clear separation of concerns?
2. **MVC/MVVM** - Are there clear model-view-controller patterns?
3. **Microservices** - Are there service boundaries evident?
4. **Event-Driven** - Are there event patterns or message passing?
5. **Domain-Driven Design** - Are there domain models and bounded contexts?
6. **Repository Pattern** - Are there data access abstractions?
7. **Dependency Injection** - Are dependencies properly injected?
8. **Factory/Builder** - Are creational patterns used?
9. **Strategy/Command** - Are behavioral patterns evident?
10. **Adapter/Facade** - Are structural patterns present?

For each pattern identified, provide:
- Pattern name
- Evidence in the codebase
- How well it's implemented (1-10 scale)
- Benefits it provides

Return your response as a JSON array of pattern objects with the structure:
[
  {
    "pattern": "Pattern Name",
    "evidence": "Specific evidence from codebase",
    "implementation_quality": number,
    "benefits": "Benefits provided by this pattern"
  }
]

IMPORTANT: Respond with ONLY the JSON array. Do not include any additional text, explanations, or formatting before or after the JSON.
"""

CODE_QUALITY_ANALYSIS_PROMPT = """
Perform a comprehensive code quality analysis based on the following metrics and code structure:

Metrics:
- Cyclomatic Complexity: {complexity}
- Coupling: {coupling}
- Cohesion: {cohesion}
- Code Smells: {code_smells}
- Total Files: {total_files}

Code Structure:
{code_structure}

Please analyze and report on the following aspects:

1. **Complexity Analysis**:
   - Are complexity metrics within acceptable ranges?
   - Which components are most complex?
   - Recommendations for complexity reduction

2. **Maintainability Assessment**:
   - How maintainable is this codebase?
   - What makes it easy or difficult to maintain?
   - Suggestions for improving maintainability

3. **Testability**:
   - How testable is the current architecture?
   - Are dependencies properly decoupled?
   - Recommendations for improving testability

4. **Performance Considerations**:
   - Any performance bottlenecks evident?
   - Algorithmic complexity concerns?
   - Memory usage patterns?

5. **Security Considerations**:
   - Any obvious security concerns in architecture?
   - Input validation patterns?
   - Authentication/authorization patterns?

6. **Code Smells and Anti-patterns**:
   - What code smells are present?
   - Any architectural anti-patterns?
   - Specific examples and fixes

Provide your analysis as a JSON object with the following structure:
{
  "complexity_analysis": string,
  "maintainability_score": number (1-10),
  "maintainability_factors": array of strings,
  "testability_score": number (1-10),
  "testability_factors": array of strings,
  "performance_considerations": string,
  "security_considerations": string,
  "code_smells": array of objects,
  "recommendations": array of strings
}

Where each code_smell object has:
{
  "smell": "Name of the code smell",
  "description": "Description of the issue",
  "severity": "Low/Medium/High",
  "location": "Where this smell is found",
  "suggestion": "How to fix it"
}

IMPORTANT: Respond with ONLY the JSON object. Do not include any additional text, explanations, or formatting before or after the JSON.
"""

ARCHITECTURAL_DRIFT_DETECTION_PROMPT = """
Compare the current codebase architecture against the expected architectural patterns and identify any architectural drift.

Expected Architecture (Golden Standard):
{golden_standard}

Current Codebase Analysis:
- Total Files: {total_files}
- Total Classes: {total_classes}
- File Types: {file_types}
- Coupling: {coupling}
- Cohesion: {cohesion}

Current Architecture Patterns Detected:
{current_patterns}

Code Structure:
{code_structure}

Please identify and report on the following types of architectural drift:

1. **Layer Violations**:
   - Components accessing layers they shouldn't
   - Cross-layer dependencies
   - Violation of separation of concerns

2. **Pattern Deviations**:
   - Incomplete implementation of expected patterns
   - Misuse of architectural patterns
   - Missing pattern implementations

3. **Dependency Issues**:
   - Circular dependencies
   - Tight coupling where loose coupling is expected
   - Missing dependency abstractions

4. **Structural Drift**:
   - Files in wrong locations
   - Missing expected components
   - Unexpected architectural elements

5. **Quality Drift**:
   - Degradation in code quality metrics
   - Increased complexity beyond thresholds
   - Decreased testability

For each drift detected, provide:
- Type of drift
- Severity (Low/Medium/High)
- Location in codebase
- Impact on architecture
- Suggested remediation

Return your analysis as a JSON object with the following structure:
{
  "drift_summary": {
    "total_drifts": number,
    "high_severity": number,
    "medium_severity": number,
    "low_severity": number
  },
  "layer_violations": array of objects,
  "pattern_deviations": array of objects,
  "dependency_issues": array of objects,
  "structural_drift": array of objects,
  "quality_drift": array of objects,
  "recommendations": array of strings
}

Each drift object should have:
{
  "type": "Type of drift",
  "severity": "Low/Medium/High",
  "location": "Where drift is found",
  "impact": "Impact on architecture",
  "remediation": "Suggested fix"
}

IMPORTANT: Respond with ONLY the JSON object. Do not include any additional text, explanations, or formatting before or after the JSON.
"""

CLUSTERING_COEFFICIENT_ANALYSIS_PROMPT = """
Analyze the codebase dependency graph and calculate clustering coefficient metrics to assess architectural coupling and modularity.

Dependency Graph Analysis:
{dependency_graph}

Codebase Metrics:
- Total Components: {total_components}
- Total Dependencies: {total_dependencies}
- Average Component Size: {avg_component_size}

Please perform the following analysis:

1. **Clustering Coefficient Calculation**:
   - Calculate global clustering coefficient
   - Calculate average local clustering coefficient
   - Identify clusters/modules with high internal connectivity

2. **Modularity Assessment**:
   - How well modularized is the codebase?
   - Are there clear module boundaries?
   - What is the coupling between modules?

3. **Architectural Insights**:
   - Is the codebase becoming "spaghetti code"?
   - Are there architectural hotspots?
   - How does the clustering compare to architectural expectations?

4. **Risk Assessment**:
   - High-risk components (highly connected)
   - Components that could cause cascading failures
   - Areas that need refactoring for better modularity

Please provide specific metrics and thresholds:
- Global clustering coefficient: [value]
- Average local clustering coefficient: [value]
- Number of identified clusters: [number]
- Average cluster size: [value]
- Inter-cluster coupling: [value]
- Intra-cluster coupling: [value]

Return your analysis as a JSON object with the following structure:
{
  "clustering_metrics": {
    "global_coefficient": number,
    "average_local_coefficient": number,
    "num_clusters": number,
    "avg_cluster_size": number
  },
  "modularity_assessment": {
    "modularity_score": number (0-1),
    "module_boundaries_clear": boolean,
    "inter_cluster_coupling": number,
    "intra_cluster_coupling": number
  },
  "architectural_insights": string,
  "risk_assessment": {
    "high_risk_components": array of strings,
    "cascading_failure_risks": array of strings,
    "refactoring_priorities": array of strings
  },
  "recommendations": array of strings
}

Include specific recommendations for improving modularity and reducing architectural risks.

IMPORTANT: Respond with ONLY the JSON object. Do not include any additional text, explanations, or formatting before or after the JSON.
"""

def format_architectural_purpose_prompt(metrics: dict, code_structure: str) -> str:
    """Format the architectural purpose prompt with actual metrics."""
    return ARCHITECTURAL_PURPOSE_PROMPT.format(
        repository_url=metrics.get('repository_url', 'Unknown'),
        analysis_date=metrics.get('analysis_date', 'Unknown'),
        total_files=metrics.get('total_files', 0),
        total_classes=metrics.get('total_classes', 0),
        total_functions=metrics.get('total_functions', 0),
        avg_complexity=metrics.get('avg_complexity', 0),
        coupling=metrics.get('coupling', 0),
        cohesion=metrics.get('cohesion', 0),
        code_smells=metrics.get('code_smells', 0),
        file_types=', '.join(metrics.get('file_types', [])),
        code_structure_summary=code_structure
    )

def format_architectural_patterns_prompt(metrics: dict, code_structure: str) -> str:
    """Format the architectural patterns prompt with actual metrics."""
    return ARCHITECTURAL_PATTERNS_PROMPT.format(
        total_classes=metrics.get('total_classes', 0),
        total_functions=metrics.get('total_functions', 0),
        avg_complexity=metrics.get('avg_complexity', 0),
        coupling=metrics.get('coupling', 0),
        cohesion=metrics.get('cohesion', 0),
        file_types=', '.join(metrics.get('file_types', [])),
        class_distribution=metrics.get('class_distribution', 'Unknown'),
        code_structure=code_structure
    )

def format_code_quality_prompt(metrics: dict, code_structure: str) -> str:
    """Format the code quality analysis prompt with actual metrics."""
    return CODE_QUALITY_ANALYSIS_PROMPT.format(
        complexity=metrics.get('complexity', 0),
        coupling=metrics.get('coupling', 0),
        cohesion=metrics.get('cohesion', 0),
        code_smells=metrics.get('code_smells', 0),
        total_files=metrics.get('total_files', 0),
        code_structure=code_structure
    )

def format_drift_detection_prompt(golden_standard: str, metrics: dict, current_patterns: str, code_structure: str) -> str:
    """Format the architectural drift detection prompt."""
    return ARCHITECTURAL_DRIFT_DETECTION_PROMPT.format(
        golden_standard=golden_standard,
        total_files=metrics.get('total_files', 0),
        total_classes=metrics.get('total_classes', 0),
        file_types=', '.join(metrics.get('file_types', [])),
        coupling=metrics.get('coupling', 0),
        cohesion=metrics.get('cohesion', 0),
        current_patterns=current_patterns,
        code_structure=code_structure
    )

def format_clustering_analysis_prompt(dependency_graph: str, metrics: dict) -> str:
    """Format the clustering coefficient analysis prompt."""
    return CLUSTERING_COEFFICIENT_ANALYSIS_PROMPT.format(
        dependency_graph=dependency_graph,
        total_components=metrics.get('total_components', 0),
        total_dependencies=metrics.get('total_dependencies', 0),
        avg_component_size=metrics.get('avg_component_size', 0)
    )
