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

## Deployment

### Environment Variables

The following environment variables must be set:

- `SUPABASE_URL`: URL for your Supabase instance
- `SUPABASE_KEY`: API key for Supabase
- `API_BEARER_TOKEN`: Bearer token for the InfoMind API

### Deployment to Render

1. Push this repository to GitHub/GitLab/Bitbucket
2. Create a new Web Service on Render
3. Connect your repository
4. Set the environment variables
5. Deploy

## Local Development

1. Clone the repository
2. Create a `.env` file with the required environment variables
3. Install dependencies: `pip install -r requirements.txt`
4. Run the app: `python app.py`
