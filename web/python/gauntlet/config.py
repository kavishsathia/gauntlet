import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from current working directory
load_dotenv(Path.cwd() / ".env")


def _env(key: str, default: str = None) -> str:
    val = os.environ.get(key, default)
    if val is None:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"ApiKey {api_key}",
        "Content-Type": "application/json",
    }


class Config:
    @property
    def KIBANA_URL(self):
        return _env("KIBANA_URL")

    @property
    def ELASTICSEARCH_URL(self):
        return _env("ELASTICSEARCH_URL")

    @property
    def API_KEY(self):
        return _env("API_KEY")

    @property
    def INFERENCE_ID(self):
        return _env("INFERENCE_ID", "my_inference_endpoint")

    @property
    def EMBEDDING_INFERENCE_ID(self):
        return _env("EMBEDDING_INFERENCE_ID", "my_embedding_endpoint")

    @property
    def KIBANA_HEADERS(self):
        h = _headers(self.API_KEY)
        h["kbn-xsrf"] = "true"
        h["x-elastic-internal-origin"] = "Kibana"
        return h

    @property
    def ES_HEADERS(self):
        return _headers(self.API_KEY)


config = Config()

INDEX_STM = "gauntlet-stm"
INDEX_LTM_BUGS = "gauntlet-ltm-bugs"
INDEX_LTM_FUNC = "gauntlet-ltm-func"
INDEX_LTM_QUERIES = "gauntlet-ltm-queries"
