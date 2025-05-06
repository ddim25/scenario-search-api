import os
import re
import json
import datetime
import calendar
from dateutil import parser
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class FilterAgent:
    """
    Agent responsible for interpreting natural language queries to filter business scenario records
    stored in a Supabase PostgreSQL table named scenarios.
    """
    
    def __init__(self):
        self.time_patterns = {
            r'\btoday\b': self._get_today_range,
            r'\byesterday\b': self._get_yesterday_range,
            r'\blast\s+week\b': self._get_last_week_range,
            r'\blast\s+month\b': self._get_last_month_range,
            r'\blast\s+24\s+hours\b': self._get_last_24_hours_range,
            r'from\s+([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)\s+to\s+([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)': self._get_explicit_date_range
        }
        
        self.status_patterns = {
            r'\bpassed\b': 'Passed',
            r'\bfailed\b': 'Failed'
        }
    
    def _get_today_range(self, match=None):
        """Get the time range for today (UTC)."""
        now = datetime.datetime.utcnow()
        start_time = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
        end_time = now
        return start_time, end_time
    
    def _get_yesterday_range(self, match=None):
        """Get the time range for yesterday (UTC)."""
        now = datetime.datetime.utcnow()
        yesterday = now - datetime.timedelta(days=1)
        start_time = datetime.datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)
        end_time = datetime.datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
        return start_time, end_time
    
    def _get_last_week_range(self, match=None):
        """Get the time range for the last 7 full days before today (UTC)."""
        now = datetime.datetime.utcnow()
        today_start = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
        start_time = today_start - datetime.timedelta(days=7)
        end_time = today_start - datetime.timedelta(seconds=1)
        return start_time, end_time
    
    def _get_last_month_range(self, match=None):
        """Get the time range for the previous calendar month (UTC)."""
        now = datetime.datetime.utcnow()
        
        # If current month is January, previous month is December of last year
        if now.month == 1:
            prev_month = 12
            prev_year = now.year - 1
        else:
            prev_month = now.month - 1
            prev_year = now.year
        
        # Get the last day of the previous month
        last_day = calendar.monthrange(prev_year, prev_month)[1]
        
        start_time = datetime.datetime(prev_year, prev_month, 1, 0, 0, 0)
        end_time = datetime.datetime(prev_year, prev_month, last_day, 23, 59, 59)
        
        return start_time, end_time
    
    def _get_last_24_hours_range(self, match=None):
        """Get the time range for the last 24 hours (UTC)."""
        now = datetime.datetime.utcnow()
        start_time = now - datetime.timedelta(hours=24)
        end_time = now
        return start_time, end_time
    
    def _get_explicit_date_range(self, match):
        """Get the time range for an explicit date range (UTC)."""
        try:
            start_date_str = match.group(1)
            end_date_str = match.group(2)
            
            # Parse dates
            start_time = parser.parse(start_date_str)
            end_time = parser.parse(end_date_str)
            
            # Set start time to beginning of day and end time to end of day
            start_time = datetime.datetime(start_time.year, start_time.month, start_time.day, 0, 0, 0)
            end_time = datetime.datetime(end_time.year, end_time.month, end_time.day, 23, 59, 59)
            
            return start_time, end_time
        except Exception as e:
            print(f"Error parsing explicit date range: {e}")
            return None, None
    
    def _extract_time_filter(self, query):
        """Extract time filter from the query."""
        for pattern, func in self.time_patterns.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return func(match)
        
        # No time filter found, return None
        return None, None
    
    def _extract_status_filter(self, query):
        """Extract status filter from the query."""
        for pattern, status in self.status_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                return status
        
        # No status filter found, return None (which means all statuses)
        return None
    
    def _format_results(self, results):
        """Format the results in a clear, abstract format."""
        formatted_results = []
        
        for row in results:
            formatted_row = {
                "Run ID": row.get("runId", ""),
                "Scenario ID": row.get("scenarioId", ""),
                "Scenario": row.get("scenarioName", ""),
                "Process ID": row.get("processId", ""),
                "Process": row.get("processName", ""),
                "Flow ID": row.get("flowId", ""),
                "Flow": row.get("flowName", ""),
                "Status": row.get("rowRunStatus", ""),
                "Timestamp": row.get("createdTimestamp", "")
            }
            formatted_results.append(formatted_row)
        
        return formatted_results
    
    def _build_query(self, start_time, end_time, status):
        """Build the SQL query based on the extracted filters."""
        # Start with a basic query
        query = supabase.table("scenarios").select("*")
        
        # Apply filters using standard Supabase query methods
        if start_time:
            # Convert to string format that Supabase can handle
            start_time_str = start_time.isoformat()
            # Use the .gte() method for greater than or equal
            query = query.gte("createdTimestamp", start_time_str)
            
        if end_time:
            # Convert to string format that Supabase can handle
            end_time_str = end_time.isoformat()
            # Use the .lte() method for less than or equal
            query = query.lte("createdTimestamp", end_time_str)
        
        # Apply status filter if provided
        if status:
            query = query.eq("rowRunStatus", status)
        
        # Order by createdTimestamp in descending order
        query = query.order("createdTimestamp", desc=True)
        
        # If no time filter, limit to 20 results
        if not start_time and not end_time:
            query = query.limit(20)
        
        return query
    
    def process_query(self, query):
        """
        Process a natural language query to filter scenario records.
        
        Args:
            query (str): The natural language query.
            
        Returns:
            dict: A dictionary containing the filtered results or an error message.
        """
        try:
            # Extract time and status filters
            start_time, end_time = self._extract_time_filter(query)
            status = self._extract_status_filter(query)
            
            # Build and execute the query
            supabase_query = self._build_query(start_time, end_time, status)
            response = supabase_query.execute()
            
            results = response.data
            
            # Format the results
            if results:
                formatted_results = self._format_results(results)
                return {
                    "success": True,
                    "results": formatted_results,
                    "count": len(formatted_results)
                }
            else:
                # Construct a meaningful message based on the filters
                message = "No scenarios found"
                
                if status:
                    message += f" with status '{status}'"
                
                if start_time and end_time:
                    # Determine which time filter was used
                    time_description = ""
                    if start_time.date() == datetime.datetime.utcnow().date():
                        time_description = "today"
                    elif (datetime.datetime.utcnow() - start_time).days == 1:
                        time_description = "yesterday"
                    elif (datetime.datetime.utcnow() - start_time).days == 7:
                        time_description = "for the last week"
                    elif start_time.day == 1 and end_time.day > 28:
                        time_description = f"for {start_time.strftime('%B %Y')}"
                    elif (datetime.datetime.utcnow() - start_time).total_seconds() <= 86400:
                        time_description = "in the last 24 hours"
                    else:
                        time_description = f"between {start_time.strftime('%B %d, %Y')} and {end_time.strftime('%B %d, %Y')}"
                    
                    message += f" {time_description}"
                
                return {
                    "success": False,
                    "message": message
                }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"Error processing query: {str(e)}"
            }

# Example usage
if __name__ == "__main__":
    agent = FilterAgent()
    
    # Test queries
    test_queries = [
        "Show me all failed scenarios from yesterday",
        "What scenarios passed last week?",
        "Show me scenarios from last month",
        "What happened in the last 24 hours?",
        "Show me scenarios from April 1 to April 10",
        "Show me the most recent scenarios"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = agent.process_query(query)
        print(json.dumps(result, indent=2))
