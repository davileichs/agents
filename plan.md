AGENTS SERVICE

This project is about creating a service that run agents. It will be used as MCP for AI applications.
IT will handle many agents at once.
The service will be a API that can only receive a request to run an agent. it is not possible to add/edit/delete from the API, it has only one type o call to the endpoint and the agent with his  tools will handle the rest.
The service will be a docker container that can be run on any server. The language used will be Python.

How endpoints work:

user request ton run an agent based on endpoint:
GET
/agents
return list of agents

POST
/agents/<agent_name>
with payload body json:
{
    "message": "user message"
}
return the result of agent execution.

ALl configuration will be handled by environment variables. what is important:
API_KEY: the Key used to connect to this endpoint, a second service will have this key to do authenticated requests to this endpoint. As it only exists one service, then the API_KEY will be the same for all agents.
LLM: The LLM used to run the agent. It can be OpenAI, Anthropic, Google, Ollama, etc.
LLM_MODEL: The LLM model used to run the agent. It can be gpt-3.5-turbo, gpt-4, claude-3, etc.
LLM_API_KEY: The API key used to connect to the LLM.
LLM_API_BASE: The API base used to connect to the LLM.


The service can have multiple agents, but everyone will use same LLM model, the tools will be different for each agent.
The LLM to be used: OpenAI, Anthropic, Google, Ollama

The agents can use same common services, but each agent must have its hown folder with tools inside of it, eg:

<agent_name>/
    schemas/
    tools/
    agent.yaml
    
the agent.yaml will have the main prompt of agent.
The tools will be autodiscovered for agent to use it.

