from ai_helper.client import AIClient

from .entity_resolver import EntityResolver
from .pii_handler import PIIHandler
from .validation import DataValidationConfig


class DataPipeline:
    def __init__(self, config: DataValidationConfig, ai_client: AIClient) -> None:
        self.config = config
        self.entity_resolver = EntityResolver(config.entity_mappings)
        self.pii_handler = PIIHandler(config.pii_patterns)
        self.ai_client = ai_client

    async def process_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Process data through the pipeline."""
        # 1. Validate data
        validation = self._validate_data(data)
        if not validation.is_valid:
            msg = f"Data validation failed: {validation.errors}"
            raise ValueError(msg)

        # 2. Resolve entities
        data = await self.entity_resolver.resolve_entities(data, "entity_column")

        # 3. Handle PII
        data["text_clean"] = data["text"].apply(
            lambda x: self.pii_handler.detect_and_redact(x)[0],
        )

        # 4. AI Analysis
        # Only analyze clean, validated data
        analysis_results = await self.ai_client.analyze_batch(data["text_clean"])
        data["ai_analysis"] = analysis_results

        return data
