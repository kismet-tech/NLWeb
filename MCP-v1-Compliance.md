# MCP v1.0 Full Compliance

This document describes the changes made to NLWeb for full compliance with MCP (Model Context Protocol) v1.0 specification.

## Summary of Changes

### 1. Simple JSON Format Support
The `/ask` endpoint now accepts the simple format specified in MCP v1.0:
```json
{"question": "your question here"}
```

This is automatically converted to the function_call format internally.

### 2. Answer Field
All responses now use the `answer` field instead of `response` for MCP v1.0 compliance:
```json
{
  "schemaVersion": "1.0",
  "type": "function_response", 
  "status": "success",
  "answer": [...],  // Changed from "response"
  "capabilities": {...}
}
```

### 3. Streaming Support
- When `"stream": true` is specified in simple format, returns SSE stream
- When `"stream": false` or not specified, returns JSON response
- Properly handles both simple and function_call formats

### 4. Schema.org Types
All responses include proper Schema.org typed objects in the answer field:
- `FAQPage`
- `WebPage` 
- `BlogPosting`
- `VideoObject`
- `ImageObject`

## API Examples

### Simple Format (Non-streaming)
```bash
curl -X POST https://yourdomain.com/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Kismet?"}'
```

Response:
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
  "answer": [
    {
      "url": "https://example.com",
      "name": "Page Title",
      "description": "...",
      "schema_object": {
        "@type": "FAQPage",
        "mainEntity": [...]
      }
    }
  ]
}
```

### Simple Format (Streaming)
```bash
curl -X POST https://yourdomain.com/ask \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"question": "Tell me more", "stream": true}'
```

### Traditional Function Call Format
Still supported for backward compatibility:
```bash
curl -X POST https://yourdomain.com/ask \
  -H "Content-Type: application/json" \
  -d '{
    "function_call": {
      "name": "ask",
      "arguments": "{\"query\": \"What is Kismet?\", \"streaming\": false}"
    }
  }'
```

## Testing

Run the compliance test script:
```bash
python test_mcp_v1_compliance.py https://your-api-url.com
```

This will verify:
1. ✅ Simple format support
2. ✅ Answer field in responses
3. ✅ Schema.org types
4. ✅ Streaming behavior
5. ✅ Error handling

## Implementation Details

### Files Modified
- `code/core/mcp_handler.py`:
  - Added simple format detection and conversion
  - Updated `create_mcp_response()` to use `answer` field
  - Consistent error handling with MCP format

### Backward Compatibility
- Function call format still works
- Old response parsing should continue to work by checking for both `answer` and `response` fields 