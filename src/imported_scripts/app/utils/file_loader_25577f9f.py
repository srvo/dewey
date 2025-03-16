import logging
import os

from app.config import Config
from llama_parse import LlamaParse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class FileLoaderConfig(BaseModel):
    use_llama_parse: bool = False


def llama_parse_parser():
    if os.getenv("LLAMA_CLOUD_API_KEY") is None:
        msg = (
            "LLAMA_CLOUD_API_KEY environment variable is not set. "
            "Please set it in .env file or in your shell environment then run again!"
        )
        raise ValueError(
            msg,
        )
    return LlamaParse(
        result_type="markdown",
        verbose=True,
        language="en",
        ignore_errors=False,
    )


def llama_parse_extractor() -> dict[str, LlamaParse]:
    from llama_parse.utils import SUPPORTED_FILE_TYPES

    parser = llama_parse_parser()
    return dict.fromkeys(SUPPORTED_FILE_TYPES, parser)


def get_file_documents(config: FileLoaderConfig):
    from llama_index.core.readers import SimpleDirectoryReader

    try:
        file_extractor = None
        if config.use_llama_parse:
            # LlamaParse is async first,
            # so we need to use nest_asyncio to run it in sync mode
            import nest_asyncio

            nest_asyncio.apply()

            file_extractor = llama_parse_extractor()
        reader = SimpleDirectoryReader(
            Config.DATA_DIR,
            recursive=True,
            filename_as_id=True,
            raise_on_error=True,
            file_extractor=file_extractor,
        )
        return reader.load_data()
    except Exception as e:
        import sys
        import traceback

        # Catch the error if the data dir is empty
        # and return as empty document list
        _, _, exc_traceback = sys.exc_info()
        function_name = traceback.extract_tb(exc_traceback)[-1].name
        if function_name == "_add_files":
            logger.warning(
                f"Failed to load file documents, error message: {e} . Return as empty document list.",
            )
            return []
        # Raise the error if it is not the case of empty data dir
        raise
