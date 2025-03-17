import logging
import ast
from datetime import datetime
from types import ModuleType
from typing import Type
from pydantic import BaseModel

from app.engine import get_query_engine
from app.services.model import IMPORTS

logger = logging.getLogger("uvicorn")


class InvalidModelCode(Exception):
    pass


class ExtractorService:
    @staticmethod
    def _validate_model_code(model_code: str) -> ast.Module:
        """Parse and validate model code using AST."""
        try:
            tree = ast.parse(model_code)
        except SyntaxError as e:
            raise InvalidModelCode(f"Invalid Python syntax: {e}") from e

        # Validate only contains class definitions with BaseModel inheritance
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
                raise InvalidModelCode("Imports and function definitions are not allowed")
            if isinstance(node, ast.ClassDef):
                base_names = [base.id for base in node.bases if isinstance(base, ast.Name)]
                if "BaseModel" not in base_names:
                    raise InvalidModelCode("Models must inherit from BaseModel")
                
        return tree

    @staticmethod
    def _parse_code(model_code: str) -> Type[BaseModel]:
        """Safely parse Pydantic model from user code."""
        try:
            # Validate code structure first
            ExtractorService._validate_model_code(model_code)
            
            # Execute in restricted environment
            namespace = {"BaseModel": BaseModel}
            exec(IMPORTS, namespace)
            exec(model_code, namespace)
            
            # Find the first BaseModel subclass
            pydantic_classes = [
                obj for obj in namespace.values() 
                if isinstance(obj, type) and issubclass(obj, BaseModel) and obj != BaseModel
            ]
            
            if not pydantic_classes:
                raise InvalidModelCode("No valid Pydantic models found")
                
            return pydantic_classes[-1]
            
        except Exception as e:
            logger.error(f"Model validation failed: {str(e)}")
            raise InvalidModelCode("Invalid model definition") from e

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
                "total_liabilities"
            ):
                financial_metadata["financial_ratios"] = {
                    "debt_to_equity": response.metadata["total_liabilities"]
                    / response.metadata["net_worth"],
                    "current_ratio": response.metadata["total_assets"]
                    / response.metadata["total_liabilities"],
                }

            output_data["financial_metadata"] = financial_metadata

        return schema_model(**output_data).model_dump_json(indent=2)
