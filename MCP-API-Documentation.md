# NLWeb MCP (Model Context Protocol) API Documentation

## Overview

NLWeb implements the Model Context Protocol v1.0 specification, providing a standardized interface for AI agents to query knowledge bases and receive Schema.org-typed responses.

## Endpoints

### POST /ask

The primary MCP endpoint that accepts both traditional and MCP-formatted requests.

#### MCP Request Format

```json
{
  "function_call": {
    "name": "ask",
    "arguments": "{\"query\": \"your question here\", \"site\": \"optional-site-filter\", \"streaming\": false}"
  }
}
```

#### MCP Response Format

```json
{
  "schemaVersion": "1.0",
  "type": "function_response",
  "status": "success",
  "capabilities": {
    "functions": ["ask", "list_tools", "list_prompts", "get_prompt", "get_sites"],
    "streaming": true,
    "schema_types": ["FAQPage", "WebPage", "BlogPosting", "VideoObject", "ImageObject"]
  },
  "response": {
    "results": [
      {
        "url": "https://example.com/page",
        "name": "Page Title",
        "description": "Page description",
        "schema_object": {
          "@type": "FAQPage",
          "name": "Page Title",
          "mainEntity": [...]
        }
      }
    ]
  }
}
```

### POST /mcp

Alternative MCP endpoint with identical functionality to `/ask` when receiving MCP-formatted requests.

## Supported Functions

### ask
Query the knowledge base with a natural language question.

**Parameters:**
- `query` (string, required): The question to ask
- `site` (string, optional): Filter results to a specific site
- `streaming` (boolean, optional): Enable streaming responses

### list_tools
Get a list of available functions/tools.

### list_prompts
Get available prompt templates.

### get_prompt
Retrieve a specific prompt by ID.

**Parameters:**
- `prompt_id` (string, required): ID of the prompt to retrieve

### get_sites
Get a list of available sites that can be queried.

## Streaming Responses

When `streaming: true` is specified, the API returns Server-Sent Events (SSE) format:

```
data: {"type": "function_stream_event", "content": {"partial_response": "..."}}
data: {"type": "function_stream_end", "status": "success"}
```

## Error Handling

For unsupported functions or errors:

```json
{
  "schemaVersion": "1.0",
  "type": "function_response",
  "status": "error",
  "error": "Error message",
  "capabilities": {...}
}
```

## Schema.org Types

Responses include Schema.org structured data types:
- `FAQPage`: Frequently asked questions
- `WebPage`: General web pages
- `BlogPosting`: Blog posts and articles
- `VideoObject`: Video content
- `ImageObject`: Images

## Testing MCP Compliance

Use the provided test script:

```bash
./test-mcp-compliance.sh https://your-api-url.com
```

This will verify:
1. ✅ POST /ask endpoint accepts MCP format
2. ✅ Responses include schemaVersion and capabilities
3. ✅ Schema.org types are returned
4. ✅ Streaming requests are handled correctly
5. ✅ Unsupported functions return proper errors 