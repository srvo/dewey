"""Data analysis and schema recommendation agent.

This module provides tools for analyzing data structures and recommending database schema changes.
It includes functionality for:
- Data structure analysis
- Schema recommendations
- Data quality assessment
- Integration planning
- Impact analysis

The main class is DataIngestionAgent which provides methods to:
- Analyze data structure and content
- Recommend optimal table structures
- Plan necessary schema changes
- Generate migration plans

Key Features:
- Automatic data type inference
- Schema normalization recommendations
- Data quality metrics
- Migration plan generation
- Impact analysis for schema changes
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import structlog
from pydantic import BaseModel, Field

from ..base import SyzygyAgent

logger = structlog.get_logger(__name__)


class ColumnAnalysis(BaseModel):
    """Analysis of a data column.

    This model represents the analysis of a single column in a dataset.
    It includes metadata and statistics about the column's content and structure.

    Attributes:
    ----------
        name (str): Name of the column
        inferred_type (str): Data type inferred from the column's content
        nullable (bool): Whether the column contains null values
        unique_ratio (float): Ratio of unique values to total values
        sample_values (List[Any]): Sample values from the column
        statistical_summary (Optional[Dict[str, Any]]): Statistical summary for numeric columns
        suggested_constraints (List[str]): Suggested database constraints for the column

    Example:
    -------
        >>> column = ColumnAnalysis(
        ...     name="age",
        ...     inferred_type="int",
        ...     nullable=False,
        ...     unique_ratio=0.95,
        ...     sample_values=[25, 30, 35],
        ...     statistical_summary={"mean": 30.5, "std": 5.0},
        ...     suggested_constraints=["NOT NULL", "CHECK(age > 0)"]
        ... )

    """

    name: str
    inferred_type: str
    nullable: bool
    unique_ratio: float
    sample_values: list[Any]
    statistical_summary: dict[str, Any] | None
    suggested_constraints: list[str]


class TableRecommendation(BaseModel):
    """Recommendation for table structure.

    This model represents a recommended database table structure based on data analysis.
    It includes details about the table's schema, constraints, and optimization strategies.

    Attributes:
    ----------
        table_name (str): Recommended name for the table
        columns (List[Dict[str, Any]]): List of column definitions
        primary_key (Optional[str]): Recommended primary key column
        indexes (List[str]): List of recommended indexes
        foreign_keys (List[Dict[str, str]]): List of foreign key relationships
        partitioning (Optional[str]): Recommended partitioning strategy
        estimated_size (str): Estimated table size (e.g., 'small', 'medium', 'large')

    Example:
    -------
        >>> recommendation = TableRecommendation(
        ...     table_name="users",
        ...     columns=[{"name": "id", "type": "int", "constraints": ["PRIMARY KEY"]}],
        ...     primary_key="id",
        ...     indexes=["created_at"],
        ...     foreign_keys=[{"column": "org_id", "references": "organizations(id)"}],
        ...     partitioning="by_month(created_at)",
        ...     estimated_size="medium"
        ... )

    """

    table_name: str
    columns: list[dict[str, Any]]
    primary_key: str | None
    indexes: list[str]
    foreign_keys: list[dict[str, str]]
    partitioning: str | None
    estimated_size: str


class SchemaChange(BaseModel):
    """Recommended schema change."""

    type: str  # new_table, alter_table, add_column, etc.
    target: str
    definition: dict[str, Any]
    reason: str
    impact: str
    priority: int = Field(ge=1, le=5)


class DataIngestionAgent(SyzygyAgent):
    """Agent for analyzing data and recommending schema changes.

    Features:
    - Data structure analysis
    - Schema recommendations
    - Data quality assessment
    - Integration planning
    - Impact analysis
    """

    def __init__(self) -> None:
        """Initialize the data ingestion agent."""
        super().__init__(
            task_type="data_analysis",
            model="qwen-coder-32b",  # Use code-specialized model
        )

    async def analyze_data(
        self,
        data: Any,
        context: str | None = None,
    ) -> list[ColumnAnalysis]:
        """Analyze data structure and content.

        Args:
        ----
            data: Data to analyze (file path, DataFrame, dict, etc.)
            context: Optional context about the data

        Returns:
        -------
            List of column analyses

        """
        # Convert data to DataFrame if needed
        if isinstance(data, (str, Path)):
            if str(data).endswith(".csv"):
                df = pd.read_csv(data)
            elif str(data).endswith(".json"):
                df = pd.read_json(data)
            else:
                msg = f"Unsupported file type: {data}"
                raise ValueError(msg)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            msg = f"Unsupported data type: {type(data)}"
            raise ValueError(msg)

        analyses = []
        for column in df.columns:
            series = df[column]

            analysis = ColumnAnalysis(
                name=column,
                inferred_type=str(series.dtype),
                nullable=series.isnull().any(),
                unique_ratio=series.nunique() / len(series),
                sample_values=series.head().tolist(),
                statistical_summary=(
                    series.describe().to_dict() if series.dtype.kind in "iuf" else None
                ),
                suggested_constraints=[],
            )

            # Get AI suggestions for constraints
            result = await self.run(
                messages=[
                    {
                        "role": "system",
                        "content": f"""Analyze this column and suggest constraints:

Column: {column}
Type: {analysis.inferred_type}
Nullable: {analysis.nullable}
Unique ratio: {analysis.unique_ratio}
Samples: {analysis.sample_values}
Stats: {analysis.statistical_summary}

Context: {context or "None"}

Suggest appropriate constraints considering:
1. Data type validation
2. Value ranges
3. Patterns
4. Business rules
5. Data quality""",  ## Data generated by LLMs should never be seen as the same quality as data generated by Sloane (srvo/me/user)
                    },
                ],
                model="qwen-coder-32b",
            )

            analysis.suggested_constraints = result["constraints"]
            analyses.append(analysis)

        return analyses

    async def recommend_table_structure(
        self,
        analyses: list[ColumnAnalysis],
        existing_tables: list[str] | None = None,
    ) -> TableRecommendation:
        """Recommend optimal table structure.

        Args:
        ----
            analyses: Column analyses
            existing_tables: Optional list of existing table names

        Returns:
        -------
            Table structure recommendation

        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Recommend table structure based on these columns:

Columns:
{[a.dict() for a in analyses]}

Existing Tables: {existing_tables or []}

Consider:
1. Normalization
2. Data types
3. Constraints
4. Indexing
5. Partitioning
6. Foreign keys""",
                },
            ],
            model="qwen-coder-32b",
            metadata={
                "column_count": len(analyses),
                "existing_tables": existing_tables,
            },
        )

        return TableRecommendation(**result)

    async def plan_schema_changes(
        self,
        recommendation: TableRecommendation,
        existing_schema: dict[str, Any] | None = None,
    ) -> list[SchemaChange]:
        """Plan necessary schema changes.

        Args:
        ----
            recommendation: Table recommendation
            existing_schema: Optional existing schema definition

        Returns:
        -------
            List of recommended changes

        """
        result = await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Plan schema changes based on recommendation:

Recommendation:
{recommendation.dict()}

Existing Schema:
{existing_schema or "None"}

Consider:
1. Data preservation
2. Backward compatibility
3. Migration complexity
4. Performance impact
5. Deployment strategy""",
                },
            ],
            model="qwen-coder-32b",
            metadata={
                "recommendation": recommendation.dict(),
                "has_existing": bool(existing_schema),
            },
        )

        return [SchemaChange(**change) for change in result["changes"]]

    async def generate_migration(self, changes: list[SchemaChange]) -> dict[str, Any]:
        """Generate migration plan for schema changes.

        Args:
        ----
            changes: List of schema changes

        Returns:
        -------
            Migration plan with SQL and rollback

        """
        return await self.run(
            messages=[
                {
                    "role": "system",
                    "content": f"""Generate migration plan for these changes:

Changes:
{[c.dict() for c in changes]}

Include:
1. Forward migration SQL
2. Rollback SQL
3. Data migration steps
4. Validation queries
5. Deployment notes""",
                },
            ],
            model="qwen-coder-32b",
            metadata={"change_count": len(changes)},
        )
