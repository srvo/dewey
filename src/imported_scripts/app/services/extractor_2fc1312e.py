import logging
from datetime import datetime

from app.engine import get_query_engine
from app.services.model import IMPORTS

logger = logging.getLogger("uvicorn")


class InvalidModelCode(Exception):
    pass


class ExtractorService:
    @staticmethod
    def _parse_code(model_code: str):
        try:
            python_code = f"{IMPORTS}\n\n{model_code}"
            logger.debug(python_code)
            namespace = {}
            exec(python_code, namespace)
            # using the last object that the user defined in `model_code` as pydantic class
            pydantic_class = namespace[list(namespace.keys())[-1]]
            class_name = pydantic_class.__name__
            logger.info(f"Using Pydantic class {class_name} for extraction")
            return pydantic_class
        except Exception as e:
            logger.exception(e)
            raise InvalidModelCode from e

    @classmethod
    async def extract(cls, query: str, model_code: str) -> str:
        schema_model = cls._parse_code(model_code)

        # Add financial context to the query
        financial_context = """
        You are a financial analysis assistant. When extracting data:
        1. Identify and extract key financial metrics
        2. Maintain currency consistency
        3. Preserve date formats
        4. Handle financial terminology accurately
        5. Extract tabular data when present
        """
        enhanced_query = f"{financial_context}\n\n{query}"

        # Create a query engine using that returns responses in the format of the schema
        query_engine = get_query_engine(schema_model)
        response = await query_engine.aquery(enhanced_query)
        output_data = response.response.dict()

        # Add financial metadata and tags to the response
        if hasattr(response, "metadata"):
            from app.services.tagging import TaggingEngine

            financial_metadata = {
                "source_document": response.metadata.get("file_name"),
                "extraction_date": datetime.now().isoformat(),
                "confidence_score": response.score,
                "tags": TaggingEngine.apply_tags(response.metadata),
            }

            # Calculate financial ratios if data available
            if response.metadata.get("total_assets") and response.metadata.get(
                "total_liabilities",
            ):
                financial_metadata["financial_ratios"] = {
                    "debt_to_equity": response.metadata["total_liabilities"]
                    / response.metadata["net_worth"],
                    "current_ratio": response.metadata["total_assets"]
                    / response.metadata["total_liabilities"],
                }

            output_data["financial_metadata"] = financial_metadata

        return schema_model(**output_data).model_dump_json(indent=2)
