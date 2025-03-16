import pytest
from app.engine.loaders.db import DBLoaderConfig, get_db_documents


@pytest.mark.asyncio
async def test_get_db_documents_success() -> None:
    """Test successful document loading from database."""
    config = DBLoaderConfig(uri="sqlite:///:memory:", queries=["SELECT 1"])

    documents = await get_db_documents([config])
    assert len(documents) > 0
    assert "SELECT 1" in documents[0].text


@pytest.mark.asyncio
async def test_get_db_documents_invalid_uri() -> None:
    """Test handling of invalid database URI."""
    config = DBLoaderConfig(uri="invalid://uri", queries=["SELECT 1"])

    with pytest.raises(Exception):
        await get_db_documents([config])


@pytest.mark.asyncio
async def test_get_db_documents_empty_queries() -> None:
    """Test handling of empty queries list."""
    config = DBLoaderConfig(uri="sqlite:///:memory:", queries=[])

    documents = await get_db_documents([config])
    assert len(documents) == 0
