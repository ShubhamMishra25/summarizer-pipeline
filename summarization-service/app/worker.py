import os
import time
import json
import logging
import redis
from model import SummarizerEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
INPUT_QUEUE = os.getenv("REDIS_INPUT_QUEUE", "summarization_queue")
SUMMARIES_DIR = os.getenv("SUMMARIES_DIR", "/shared/summaries")

os.makedirs(SUMMARIES_DIR, exist_ok=True)

def get_redis_connection():
    while True:
        try:
            client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
            client.ping()
            logging.info("Connected to Redis successfully.")
            return client
        except redis.ConnectionError:
            logging.warning("Redis not reachable. Retrying in 2 seconds...")
            time.sleep(2)

def update_job_metadata(r: redis.Redis, job_id: str, updates: dict):
    data_str = r.get(f"job:{job_id}")
    if data_str:
        job_data = json.loads(data_str)
        job_data.update(updates)
        r.set(f"job:{job_id}", json.dumps(job_data))

def main():
    r = get_redis_connection()
    engine = SummarizerEngine()
    logging.info(f"Summarization Worker ready. Listening on '{INPUT_QUEUE}'...")

    while True:
        try:
            item = r.blpop(INPUT_QUEUE, timeout=5)
            if not item:
                continue

            _, message_json = item
            payload = json.loads(message_json)
            job_id = payload["job_id"]
            cleaned_text_path = payload["cleaned_text_path"]

            logging.info(f"Processing Job [{job_id}] - Starting AI inference...")
            update_job_metadata(r, job_id, {"status": "summarizing"})

            with open(cleaned_text_path, "r", encoding="utf-8") as f:
                raw_text = f.read()

            start_time = time.time()
            summary = engine.summarize(raw_text)
            inference_duration = round(time.time() - start_time, 2)

            summary_file_path = os.path.join(SUMMARIES_DIR, f"{job_id}_summary.txt")
            with open(summary_file_path, "w", encoding="utf-8") as f:
                f.write(summary)

            update_job_metadata(r, job_id, {
                "status": "completed",
                "summary": summary,
                "summary_file_path": summary_file_path,
                "inference_time_seconds": inference_duration
            })
            logging.info(f"Job [{job_id}] completed in {inference_duration}s.")

        except Exception as e:
            logging.error(f"Inference error: {str(e)}")
            if 'job_id' in locals():
                update_job_metadata(r, job_id, {
                    "status": "failed",
                    "error": f"Summarization error: {str(e)}"
                })

if __name__ == "__main__":
    main()
