# Scenario Search API

This API allows you to query scenario data using natural language. It checks if data needs to be refreshed (based on a 24-hour rule) before processing queries.

## API Endpoint

### Query Scenarios

```
POST /api/query
```

**Request Body:**
```json
{
  "query": "Show me failed scenarios from last week"
}
```

**Response:**
```json
{
  "success": true,
  "count": 5,
  "results": [
    {
      "Run ID": "12345",
      "Scenario ID": "67890",
      "Scenario": "Login Test",
      "Process ID": "1111",
      "Process": "Authentication",
      "Flow ID": "2222",
      "Flow": "User Login",
      "Status": "Failed",
      "Timestamp": "2025-04-30T10:30:00Z"
    },
    ...
  ]
}
```

## Example Queries

- "Show me failed scenarios from last week"
- "Show me passed scenarios from yesterday"
- "Show me scenarios from last 24 hours"
- "Show me all scenarios from April 2025"
