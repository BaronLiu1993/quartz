from config import app


@app.task(name="ingestion.fetch_data")
def fetch_data(source_id):
    # Placeholder for data fetching logic based on source_id
    # This could involve API calls, database queries, etc.
    data = f"Fetched data for source {source_id}"
    return data