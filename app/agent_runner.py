import os
import yaml
import importlib.util
import inspect
import json
import litellm
import logging
from typing import List, Dict, Any, Callable
from .config import settings

logger = logging.getLogger(__name__)

AGENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agents")

def get_available_agents() -> List[str]:
    """Scans the agents directory and returns a list of valid agent names."""
    if not os.path.exists(AGENTS_DIR):
        return []
    
    agents = []
    for item in os.listdir(AGENTS_DIR):
        agent_path = os.path.join(AGENTS_DIR, item)
        if os.path.isdir(agent_path):
            agent_yaml_path = os.path.join(agent_path, "agent.yaml")
            if os.path.exists(agent_yaml_path):
                agents.append(item)
    return agents

def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """Loads the agent.yaml file for a specific agent."""
    agent_yaml_path = os.path.join(AGENTS_DIR, agent_name, "agent.yaml")
    if not os.path.exists(agent_yaml_path):
        return {}
    
    with open(agent_yaml_path, "r") as f:
        return yaml.safe_load(f) or {}

def generate_tool_schema(func: Callable) -> dict:
    sig = inspect.signature(func)
    parameters = {"type": "object", "properties": {}, "required": []}
    for name, param in sig.parameters.items():
        if name == 'self':
            continue
        param_type = "string"
        if param.annotation == int:
            param_type = "integer"
        elif param.annotation == bool:
            param_type = "boolean"
        elif param.annotation == float:
            param_type = "number"
        
        parameters["properties"][name] = {"type": param_type, "description": f"The {name} parameter"}
        if param.default == inspect.Parameter.empty:
            parameters["required"].append(name)
            
    doc = inspect.getdoc(func) or f"Tool to execute {func.__name__}"
    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": doc,
            "parameters": parameters
        }
    }

def get_tool_schemas(agent_name: str, tools_map: Dict[str, Callable]) -> List[dict]:
    """Generates or loads JSON schemas for the agent's tools and normalizes them for LiteLLM."""
    schemas = []
    schemas_dir = os.path.join(AGENTS_DIR, agent_name, "schemas")
    
    for tool_name, func in tools_map.items():
        # Check if an explicit schema file exists
        schema = None
        schema_file_json = os.path.join(schemas_dir, f"{tool_name}.json")
        schema_file_yaml = os.path.join(schemas_dir, f"{tool_name}.yaml")
        
        if os.path.exists(schema_file_json):
            with open(schema_file_json, "r") as f:
                schema = json.load(f)
        elif os.path.exists(schema_file_yaml):
            with open(schema_file_yaml, "r") as f:
                schema = yaml.safe_load(f)
        else:
            # Fallback to auto-generation
            schema = generate_tool_schema(func)
            
        # Normalize schema for LiteLLM
        if schema:
            if not isinstance(schema, dict):
                continue

            # Ensure we have a "function" wrapper with a "name"
            if schema.get("type") == "function" and "function" in schema:
                # Format: {"type": "function", "function": {...}}
                if "name" not in schema["function"]:
                    schema["function"]["name"] = tool_name
                # Ensure parameters are present inside function
                if "parameters" not in schema["function"] and "properties" in schema["function"]:
                    # If properties are at the same level as name/description, wrap them
                    props = schema["function"].pop("properties")
                    req = schema["function"].pop("required", [])
                    schema["function"]["parameters"] = {
                        "type": "object",
                        "properties": props,
                        "required": req
                    }
            elif "function" in schema:
                # Format: {"function": {...}}
                schema["type"] = "function"
                if "name" not in schema["function"]:
                    schema["function"]["name"] = tool_name
            else:
                # Format: raw function definition or parameters
                name = schema.get("name", tool_name)
                description = schema.get("description", f"Tool to execute {tool_name}")
                
                if "parameters" in schema:
                    parameters = schema["parameters"]
                elif "properties" in schema:
                    # It's an object schema, use it as parameters
                    parameters = {
                        "type": "object",
                        "properties": schema.get("properties", {}),
                        "required": schema.get("required", [])
                    }
                    # If there was a description, it's often better to keep it in the function,
                    # but we can leave it in parameters too as LiteLLM mostly cares about the top one
                else:
                    parameters = {"type": "object", "properties": {}}

                schema = {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": parameters
                    }
                }
            schemas.append(schema)
            
    return schemas

def load_agent_tools(agent_name: str) -> Dict[str, Callable]:
    """Dynamically loads tools from the agents/<agent_name>/tools directory."""
    tools_dir = os.path.join(AGENTS_DIR, agent_name, "tools")
    tools_map = {}
    
    if not os.path.exists(tools_dir):
        return tools_map

    for filename in os.listdir(tools_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            file_path = os.path.join(tools_dir, filename)
            
            # Load module dynamically
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Assume function with same name as file
                if hasattr(module, module_name):
                    func = getattr(module, module_name)
                    if callable(func):
                        tools_map[module_name] = func
                        
    return tools_map

async def run_agent_request(agent_name: str, message: str, user_id: str = None) -> Dict[str, Any]:
    """Runs the specified agent with history support."""
    from .services.history_service import history_service
    
    if agent_name not in get_available_agents():
        raise ValueError(f"Agent {agent_name} not found")
        
    config = get_agent_config(agent_name)
    tools_map = load_agent_tools(agent_name)
    tools_schemas = get_tool_schemas(agent_name, tools_map) if tools_map else None
    
    # Load history
    history = await history_service.get_recent_history(user_id, agent_name, limit=5)
    
    # Identify how many new messages we add to save later
    initial_history_count = len(history)
    
    system_prompt = config.get("prompt", "You are a helpful AI agent.")
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    
    # Add new user message
    user_msg = {"role": "user", "content": message}
    messages.append(user_msg)
    
    # Provider mapping based on .env
    # litellm requires model explicitly prefixing like 'openai/gpt-4o' or 'anthropic/claude-3-opus'
    # we can just use the provided LLM_MODEL directly or construct it.
    model_name = settings.llm_model
    if settings.llm == "openai" and not model_name.startswith("openai/"):
         # LiteLLM already maps standard gpt-4 to openai but safe
         pass
    elif settings.llm == "anthropic" and not model_name.startswith("anthropic/"):
         model_name = f"anthropic/{model_name}"
    elif settings.llm == "google" and not model_name.startswith("gemini/"):
         model_name = f"gemini/{model_name}"
    elif settings.llm == "ollama" and not model_name.startswith("ollama/"):
         model_name = f"ollama/{model_name}"
         
    # LiteLLM environment sets like OPENAI_API_KEY inside the lib, 
    # but we can pass it directly to completion api_key param
    
    MAX_STEPS = 5
    for step in range(MAX_STEPS):
        response = litellm.completion(
            model=model_name,
            messages=messages,
            tools=tools_schemas if tools_schemas else None,
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_base
        )
        
        msg = response.choices[0].message
        
        # Convert Pydantic model to dict filtering Nones
        # LiteLLM message sometimes is an object depending on the version, safest is model_dump
        try:
            msg_dict = msg.model_dump(exclude_none=True)
        except AttributeError:
            msg_dict = dict(msg)
            # Remove none values
            msg_dict = {k: v for k, v in msg_dict.items() if v is not None}
        
        messages.append(msg_dict)
        
        if getattr(msg, 'tool_calls', None):
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                args_str = tool_call.function.arguments
                try:
                    args = json.loads(args_str)
                except Exception:
                    args = {}
                    
                if func_name in tools_map:
                    func = tools_map[func_name]
                    
                    # Intercept and securely inject user_id if the tool accepts it
                    if user_id:
                        sig = inspect.signature(func)
                        if 'user_id' in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                            args['user_id'] = user_id
                            
                    try:
                        if inspect.iscoroutinefunction(func):
                            result = await func(**args)
                        else:
                            result = func(**args)
                    except Exception as e:
                        result = f"Error executing tool: {e}"
                else:
                    result = f"Unknown tool: {func_name}"
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": str(result)
                })
        else:
            break
            
    final_content = messages[-1].get("content", "")
    if hasattr(final_content, "content"): # if object
        final_content = final_content.content
        
    # Save new messages to history
    # System prompt is at index 0, followed by history (len = initial_history_count)
    # The new messages start after the history
    new_messages = messages[1 + initial_history_count:]
    if user_id and new_messages:
        await history_service.add_messages(user_id, agent_name, new_messages)

    return {
        "agent": agent_name,
        "message": message,
        "response": final_content,
        "steps": len(messages) - 2 # Not counting initial sys+user
    }
