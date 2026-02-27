import os
from dotenv import load_dotenv

load_dotenv()

KIBANA_URL = os.environ["KIBANA_URL"]
ELASTICSEARCH_URL = os.environ["ELASTICSEARCH_URL"]
API_KEY = os.environ["API_KEY"]
INFERENCE_ID = os.environ.get("INFERENCE_ID", "my_inference_endpoint")
EMBEDDING_INFERENCE_ID = os.environ.get("EMBEDDING_INFERENCE_ID", "my_embedding_endpoint")

KIBANA_HEADERS = {
    "Authorization": f"ApiKey {API_KEY}",
    "kbn-xsrf": "true",
    "Content-Type": "application/json",
}

ES_HEADERS = {
    "Authorization": f"ApiKey {API_KEY}",
    "Content-Type": "application/json",
}

INDEX_STM = "gauntlet-stm"
INDEX_LTM_BUGS = "gauntlet-ltm-bugs"
INDEX_LTM_QUERIES = "gauntlet-ltm-queries"
