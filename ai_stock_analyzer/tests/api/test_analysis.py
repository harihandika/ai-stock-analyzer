"""
AI Stock Analyzer - Analysis API Tests
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from app.main import app
from app.api.dependencies import get_current_active_user
from app.domain.models.models import User
import uuid

@pytest.mark.asyncio
async def test_analysis_health_check(client: AsyncClient):
    """Test health check endpoint requiring authentication"""
    def override_get_user():
        return User(id=uuid.uuid4(), email="test@test.com", is_active=True, subscription_tier="free")
        
    app.dependency_overrides[get_current_active_user] = override_get_user
    
    response = await client.get("/api/v1/analysis/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert "available_engines" in data
    
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_analysis_health_check_unauthorized(client: AsyncClient):
    """Test health check without token"""
    response = await client.get("/api/v1/analysis/health")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
