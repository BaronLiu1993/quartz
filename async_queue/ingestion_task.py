from config import app


@app.task(name="ingestion.fetch_data")
def fetch_data(source_id):
    data = f"Fetched data for source {source_id}"
    return data