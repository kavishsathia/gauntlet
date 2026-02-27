import uuid
from datetime import datetime, timezone

import requests

from gauntlet.config import config, INDEX_STM


class Session:
    def __init__(self, agent_id: str = "gauntlet-mock-agent"):
        self.run_id = str(uuid.uuid4())
        self.agent_id = agent_id
        self.conversation_id = None
        self.hypothesis = None
        self.hypothesis_embedding = None

    def converse(self, message: str) -> dict:
        url = f"{config.KIBANA_URL}/api/agent_builder/converse"
        body = {
            "input": message,
            "agent_id": self.agent_id,
        }
        if self.conversation_id:
            body["conversation_id"] = self.conversation_id
        resp = requests.post(url, json=body, headers=config.KIBANA_HEADERS)
        resp.raise_for_status()
        data = resp.json()
        self.conversation_id = data.get("conversation_id")
        return data

    def store_mutation(self, tool_name: str, query: str, original_result: str,
                       mutated_result: str, mutation_description: str):
        doc = {
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_name": tool_name,
            "query": query,
            "original_result": original_result,
            "mutated_result": mutated_result,
            "mutation_description": mutation_description,
            "hypothesis_id": self.hypothesis or "",
        }
        url = f"{config.ELASTICSEARCH_URL}/{INDEX_STM}/_doc"
        resp = requests.post(url, json=doc, headers=config.ES_HEADERS)
        resp.raise_for_status()

    def store_query_result(self, tool_name: str, query_description: str,
                           query_params: str, result: str, was_mutated: bool,
                           mutation_applied: str = ""):
        doc = {
            "query_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "tool_name": tool_name,
            "query_description": query_description,
            "query_params": query_params,
            "result": result,
            "was_mutated": was_mutated,
            "mutation_applied": mutation_applied,
        }
        url = f"{config.ELASTICSEARCH_URL}/gauntlet-ltm-queries/_doc"
        resp = requests.post(url, json=doc, headers=config.ES_HEADERS)
        resp.raise_for_status()
