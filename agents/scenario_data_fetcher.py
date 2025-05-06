import os
import datetime
import logging
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data_fetcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("scenario_data_fetcher")

# Load environment variables
load_dotenv()

# API configuration
API_BEARER_TOKEN = os.getenv("API_BEARER_TOKEN")
BASE_URL = "https://prod-backend.infomind.ai/automation-reports/reports"

# API functions
def get_runs():
    """Fetch all run IDs from the API."""
    url = f"{BASE_URL}/getruns"
    headers = {
        "Authorization": f"Bearer {API_BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    
    logger.info(f"Making API request to: {url}")
    logger.info(f"Using Authorization header: Bearer {API_BEARER_TOKEN[:10]}...")
    
    try:
        response = requests.get(url, headers=headers)
        logger.info(f"API response status code: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"API error response: {response.text}")
            return None
            
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        response_data = response.json()
        logger.info(f"API response data type: {type(response_data)}")
        logger.info(f"API response data preview: {str(response_data)[:500]}..." if response_data else "Empty response")
        return response_data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching run IDs: {str(e)}")
        return None

def get_run_timestamps(runs_response):
    """Extract run ID to timestamp mapping from the API response."""
    timestamp_map = {}
    
    if isinstance(runs_response, dict) and 'data' in runs_response:
        for run_data in runs_response['data']:
            run_id = run_data.get('runId')
            created_timestamp = run_data.get('createdTimestamp')
            
            if run_id is not None and created_timestamp is not None:
                timestamp_map[str(run_id)] = created_timestamp
    
    return timestamp_map

def get_report_by_run_id(run_id):
    """Fetch scenario details for a specific run ID."""
    url = f"{BASE_URL}/reportbyrunid"
    headers = {
        "Authorization": f"Bearer {API_BEARER_TOKEN}",
        "Content-Type": "application/json"
    }
    params = {"runId": run_id}
    
    logger.info(f"Making API request to: {url} with runId: {run_id}")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        logger.info(f"API response status code for runId {run_id}: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"API error response for runId {run_id}: {response.text}")
            return None
            
        response.raise_for_status()
        response_data = response.json()
        logger.info(f"API response data type for runId {run_id}: {type(response_data)}")
        logger.info(f"API response data preview for runId {run_id}: {str(response_data)[:200]}..." if response_data else "Empty response")
        return response_data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching report for run ID {run_id}: {str(e)}")
        return None

def extract_run_ids(api_response):
    """Extract all run IDs from the API response."""
    # Check if response is None
    if not api_response:
        return []
    
    # Handle the case where the response has a 'data' field (actual API format)
    if isinstance(api_response, dict) and 'data' in api_response:
        items = api_response['data']
        logger.info(f"Found {len(items)} items in the 'data' field")
        return [str(item.get('runId')) for item in items if item.get('runId') is not None]
    
    # Handle the case where the response is a list (original expected format)
    elif isinstance(api_response, list):
        return [str(item.get('runId')) for item in api_response if item.get('runId') is not None]
    
    # If response is in an unexpected format
    logger.error(f"Unexpected API response format: {type(api_response)}")
    return []

def extract_scenario_details(run_id, api_response, created_timestamp=None):
    """Extract scenario details from the API response for a specific run ID.
    
    Args:
        run_id: The run ID to extract scenarios for
        api_response: The API response containing the scenario details
        created_timestamp: The timestamp when the run was created (from the runs API)
    """
    if not api_response:
        return []
    
    scenarios = []
    
    # Use the provided timestamp or default to current time if not available
    if created_timestamp is None:
        timestamp = datetime.datetime.now().isoformat()
        logger.warning(f"No timestamp provided for runId {run_id}, using current time")
    else:
        timestamp = created_timestamp
        logger.info(f"Using timestamp {timestamp} for runId {run_id}")
    
    try:
        # Based on the actual API response structure:
        # data -> processResults -> run_id -> processResults -> [processes] -> flows -> [flows] -> scenarioRunDetails -> [scenarios]
        if isinstance(api_response, dict) and 'data' in api_response:
            data = api_response['data']
            
            if isinstance(data, dict) and 'processResults' in data:
                process_results = data['processResults']
                
                # The run_id is a key in the processResults dict
                if str(run_id) in process_results:
                    run_data = process_results[str(run_id)]
                    
                    if isinstance(run_data, dict) and 'processResults' in run_data:
                        processes = run_data['processResults']
                        
                        # Iterate through each process
                        for process in processes:
                            process_id = process.get('processId', '')
                            process_name = process.get('processName', '')
                            
                            # Check if the process has flows
                            if 'flows' in process and isinstance(process['flows'], list):
                                flows = process['flows']
                                
                                # Iterate through each flow
                                for flow in flows:
                                    flow_id = flow.get('flowId', '')
                                    flow_name = flow.get('flowName', '')
                                    
                                    # Check if the flow has scenarioRunDetails (this is the actual field name in the API response)
                                    if 'scenarioRunDetails' in flow and isinstance(flow['scenarioRunDetails'], list):
                                        scenario_details = flow['scenarioRunDetails']
                                        logger.info(f"Found {len(scenario_details)} scenarios in flow {flow_id} for runId {run_id}")
                                        
                                        # Iterate through each scenario
                                        for scenario in scenario_details:
                                            # The rowRunStatus is a dict with row numbers as keys
                                            row_status = scenario.get('rowRunStatus', {})
                                            status_value = ''
                                            
                                            # Extract the status value from the first row
                                            if isinstance(row_status, dict) and row_status:
                                                first_row = next(iter(row_status))
                                                status_value = 'Passed' if row_status.get(first_row) else 'Failed'
                                            
                                            scenarios.append({
                                                'runId': str(run_id),
                                                'scenarioId': str(scenario.get('scenarioId', '')),
                                                'scenarioName': scenario.get('scenarioName', ''),
                                                'flowId': str(flow_id),
                                                'flowName': flow_name,
                                                'processId': str(process_id),
                                                'processName': process_name,
                                                'createdTimestamp': timestamp,  # Using the timestamp from the runs API
                                                'rowRunStatus': status_value
                                            })
        
        if not scenarios:
            logger.warning(f"No scenarios found in the expected structure for runId {run_id}")
        else:
            logger.info(f"Successfully extracted {len(scenarios)} scenarios for runId {run_id}")
            
    except Exception as e:
        logger.error(f"Error extracting scenario details for runId {run_id}: {str(e)}")
    
    return scenarios

def fetch_all_scenarios():
    """Fetch all scenarios from the API.
    
    This function:
    1. Fetches all run IDs
    2. For each run ID, fetches the scenario details
    3. Extracts and returns all scenarios
    
    Returns:
        list: A list of scenario dictionaries
    """
    logger.info("Starting scenario data fetching process")
    
    # Step 1: Fetch all run IDs
    logger.info("Fetching all run IDs")
    runs_response = get_runs()
    
    if not runs_response:
        logger.error("Failed to fetch run IDs. Aborting data fetching.")
        return []
    
    # Extract run IDs and timestamps
    run_ids = extract_run_ids(runs_response)
    timestamp_map = get_run_timestamps(runs_response)
    logger.info(f"Found {len(run_ids)} run IDs")
    
    if not run_ids:
        logger.warning("No run IDs found. Aborting data fetching.")
        return []
    
    # Step 2: Fetch scenario details for each run ID
    all_scenarios = []
    
    for run_id in run_ids:
        logger.info(f"Fetching scenarios for run ID: {run_id}")
        report_response = get_report_by_run_id(run_id)
        
        if not report_response:
            logger.warning(f"Failed to fetch report for run ID: {run_id}. Skipping.")
            continue
        
        # Pass the timestamp for this run ID to the extract_scenario_details function
        timestamp = timestamp_map.get(run_id)
        scenarios = extract_scenario_details(run_id, report_response, timestamp)
        logger.info(f"Found {len(scenarios)} scenarios for run ID: {run_id}")
        all_scenarios.extend(scenarios)
    
    logger.info(f"Total scenarios fetched: {len(all_scenarios)}")
    return all_scenarios

if __name__ == "__main__":
    # For testing purposes
    scenarios = fetch_all_scenarios()
    print(f"Fetched {len(scenarios)} scenarios")
