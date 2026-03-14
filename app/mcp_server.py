from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from typing import Any, Dict, List
from . import agent_runner
import logging

logger = logging.getLogger(__name__)

# Create the MCP server
agent_mcp_server = Server("agents-service")

@agent_mcp_server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available agents as MCP tools."""
    available_agents = agent_runner.get_available_agents()
    tools = []
    
    for agent_name in available_agents:
        cfg = agent_runner.get_agent_config(agent_name)
        tools.append(Tool(
            name=agent_name,
            description=cfg.get("description", f"Run the {agent_name} agent"),
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to send to the agent"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "Optional user ID for session persistence",
                        "default": "mcp-user"
                    }
                },
                "required": ["message"]
            }
        ))
    
    return tools

@agent_mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any] | None) -> List[TextContent]:
    """Handle MCP tool calls by running the corresponding agent."""
    if not arguments:
        arguments = {}
        
    message = arguments.get("message")
    user_id = arguments.get("user_id", "mcp-user")
    
    if not message:
        return [TextContent(type="text", text="Error: 'message' argument is required.")]
        
    try:
        available_agents = agent_runner.get_available_agents()
        if name not in available_agents:
            return [TextContent(type="text", text=f"Error: Agent '{name}' not found.")]
            
        result = await agent_runner.run_agent_request(name, message, user_id)
        response_text = result.get("response", "No response from agent.")
        
        return [TextContent(type="text", text=response_text)]
    except Exception as e:
        logger.error(f"Error calling MCP tool {name}: {e}")
        return [TextContent(type="text", text=f"Error executing agent: {str(e)}")]
