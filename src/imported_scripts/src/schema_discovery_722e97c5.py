from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import dlt
import mistune  # For better markdown parsing
import pandas as pd
from pydantic import BaseModel


class FileMetadata(BaseModel):
    """Metadata about the source file."""

    file_path: str
    file_type: str
    last_modified: datetime
    size_bytes: int
    encoding: str | None = None
    line_count: int | None = None
    has_headers: bool | None = None


class DataQualityMetrics(BaseModel):
    """Quality metrics for a data field."""

    completeness: float  # Percentage of non-null values
    uniqueness: float  # Percentage of unique values
    consistency: float  # Score based on pattern matching
    validity: float  # Score based on data type validation
    patterns: list[str]  # Common patterns found in the data
    anomalies: list[str]  # Detected anomalies
    sample_anomalies: list[str]  # Sample values that don't match patterns


class DataPattern(BaseModel):
    """Detected pattern in data."""

    pattern_type: str  # e.g., 'date', 'email', 'phone', 'number', 'text'
    regex: str  # The regex pattern that matches this type
    confidence: float  # Confidence score for this pattern
    examples: list[str]  # Example values that match this pattern


class DataPointMetadata(BaseModel):
    """Metadata about a discovered data point."""

    name: str
    data_type: str
    sample_values: list[str]
    first_seen: datetime
    last_seen: datetime
    frequency: int
    confidence: float
    possible_pii: bool
    possible_entity: bool
    source_files: list[str]
    quality_metrics: DataQualityMetrics | None = None
    detected_patterns: list[DataPattern] = []
    dlt_schema: dict[str, Any] | None = None


class SchemaDiscovery:
    def __init__(self) -> None:
        self.known_datapoints: dict[str, DataPointMetadata] = {}
        self.file_metadata: dict[str, FileMetadata] = {}
        self.pipeline = dlt.pipeline(
            pipeline_name="schema_discovery",
            destination="duckdb",
            dataset_name="discovered_schemas",
        )
        # Common data patterns
        self.patterns = {
            "email": (r"\b[\w\.-]+@[\w\.-]+\.\w+\b", "email"),
            "phone": (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "phone"),
            "date": (r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", "date"),
            "url": (r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*", "url"),
            "ip": (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "ip"),
            "currency": (r"\$\d+(?:\.\d{2})?", "currency"),
            "percentage": (r"\b\d+(?:\.\d+)?%\b", "percentage"),
            "credit_card": (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "credit_card"),
            "ssn": (r"\b\d{3}-\d{2}-\d{4}\b", "ssn"),
            "zip_code": (r"\b\d{5}(?:-\d{4})?\b", "zip_code"),
        }

    async def process_file(self, file_path: str | Path) -> list[DataPointMetadata]:
        """Process a single file and discover its schema."""
        file_path = Path(file_path)
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        # Store file metadata
        self.file_metadata[str(file_path)] = self._get_file_metadata(file_path)

        # Process based on file type
        if file_path.suffix.lower() == ".csv":
            return await self._process_csv(file_path)
        if file_path.suffix.lower() == ".md":
            return await self._process_markdown(file_path)
        if file_path.suffix.lower() == ".txt":
            return await self._process_text(file_path)
        msg = f"Unsupported file type: {file_path.suffix}"
        raise ValueError(msg)

    def _get_file_metadata(self, file_path: Path) -> FileMetadata:
        """Get metadata for a file."""
        stats = file_path.stat()

        # Try to detect encoding
        encoding = "utf-8"  # default
        try:
            with open(file_path, "rb") as f:
                import chardet

                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result["encoding"]
        except ImportError:
            pass  # chardet not installed

        # Count lines if file is not too large
        line_count = None
        if stats.st_size < 10_000_000:  # Only count lines for files < 10MB
            with open(file_path, encoding=encoding) as f:
                line_count = sum(1 for _ in f)

        return FileMetadata(
            file_path=str(file_path),
            file_type=file_path.suffix.lower()[1:],
            last_modified=datetime.fromtimestamp(stats.st_mtime),
            size_bytes=stats.st_size,
            encoding=encoding,
            line_count=line_count,
        )

    async def _process_csv(self, file_path: Path) -> list[DataPointMetadata]:
        """Process a CSV file."""
        # Try to read with pandas
        df = pd.read_csv(file_path)

        # Let dlt handle the schema evolution
        self.pipeline.run(
            df,
            table_name=f"data_{file_path.stem}",
            write_disposition="append",
        )

        # Update known datapoints
        new_points = []
        for column in df.columns:
            metadata = self._create_metadata_from_series(
                df[column],
                str(file_path),
            )
            if column not in self.known_datapoints:
                self.known_datapoints[column] = metadata
                new_points.append(metadata)
            else:
                self._update_metadata(
                    self.known_datapoints[column],
                    metadata,
                    str(file_path),
                )

        return new_points

    async def _process_markdown(self, file_path: Path) -> list[DataPointMetadata]:
        """Enhanced markdown processing with better table extraction."""
        with open(file_path, encoding=self.file_metadata[str(file_path)].encoding) as f:
            content = f.read()

        # Use mistune for better markdown parsing
        markdown = mistune.create_markdown(renderer=mistune.HTMLRenderer())
        html = markdown(content)

        # Extract tables using both HTML parsing and regex
        tables = self._extract_markdown_tables_advanced(content, html)
        new_points = []

        if tables:
            for _i, table in enumerate(tables):
                # Create a library record for each row
                for row in table:
                    # Clean up the data
                    name = row.get("Library Name", "").strip()
                    description = row.get("Description", "").strip()
                    url = row.get("URL", row.get("wURL", "")).strip()

                    if name and url:
                        metadata = DataPointMetadata(
                            name=name,
                            data_type="library",
                            sample_values=[url, description],
                            first_seen=datetime.now(),
                            last_seen=datetime.now(),
                            frequency=1,
                            confidence=1.0,
                            possible_pii=False,
                            possible_entity=True,
                            source_files=[str(file_path)],
                            quality_metrics=None,
                            detected_patterns=[],
                        )
                        new_points.append(metadata)

        return new_points

    def _extract_markdown_tables_advanced(self, content: str, html: str) -> list[dict]:
        """Advanced markdown table extraction using multiple methods."""
        tables = []

        # Method 1: Parse pipe-style markdown tables
        pipe_tables = self._extract_pipe_tables(content)
        if pipe_tables:
            tables.extend(pipe_tables)

        # Method 2: Parse HTML tables from mistune output
        html_tables = self._extract_html_tables(html)
        if html_tables:
            tables.extend(html_tables)

        # Method 3: Parse grid-style markdown tables
        grid_tables = self._extract_grid_tables(content)
        if grid_tables:
            tables.extend(grid_tables)

        return tables

    def _extract_pipe_tables(self, content: str) -> list[dict]:
        """Extract pipe-style markdown tables."""
        tables = []
        lines = content.split("\n")
        current_table = []
        in_table = False

        def clean_cell(cell: str) -> str:
            """Clean a cell value by removing markdown formatting."""
            # Remove bold formatting
            cell = cell.strip().replace("**", "").replace("w**", "")
            # Extract URL from markdown link [text](url)
            if "[" in cell and "](" in cell and cell.endswith(")"):
                return cell[cell.find("](") + 2 : -1]
            return cell

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                if not in_table:
                    in_table = True
                current_table.append(stripped)
            elif in_table and not stripped:
                if len(current_table) >= 2:  # Need at least header and separator
                    try:
                        # Process the table
                        rows = [
                            [clean_cell(cell) for cell in row.strip("|").split("|")]
                            for row in current_table
                        ]
                        # Remove separator row
                        if any("-" in cell for cell in rows[1]):
                            headers = rows[0]
                            data = rows[2:]
                            # Convert to list of dicts
                            table_data = [
                                {
                                    headers[i]: cell
                                    for i, cell in enumerate(row)
                                    if i < len(headers)
                                }
                                for row in data
                            ]
                            tables.append(table_data)
                    except Exception:
                        pass
                current_table = []
                in_table = False

        # Handle last table if it exists
        if in_table and len(current_table) >= 2:
            try:
                rows = [
                    [clean_cell(cell) for cell in row.strip("|").split("|")]
                    for row in current_table
                ]
                if any("-" in cell for cell in rows[1]):
                    headers = rows[0]
                    data = rows[2:]
                    table_data = [
                        {
                            headers[i]: cell
                            for i, cell in enumerate(row)
                            if i < len(headers)
                        }
                        for row in data
                    ]
                    tables.append(table_data)
            except Exception:
                pass

        return tables

    def _extract_html_tables(self, html: str) -> list[dict]:
        """Extract tables from HTML content."""
        # This is a placeholder - we'll need to implement proper HTML parsing
        # For now, return empty list as we're focusing on markdown tables
        return []

    def _extract_grid_tables(self, content: str) -> list[dict]:
        """Extract grid-style markdown tables."""
        # This is a placeholder - we'll implement if needed
        return []

    def _clean_column_name(self, column: str) -> str:
        """Clean column names to make them database-friendly."""
        # Remove special characters and extra whitespace
        clean = re.sub(r"[^\w\s-]", "", column)
        # Replace spaces and - with _
        clean = re.sub(r"[-\s]+", "_", clean)
        # Convert to lowercase
        clean = clean.lower()
        # Remove leading/trailing underscores
        clean = clean.strip("_")
        # Ensure it's not empty and doesn't start with a number
        if not clean:
            clean = "column"
        if clean[0].isdigit():
            clean = "col_" + clean
        return clean

    def _analyze_table_structure(self, df: pd.DataFrame) -> dict[str, dict]:
        """Analyze the structure of a table."""
        analysis = {}
        for column in df.columns:
            column_data = df[column].dropna()

            # Basic statistics
            stats = {
                "count": len(column_data),
                "unique_count": column_data.nunique(),
                "null_count": df[column].isna().sum(),
                "sample_values": column_data.head().tolist(),
            }

            # Infer data type
            if column_data.empty:
                data_type = "unknown"
            else:
                # Try to infer if it's a date
                try:
                    pd.to_datetime(column_data.iloc[0])
                    data_type = "date"
                except:
                    # Check if numeric
                    if pd.to_numeric(column_data, errors="coerce").notna().all():
                        data_type = "numeric"
                    else:
                        # Check if boolean-like
                        bool_values = {"true", "false", "yes", "no", "1", "0"}
                        if all(str(v).lower() in bool_values for v in column_data):
                            data_type = "boolean"
                        else:
                            data_type = "text"

            stats["inferred_type"] = data_type

            # Pattern analysis
            if data_type == "text":
                # Look for common patterns
                patterns = []
                for pattern_name, (regex, _) in self.patterns.items():
                    matches = column_data.astype(str).str.match(regex).sum()
                    if matches > 0:
                        patterns.append(
                            {
                                "name": pattern_name,
                                "match_count": matches,
                                "match_percentage": matches / len(column_data),
                            },
                        )
                stats["patterns"] = patterns

            # Quality metrics
            stats["completeness"] = 1 - (stats["null_count"] / len(df))
            stats["uniqueness"] = (
                stats["unique_count"] / len(column_data) if len(column_data) > 0 else 0
            )

            analysis[column] = stats

        return analysis

    def _looks_like_entity(self, series: pd.Series) -> bool:
        """Check if a series looks like it contains entity data."""
        # Drop NA values and convert to string
        values = series.dropna().astype(str)
        if len(values) == 0:
            return False

        # Check for common entity indicators in column name
        entity_keywords = {
            "name",
            "id",
            "identifier",
            "key",
            "code",
            "symbol",
            "ticker",
        }
        if any(keyword in str(series.name).lower() for keyword in entity_keywords):
            return True

        # Check if values follow common entity patterns
        entity_patterns = [
            r"^[A-Z]{2,5}$",  # Stock symbols, currency codes
            r"^[A-Z0-9]{6,12}$",  # IDs, product codes
            r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$",  # Proper names
            r"^\w+\.\w+$",  # Dotted identifiers
            r"^[A-Z0-9-]{3,}$",  # Dashed identifiers
        ]

        # Check if a significant portion of values match entity patterns
        pattern_matches = 0
        for pattern in entity_patterns:
            matches = values.str.match(pattern).sum()
            if matches / len(values) > 0.8:  # 80% threshold
                return True
            pattern_matches += matches

        # If more than 50% of values match any entity pattern
        if pattern_matches / len(values) > 0.5:
            return True

        # Check uniqueness - entities tend to be unique
        if len(values.unique()) / len(values) > 0.8:  # 80% unique values
            # Additional check for reasonable length
            avg_length = values.str.len().mean()
            if 2 <= avg_length <= 50:  # Most entity values are between 2 and 50 chars
                return True

        return False

    def _update_metadata(
        self,
        existing: DataPointMetadata,
        new: DataPointMetadata,
        source_file: str,
    ) -> None:
        """Update existing metadata with new information."""
        # Update timestamps
        existing.first_seen = min(existing.first_seen, new.first_seen)
        existing.last_seen = max(existing.last_seen, new.last_seen)

        # Update frequency and confidence
        existing.frequency += new.frequency
        existing.confidence = (existing.confidence + new.confidence) / 2

        # Update sample values (keep unique values, max 10)
        combined_samples = list(set(existing.sample_values + new.sample_values))
        existing.sample_values = combined_samples[:10]

        # Update source files
        if source_file not in existing.source_files:
            existing.source_files.append(source_file)

        # Update quality metrics if available
        if new.quality_metrics:
            if not existing.quality_metrics:
                existing.quality_metrics = new.quality_metrics
            else:
                # Average the metrics
                existing.quality_metrics.completeness = (
                    existing.quality_metrics.completeness
                    + new.quality_metrics.completeness
                ) / 2
                existing.quality_metrics.uniqueness = (
                    existing.quality_metrics.uniqueness + new.quality_metrics.uniqueness
                ) / 2
                existing.quality_metrics.consistency = (
                    existing.quality_metrics.consistency
                    + new.quality_metrics.consistency
                ) / 2
                existing.quality_metrics.validity = (
                    existing.quality_metrics.validity + new.quality_metrics.validity
                ) / 2

                # Combine patterns and anomalies
                existing.quality_metrics.patterns = list(
                    set(
                        existing.quality_metrics.patterns
                        + new.quality_metrics.patterns,
                    ),
                )
                existing.quality_metrics.anomalies = list(
                    set(
                        existing.quality_metrics.anomalies
                        + new.quality_metrics.anomalies,
                    ),
                )
                existing.quality_metrics.sample_anomalies = list(
                    set(
                        existing.quality_metrics.sample_anomalies
                        + new.quality_metrics.sample_anomalies,
                    ),
                )[
                    :10
                ]  # Keep max 10 sample anomalies

        # Update detected patterns
        if new.detected_patterns:
            pattern_map = {p.pattern_type: p for p in existing.detected_patterns}
            for pattern in new.detected_patterns:
                if pattern.pattern_type in pattern_map:
                    # Average confidence for existing patterns
                    pattern_map[pattern.pattern_type].confidence = (
                        pattern_map[pattern.pattern_type].confidence
                        + pattern.confidence
                    ) / 2
                    # Combine examples (keep unique, max 5)
                    combined_examples = list(
                        set(
                            pattern_map[pattern.pattern_type].examples
                            + pattern.examples,
                        ),
                    )
                    pattern_map[pattern.pattern_type].examples = combined_examples[:5]
                else:
                    existing.detected_patterns.append(pattern)

        # Update dlt schema if available
        if new.dlt_schema:
            existing.dlt_schema = new.dlt_schema

    def _analyze_data_patterns(self, series: pd.Series) -> list[DataPattern]:
        """Analyze data patterns in a series."""
        patterns = []
        values = series.dropna().astype(str).tolist()

        for regex, pattern_type in self.patterns.values():
            matches = [v for v in values if re.match(regex, v)]
            if matches:
                confidence = len(matches) / len(values)
                if confidence > 0.1:  # Only include if pattern matches >10% of values
                    patterns.append(
                        DataPattern(
                            pattern_type=pattern_type,
                            regex=regex,
                            confidence=confidence,
                            examples=matches[:5],
                        ),
                    )

        # Detect custom patterns
        if not patterns:
            custom_pattern = self._detect_custom_pattern(values)
            if custom_pattern:
                patterns.append(custom_pattern)

        return patterns

    def _calculate_quality_metrics(self, series: pd.Series) -> DataQualityMetrics:
        """Calculate data quality metrics for a series."""
        total_count = len(series)
        non_null_count = series.count()
        unique_count = series.nunique()

        # Basic metrics
        completeness = non_null_count / total_count if total_count > 0 else 0
        uniqueness = unique_count / total_count if total_count > 0 else 0

        # Pattern consistency
        patterns = self._analyze_data_patterns(series)
        pattern_coverage = sum(p.confidence for p in patterns)
        consistency = pattern_coverage / len(patterns) if patterns else 0

        # Validity check based on data type
        validity = self._check_data_validity(series)

        # Detect anomalies
        anomalies, sample_anomalies = self._detect_anomalies(series)

        return DataQualityMetrics(
            completeness=completeness,
            uniqueness=uniqueness,
            consistency=consistency,
            validity=validity,
            patterns=[p.pattern_type for p in patterns],
            anomalies=anomalies,
            sample_anomalies=sample_anomalies,
        )

    def _detect_custom_pattern(self, values: list[str]) -> DataPattern | None:
        """Detect custom patterns in data."""
        if not values:
            return None

        # Try to detect common patterns
        patterns = []
        for value in values[:100]:  # Sample first 100 values
            pattern = self._value_to_pattern(value)
            patterns.append(pattern)

        # Find most common pattern
        pattern_counts = Counter(patterns)
        if pattern_counts:
            most_common = pattern_counts.most_common(1)[0]
            pattern, count = most_common
            confidence = count / len(patterns)

            if confidence > 0.5:  # If pattern appears in >50% of values
                return DataPattern(
                    pattern_type="custom",
                    regex=pattern,
                    confidence=confidence,
                    examples=[
                        v for v in values[:5] if self._value_to_pattern(v) == pattern
                    ],
                )

        return None

    def _value_to_pattern(self, value: str) -> str:
        """Convert a value to a pattern representation."""
        pattern = ""
        for char in str(value):
            if char.isalpha():
                pattern += "a"
            elif char.isdigit():
                pattern += "9"
            else:
                pattern += char
        return pattern

    def _check_data_validity(self, series: pd.Series) -> float:
        """Check data validity based on type."""
        if series.empty:
            return 0.0

        dtype = series.dtype
        valid_count = 0
        total_count = len(series)

        if dtype in ["int64", "float64"]:
            # Check if numeric values are within reasonable ranges
            valid_count = series.between(
                series.mean() - 3 * series.std(),
                series.mean() + 3 * series.std(),
            ).sum()
        elif dtype == "object":
            # For strings, check if they match any known patterns
            patterns = self._analyze_data_patterns(series)
            if patterns:
                valid_count = sum(
                    1
                    for v in series.dropna()
                    if any(re.match(p.regex, str(v)) for p in patterns)
                )

        return valid_count / total_count if total_count > 0 else 0.0

    def _detect_anomalies(self, series: pd.Series) -> tuple[list[str], list[str]]:
        """Detect anomalies in the data."""
        anomalies = []
        sample_anomalies = []

        if series.empty:
            return anomalies, sample_anomalies

        # Statistical anomalies for numeric data
        if series.dtype in ["int64", "float64"]:
            mean = series.mean()
            std = series.std()
            outliers = series[abs(series - mean) > 3 * std]
            if not outliers.empty:
                anomalies.append(f"Found {len(outliers)} statistical outliers")
                sample_anomalies.extend(outliers.head().astype(str).tolist())

        # Pattern anomalies for string data
        elif series.dtype == "object":
            patterns = self._analyze_data_patterns(series)
            if patterns:
                non_matching = [
                    v
                    for v in series.dropna()
                    if not any(re.match(p.regex, str(v)) for p in patterns)
                ]
                if non_matching:
                    anomalies.append(
                        f"Found {len(non_matching)} values not matching common patterns",
                    )
                    sample_anomalies.extend(non_matching[:5])

        return anomalies, sample_anomalies

    def _create_metadata_from_series(
        self,
        series: pd.Series,
        source_file: str,
        table_analysis: dict | None = None,
    ) -> DataPointMetadata:
        """Create enhanced metadata from a pandas series."""
        patterns = self._analyze_data_patterns(series)
        quality_metrics = self._calculate_quality_metrics(series)

        return DataPointMetadata(
            name=series.name,
            data_type=str(series.dtype),
            sample_values=series.dropna().unique()[:5].tolist(),
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            frequency=len(series),
            confidence=quality_metrics.validity,
            possible_pii=any(
                p.pattern_type in ["email", "phone", "ssn", "credit_card"]
                for p in patterns
            ),
            possible_entity=self._looks_like_entity(series),
            source_files=[source_file],
            quality_metrics=quality_metrics,
            detected_patterns=patterns,
        )

    async def _process_text(self, file_path: Path) -> list[DataPointMetadata]:
        """Process a text file."""
        with open(file_path, encoding=self.file_metadata[str(file_path)].encoding) as f:
            content = f.read()

        # Try to detect if it's a structured text file (e.g., pipe-separated)
        if "|" in content:
            # Try to parse as pipe-separated
            try:
                df = pd.read_csv(file_path, sep="|")
                return await self._process_csv(file_path)  # Reuse CSV processing
            except:
                pass

        # For now, just store as raw text
        df = pd.DataFrame({"content": [content]})
        self.pipeline.run(
            df,
            table_name=f"text_{file_path.stem}",
            write_disposition="append",
        )

        return []  # No structured data points found

    def _extract_markdown_tables(self, content: str) -> list[dict]:
        """Extract tables from markdown content."""
        # Simple markdown table detection (can be enhanced)
        table_pattern = r"\|.*\|[\r\n]\|[-:\s|]*\|[\r\n](?:\|.*\|[\r\n])*"
        tables = []

        for table_match in re.finditer(table_pattern, content, re.MULTILINE):
            table_str = table_match.group(0)
            lines = table_str.strip().split("\n")

            # Extract headers
            headers = [cell.strip() for cell in lines[0].split("|")[1:-1]]

            # Skip separator line
            data = []
            for line in lines[2:]:
                if line.strip():
                    row = [cell.strip() for cell in line.split("|")[1:-1]]
                    data.append(dict(zip(headers, row, strict=False)))

            if data:
                tables.append(data)

        return tables

    def get_analysis(self) -> dict[str, Any]:
        """Get analysis of discovered data."""
        return {
            "files": self.file_metadata,
            "datapoints": self.known_datapoints,
            "summary": {
                "total_files": len(self.file_metadata),
                "total_datapoints": len(self.known_datapoints),
                "file_types": {
                    ft: sum(
                        1 for fm in self.file_metadata.values() if fm.file_type == ft
                    )
                    for ft in {fm.file_type for fm in self.file_metadata.values()}
                },
            },
        }
