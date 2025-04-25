import pytest
from temdb_client import TEMdbClient



@pytest.mark.asyncio
async def test_client_initialization(client):
    assert isinstance(client, TEMdbClient)

@pytest.mark.asyncio
async def test_resource_creation(client):
    assert hasattr(client, 'specimen')
    assert hasattr(client, 'block')
    assert hasattr(client, 'cutting_session')
    assert hasattr(client, 'imaging_session')
    assert hasattr(client, 'roi')
    assert hasattr(client, 'acquisition')