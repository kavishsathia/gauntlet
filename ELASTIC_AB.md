# Elastic Agent Builder Reference

## Overview

Agent Builder is a framework within Elasticsearch for creating custom AI agents that connect LLMs to Elasticsearch data. Agents reason over data using tools, maintain conversation context, and are accessible via Kibana, APIs, MCP, and A2A.

Requires an Enterprise license. Enabled by default in serverless Elasticsearch projects.

## Authentication

```bash
export KIBANA_URL="your-kibana-url"
export ELASTICSEARCH_URL="your-elasticsearch-url"
export API_KEY="your-api-key"
```

All requests require:
```
Authorization: ApiKey ${API_KEY}
kbn-xsrf: true
```

## API Base Path

`/api/agent_builder`

For non-default spaces: `/s/<space_name>/api/agent_builder`

---

## Tools

Tools are modular, reusable actions that agents call to interact with Elasticsearch data.

### Tool Types

- **Built-in tools**: Ready to use, cannot be modified or deleted (e.g., search, ES|QL query)
- **Custom tools**: User-defined ES|QL tools with parameterized queries
- **MCP tools**: Accessible via Model Context Protocol for external clients

### ES|QL Tool Creation

ES|QL tools execute pre-defined parameterized queries against Elasticsearch data.

**Create a tool:**
```
POST /api/agent_builder/tools
```

**Payload:**
```json
{
  "id": "my-tool-id",
  "type": "esql",
  "description": "Description guiding the agent on when/how to use this tool",
  "configuration": {
    "query": "FROM my_index | WHERE field == ?param_name | SORT timestamp ASC | LIMIT 10",
    "params": {
      "param_name": {
        "type": "string",
        "description": "What this parameter represents"
      }
    }
  }
}
```

**Parameter syntax:** Use `?parameter_name` in the query. The agent interpolates values at execution time.

**Supported parameter types (Serverless):** string, integer, float, boolean, date, array

**Best practices:**
- Always include LIMIT clauses to prevent excessive results
- Use descriptive parameter names
- Set default values for optional parameters to prevent syntax errors
- Write clear descriptions so the agent knows when to use the tool

### Tool API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tools` | List all tools |
| POST | `/tools` | Create a tool |
| GET | `/tools/{toolId}` | Get tool by ID |
| PUT | `/tools/{toolId}` | Update a tool |
| DELETE | `/tools/{toolId}` | Delete a tool |
| POST | `/tools/_execute` | Execute a tool directly |

**Execute a tool directly:**
```
POST /api/agent_builder/tools/_execute
```
```json
{
  "tool_id": "my-tool-id",
  "tool_params": {
    "param_name": "value"
  }
}
```

---

## Agents

Agents combine instructions, tools, and conversation context to reason over data.

### Agent Creation

```
POST /api/agent_builder/agents
```

**Payload:**
```json
{
  "id": "my-agent-id",
  "name": "My Agent",
  "description": "What this agent does",
  "labels": ["label1", "label2"],
  "avatar_color": "#0077CC",
  "avatar_symbol": "gear",
  "instructions": "System-level guidance for the agent's behavior. Natural language.",
  "tools": {
    "tool_ids": ["tool-id-1", "tool-id-2"]
  }
}
```

### Agent API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents` | List all agents |
| POST | `/agents` | Create an agent |
| GET | `/agents/{id}` | Get agent by ID |
| PUT | `/agents/{id}` | Update an agent |
| DELETE | `/agents/{id}` | Delete an agent |

---

## Conversations (Chat)

### Send a message (synchronous)

```
POST /api/agent_builder/converse
```

**Request:**
```json
{
  "input": "User message to the agent",
  "agent_id": "my-agent-id",
  "conversation_id": "existing-conversation-id-or-omit-for-new"
}
```

**Response:**
```json
{
  "conversation_id": "conv-123",
  "round_id": "round-456",
  "status": "completed",
  "steps": [
    { "type": "reasoning", "content": "..." },
    { "type": "tool_call", "tool_id": "...", "params": {...}, "result": {...} }
  ],
  "model_usage": { "prompt_tokens": 100, "completion_tokens": 50 },
  "response": { "message": "Agent's reply" }
}
```

### Send a message (streaming)

```
POST /api/agent_builder/converse/async
```

Same request body, but returns streaming events.

### Conversation Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/conversations` | List conversations |
| GET | `/conversations/{conversation_id}` | Get conversation history |
| DELETE | `/conversations/{conversation_id}` | Delete conversation |

---

## Attachments

Conversations support file attachments.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/conversations/{id}/attachments` | List attachments |
| POST | `/conversations/{id}/attachments` | Create attachment |
| PUT | `/conversations/{id}/attachments/{aid}` | Update attachment |
| DELETE | `/conversations/{id}/attachments/{aid}` | Delete attachment |
| PATCH | `/conversations/{id}/attachments/{aid}` | Rename attachment |
| POST | `/conversations/{id}/attachments/{aid}/_restore` | Restore deleted |

---

## Integration Protocols

### MCP (Model Context Protocol)

```
POST /api/agent_builder/mcp
```

Exposes tools via the MCP standard for external client integration.

### A2A (Agent-to-Agent)

```
POST /api/agent_builder/a2a/{agentId}
```

Send tasks between agents.

```
GET /api/agent_builder/a2a/{agentId}.json
```

Get an agent's A2A card (capabilities descriptor).

---

## ES|QL Quick Reference

ES|QL is Elasticsearch's piped query language used in tool definitions.

```esql
FROM index_name
| WHERE field == ?param
| WHERE MATCH(text_field, ?search_terms)
| WHERE DATE_EXTRACT("year", date_field) < ?max_year
| SORT field ASC
| KEEP field1, field2, field3
| LIMIT 10
```

Key commands: `FROM`, `WHERE`, `SORT`, `KEEP`, `LIMIT`, `STATS ... BY`, `EVAL`, `DISSECT`, `GROK`, `ENRICH`, `DROP`, `RENAME`
