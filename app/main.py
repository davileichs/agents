import asyncio
from fastapi import FastAPI, Depends, HTTPException, Security, status, Request
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from .config import settings
from . import agent_runner
from typing import Optional, Any, Dict, List
from contextlib import asynccontextmanager
from app.services.database import engine, Base
import app.models.token
import app.models.travel_profile
import app.models.message
from .mcp_server import agent_mcp_server
from mcp.server.sse import SseServerTransport
from starlette.responses import Response

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    if settings.database_url:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("Database tables initialized successfully.")
        except Exception as e:
            print(f"Warning: Failed to initialize database tables: {e}")
    else:
        print("Warning: DATABASE_URL not set, skipping table initialization.")
        
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

app = FastAPI(
    title="Agents Service", 
    description="API to run dynamically configured agents",
    lifespan=lifespan
)

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

@app.get("/agents/{agent_name}")
async def get_agent_details(agent_name: str, api_key: str = Depends(get_api_key)):
    """Returns details for a specific agent: prompt, name, and tools."""
    available_agents = agent_runner.get_available_agents()
    if agent_name not in available_agents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Agent '{agent_name}' not found"
        )
        
    cfg = agent_runner.get_agent_config(agent_name)
    tools_map = agent_runner.load_agent_tools(agent_name)
    tools_schemas = agent_runner.get_tool_schemas(agent_name, tools_map)
    
    # Filter to only return name and description for each tool
    tools_data = []
    for schema in tools_schemas:
        if "function" in schema:
            tools_data.append({
                "name": schema["function"].get("name"),
                "description": schema["function"].get("description")
            })
    
    return {
        "name": cfg.get("name", agent_name),
        "prompt": cfg.get("prompt", ""),
        "tools": tools_data
    }

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

# Instantiate the transport globally so it persists across requests
mcp_transport = SseServerTransport("/mcp/messages")

async def check_mcp_auth(scope) -> bool:
    """Manually verify API key from ASGI scope."""
    headers = dict(scope.get('headers', []))
    auth_header = headers.get(b'authorization', b'').decode('utf-8')
    if not auth_header:
        return False
    
    token = auth_header
    if token.startswith("Bearer "):
        token = token[7:]
    
    return token == settings.api_key

class MCPSSEApp:
    async def __call__(self, scope, receive, send):
        if not await check_mcp_auth(scope):
            response = Response("Unauthorized", status_code=403)
            await response(scope, receive, send)
            return

        async with mcp_transport.connect_sse(scope, receive, send) as (read_stream, write_stream):
            await agent_mcp_server.run(
                read_stream,
                write_stream,
                agent_mcp_server.create_initialization_options()
            )

class MCPMessagesApp:
    async def __call__(self, scope, receive, send):
        if not await check_mcp_auth(scope):
            response = Response("Unauthorized", status_code=403)
            await response(scope, receive, send)
            return

        await mcp_transport.handle_post_message(scope, receive, send)

# Register raw ASGI routes
app.add_route("/mcp/sse", MCPSSEApp(), methods=["GET"])
app.add_route("/mcp/messages", MCPMessagesApp(), methods=["POST"])

@app.get("/health")
async def health_check():
    """Health check endpoint to verify the service is running."""
    return {"status": "healthy"}


