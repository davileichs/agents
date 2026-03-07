from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from .config import settings
from . import agent_runner

app = FastAPI(title="Agents Service", description="API to run dynamically configured agents")

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

def get_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Missing Authorization header"
        )
    
    # Allow Bearer token format as well
    if api_key.startswith("Bearer "):
        api_key = api_key.replace("Bearer ", "")
        
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Could not validate credentials"
        )
    return api_key

from typing import Optional

class AgentRequest(BaseModel):
    message: str
    user_id: Optional[str] = None

@app.get("/health")
async def health_check():
    """Health check endpoint to verify the service is running."""
    return {"status": "healthy"}

@app.get("/agents")
async def list_agents(api_key: str = Depends(get_api_key)):
    """Returns a list of available agents and their defined endpoints."""
    agents_list = agent_runner.get_available_agents()
    
    # Return mapping of agent name to endpoint
    agents_data = []
    for agent in agents_list:
        cfg = agent_runner.get_agent_config(agent)
        # Default to /agent_name if custom endpoint is not defined
        endpoint = cfg.get("endpoint", f"/{agent}")
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
            
        # Ensure it's prefixed with /agents
        if not endpoint.startswith("/agents"):
            endpoint = f"/agents{endpoint}"
            
        agents_data.append({
            "name": agent,
            "endpoint": endpoint,
            "description": cfg.get("description", "")
        })
        
    return {"agents": agents_data}

# Function to generate route handler dynamically
def create_agent_route(agent_name: str):
    async def route_handler(request: AgentRequest, api_key: str = Depends(get_api_key)):
        try:
            result = await agent_runner.run_agent_request(agent_name, request.message, request.user_id)
            return result
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
            
    # Modify function name for OpenAPI schema clarity
    route_handler.__name__ = f"run_{agent_name}"
    return route_handler

from contextlib import asynccontextmanager
from app.services.database import engine, Base
import app.models.token
import app.models.travel_profile

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    agents = agent_runner.get_available_agents()
    for agent_name in agents:
        cfg = agent_runner.get_agent_config(agent_name)
        endpoint = cfg.get("endpoint", f"/{agent_name}")
        
        # Ensure it starts with slash
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
            
        # Ensure it's prefixed with /agents
        if not endpoint.startswith("/agents"):
            endpoint = f"/agents{endpoint}"
            
        print(f"Registering agent '{agent_name}' at endpoint POST {endpoint}")
        
        # Add the route dynamically using the factory function
        app.add_api_route(
            path=endpoint,
            endpoint=create_agent_route(agent_name),
            methods=["POST"],
            response_model=dict,
            dependencies=[Depends(get_api_key)],
            tags=["Agents Execution"]
        )
    yield

app = FastAPI(title="Agents Service", description="API to run dynamically configured agents", lifespan=lifespan)
