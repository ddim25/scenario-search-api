import os
import datetime
import time
import logging
import schedule
from dotenv import load_dotenv
from supabase import create_client, Client

# Import the required modules from agents folder
from agents import scenario_data_fetcher
from agents.filter_agent import FilterAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("orchestrator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("orchestrator")

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Database functions
def initialize_database():
    """
    Check if the scenarios table exists in Supabase.
    If it doesn't exist, create it automatically.
    """
    try:
        # Try to query the table to see if it exists
        supabase.table('scenarios').select('runId').limit(1).execute()
        logger.info("Scenarios table exists in Supabase")
        return True
    except Exception as e:
        logger.warning(f"Scenarios table might not exist: {str(e)}")
        logger.info("Attempting to create scenarios table automatically...")
        
        # Create the table using SQL
        try:
            # SQL to create the scenarios table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS scenarios (
                "runId" TEXT NOT NULL,
                "scenarioId" TEXT NOT NULL,
                "scenarioName" TEXT,
                "flowId" TEXT,
                "flowName" TEXT,
                "processId" TEXT,
                "processName" TEXT,
                "createdTimestamp" TIMESTAMP,
                "rowRunStatus" TEXT,
                "last_updated_timestamp" TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY ("runId", "scenarioId")
            );
            """
            
            # Execute the SQL using RPC
            supabase.rpc('exec_sql', {'query': create_table_sql}).execute()
            logger.info("Successfully created scenarios table")
            return True
        except Exception as create_error:
            logger.error(f"Failed to create scenarios table: {str(create_error)}")
            logger.error("Please create the scenarios table manually in the Supabase dashboard with the following columns:")
            logger.error("runId (text, primary key), scenarioId (text, primary key), scenarioName (text), "
                        "flowId (text), flowName (text), processId (text), processName (text), "
                        "createdTimestamp (timestamp), rowRunStatus (text), last_updated_timestamp (timestamp)")
            return False

def get_last_updated_timestamp():
    """Get the most recent last_updated_timestamp from the scenarios table."""
    try:
        response = supabase.table('scenarios') \
            .select('last_updated_timestamp') \
            .order('last_updated_timestamp', desc=True) \
            .limit(1) \
            .execute()
        
        if response.data and len(response.data) > 0:
            return datetime.datetime.fromisoformat(response.data[0]['last_updated_timestamp'].replace('Z', '+00:00'))
        return None
    except Exception as e:
        logger.error(f"Error getting last updated timestamp: {str(e)}")
        return None

def insert_scenarios(scenario_data):
    """Insert multiple scenarios into the database."""
    current_time = datetime.datetime.now().isoformat()
    
    # Add the current timestamp to each scenario
    for scenario in scenario_data:
        scenario['last_updated_timestamp'] = current_time
        # Convert datetime objects to ISO format strings if needed
        if isinstance(scenario.get('createdTimestamp'), datetime.datetime):
            scenario['createdTimestamp'] = scenario['createdTimestamp'].isoformat()
    
    try:
        # Group scenarios by runId for processing
        run_ids = {scenario['runId'] for scenario in scenario_data}
        
        # Process each runId group
        for run_id in run_ids:
            # Delete existing scenarios with this runId
            supabase.table('scenarios') \
                .delete() \
                .eq('runId', run_id) \
                .execute()
            
            # Filter scenarios for this runId
            run_scenarios = [s for s in scenario_data if s['runId'] == run_id]
            
            # Insert new scenarios in batches of 50 to avoid payload size limits
            batch_size = 50
            for i in range(0, len(run_scenarios), batch_size):
                batch = run_scenarios[i:i+batch_size]
                supabase.table('scenarios') \
                    .insert(batch) \
                    .execute()
        
        return True, f"Successfully inserted {len(scenario_data)} scenarios"
    except Exception as e:
        logger.error(f"Error inserting scenarios: {str(e)}")
        return False, f"Error inserting scenarios: {str(e)}"

# Orchestration functions
def should_run_ingestion():
    """Check if 24 hours have passed since the last ingestion."""
    last_updated = get_last_updated_timestamp()
    
    if not last_updated:
        logger.info("No previous ingestion found. Running initial ingestion.")
        return True
    
    now = datetime.datetime.now()
    time_diff = now - last_updated
    
    # Check if more than 24 hours (86400 seconds) have passed
    if time_diff.total_seconds() > 86400:
        logger.info(f"Last ingestion was {time_diff.total_seconds()/3600:.2f} hours ago. Running new ingestion.")
        return True
    else:
        logger.info(f"Last ingestion was only {time_diff.total_seconds()/3600:.2f} hours ago. Skipping ingestion.")
        return False

def ingest_scenarios():
    """Main function to ingest scenarios and store them in the database."""
    logger.info("Starting scenario ingestion process")
    
    # Check if we should run the ingestion
    if not should_run_ingestion():
        logger.info("Skipping scenario ingestion, not time yet")
        return False
    
    # Fetch all scenarios using the data fetcher
    logger.info("Fetching scenarios from the data fetcher")
    all_scenarios = scenario_data_fetcher.fetch_all_scenarios()
    
    # Store scenarios in the database
    if all_scenarios:
        logger.info(f"Storing {len(all_scenarios)} scenarios in the database")
        success, message = insert_scenarios(all_scenarios)
        
        if success:
            logger.info(message)
            return True
        else:
            logger.error(message)
            return False
    else:
        logger.warning("No scenarios found to store in the database")
        return False

def run_scheduled_job():
    """Run the ingestion job on schedule."""
    try:
        success = ingest_scenarios()
        logger.info(f"Scheduled job completed with success: {success}")
        # Here you can add triggers for other agents when ingest_scenarios is done
        if success:
            # Example: Call other agents here
            # from agents import another_agent
            # another_agent.run()
            pass
    except Exception as e:
        logger.error(f"Error in scheduled job: {str(e)}")

def main():
    """Main entry point for the orchestrator."""
    logger.info("Initializing orchestrator")
    
    # Initialize the database
    if not initialize_database():
        logger.error("Database initialization failed. Exiting.")
        return
    
    # Run immediately on startup
    run_scheduled_job()
    
    # Schedule to run daily
    schedule.every(24).hours.do(run_scheduled_job)
    
    logger.info("Scheduled job to run every 24 hours")
    logger.info("The orchestrator will check every 24 hours if new data needs to be ingested")
    logger.info("If data is ingested successfully, other agents can be triggered")
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def process_query(query):
    """Process a natural language query through the orchestrator."""
    logger.info(f"Processing query: {query}")
    
    # Check if we need to update data
    if should_run_ingestion():
        logger.info("Data is outdated. Running ingestion before processing query.")
        success = ingest_scenarios()
        if not success:
            return {
                'success': False,
                'message': 'Failed to update data from source. Please try again later.',
                'count': 0,
                'results': []
            }
    
    # Initialize FilterAgent
    filter_agent = FilterAgent()
    
    # Process the query
    try:
        result = filter_agent.process_query(query)
        logger.info(f"Query processed successfully. Found {len(result.get('results', []))} results")
        return result
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {
            'success': False,
            'message': f'Error processing query: {str(e)}',
            'count': 0,
            'results': []
        }

def run_once():
    """Run the ingestion process once without scheduling."""
    logger.info("Running one-time ingestion")
    
    # Initialize the database
    if not initialize_database():
        logger.error("Database initialization failed. Exiting.")
        return
    
    # Run ingestion once
    success = ingest_scenarios()
    
    if success:
        logger.info("One-time ingestion completed successfully")
    else:
        logger.info("One-time ingestion completed with no changes")

if __name__ == "__main__":
    # Use run_once() for testing
    run_once()
    # Uncomment the line below and comment the line above for scheduled operation
    # main()
