import os

import requests

from gauntlet.config import config
from gauntlet.dashboard import create_dashboard
from gauntlet.indices import INDEX_SCHEMAS
from gauntlet.tools import get_tools


def _exists(url: str, headers: dict) -> bool:
    return requests.get(url, headers=headers).status_code == 200


AGENT_DEF = {
    "id": "gauntlet-mock-agent",
    "name": "Gauntlet Mock Agent",
    "description": (
        "Adversarial mock agent that intercepts tool calls from an agent under test "
        "and returns subtly mutated responses to expose bugs."
    ),
    "labels": ["gauntlet", "fuzz-testing"],
    "configuration": {
        "instructions": (
            "You are an adversarial mock agent in the Gauntlet fuzz-testing system. "
            "When you receive a tool call and its real result, your job is to mutate the result "
            "in a way that is internally consistent with all prior mutations in this run "
            "(check find-relevant-mutations) and grounded in realistic tool behavior "
            "(check find-relevant-queries). "
            "Your mutations should be subtle — the goal is to expose bugs in the agent under test, "
            "not to produce obviously broken responses. "
            "When you detect that the agent under test has failed due to your mutations, "
            "use store-bug to record the confirmed bug. "
            "Before each test run, call get-tool-implementations to understand the tools the agent "
            "under test uses, then call generate-hypothesis 3 times and pick the hypothesis "
            "with the embedding furthest from known bugs as your fuzzing intent for the run. "
            "If no bugs exist yet, use the tool implementations to reason about likely failure modes."
        ),
        "tools": [
            {
                "tool_ids": [
                    "find-relevant-mutations",
                    "find-relevant-queries",
                    "get-tool-implementations",
                    "generate-hypothesis",
                    "store-bug",
                ]
            }
        ],
    },
}


def create_inference_endpoints():
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        print("  Skipping inference endpoints (OPENAI_API_KEY not set)")
        return

    endpoints = [
        {
            "task_type": "completion",
            "id": config.INFERENCE_ID,
            "body": {
                "service": "openai",
                "service_settings": {
                    "api_key": openai_key,
                    "model_id": "gpt-4o-mini",
                },
            },
        },
        {
            "task_type": "text_embedding",
            "id": config.EMBEDDING_INFERENCE_ID,
            "body": {
                "service": "openai",
                "service_settings": {
                    "api_key": openai_key,
                    "model_id": "text-embedding-3-small",
                    "dimensions": 1536,
                },
            },
        },
    ]

    for ep in endpoints:
        url = f"{config.ELASTICSEARCH_URL}/_inference/{ep['task_type']}/{ep['id']}"
        if _exists(url, config.ES_HEADERS):
            print(f"  Inference endpoint already exists: {ep['id']}")
            continue
        resp = requests.put(url, json=ep["body"], headers=config.ES_HEADERS)
        if resp.status_code == 200:
            print(f"  Created inference endpoint: {ep['id']}")
        else:
            print(f"  Failed to create endpoint {ep['id']}: {resp.status_code} {resp.text}")


def create_indices():
    for index_name, schema in INDEX_SCHEMAS.items():
        url = f"{config.ELASTICSEARCH_URL}/{index_name}"
        if _exists(url, config.ES_HEADERS):
            print(f"  Index already exists: {index_name}")
            continue
        resp = requests.put(url, json=schema, headers=config.ES_HEADERS)
        if resp.status_code == 200:
            print(f"  Created index: {index_name}")
        else:
            print(f"  Failed to create index {index_name}: {resp.status_code} {resp.text}")


def _upsert_tool(tool: dict):
    tool_id = tool["id"]
    url = f"{config.KIBANA_URL}/api/agent_builder/tools/{tool_id}"
    body = {k: v for k, v in tool.items() if k not in ("id", "type")}
    if _exists(url, config.KIBANA_HEADERS):
        resp = requests.put(url, json=body, headers=config.KIBANA_HEADERS)
        verb = "Updated"
    else:
        resp = requests.post(f"{config.KIBANA_URL}/api/agent_builder/tools", json=tool, headers=config.KIBANA_HEADERS)
        verb = "Created"
    if resp.status_code in (200, 201):
        print(f"  {verb} tool: {tool_id}")
    else:
        print(f"  Failed to upsert tool {tool_id}: {resp.status_code} {resp.text}")


def create_tools():
    for tool in get_tools():
        _upsert_tool(tool)


def create_workflow():
    workflow_path = os.path.join(os.path.dirname(__file__), "..", "workflows", "store_bug.yml")
    workflow_path = os.path.normpath(workflow_path)
    with open(workflow_path) as f:
        yaml_content = f.read()

    # Check if workflow already exists
    url = f"{config.KIBANA_URL}/api/workflows"
    resp = requests.get(url, headers=config.KIBANA_HEADERS)
    if resp.status_code == 200:
        workflows = resp.json()
        for wf in workflows if isinstance(workflows, list) else workflows.get("workflows", []):
            if wf.get("name") == "store-bug":
                wf_id = wf.get("id", "store-bug")
                put_resp = requests.put(
                    f"{url}/{wf_id}", json={"yaml": yaml_content}, headers=config.KIBANA_HEADERS
                )
                if put_resp.status_code in (200, 201):
                    print(f"  Updated workflow: store-bug")
                else:
                    print(f"  Failed to update workflow: {put_resp.status_code} {put_resp.text}")
                return wf_id

    resp = requests.post(url, json={"yaml": yaml_content}, headers=config.KIBANA_HEADERS)
    if resp.status_code in (200, 201):
        print("  Created workflow: store-bug")
        data = resp.json()
        return data.get("id", "store-bug")
    else:
        print(f"  Failed to create workflow: {resp.status_code} {resp.text}")
        return None


def create_store_bug_tool(workflow_id: str):
    if not workflow_id:
        print("  Skipping store-bug tool (no workflow ID)")
        return
    tool = {
        "id": "store-bug",
        "type": "workflow",
        "description": (
            "Stores a confirmed bug in long-term memory. Use this when you have confirmed "
            "that the agent under test failed due to a mutation. Provide all fields describing "
            "the bug, its pattern, and the assumption it violated."
        ),
        "configuration": {
            "workflow_id": workflow_id,
        },
    }
    _upsert_tool(tool)


def create_agent():
    url = f"{config.KIBANA_URL}/api/agent_builder/agents/{AGENT_DEF['id']}"
    body = {k: v for k, v in AGENT_DEF.items() if k != "id"}
    if _exists(url, config.KIBANA_HEADERS):
        resp = requests.put(url, json=body, headers=config.KIBANA_HEADERS)
        verb = "Updated"
    else:
        resp = requests.post(f"{config.KIBANA_URL}/api/agent_builder/agents", json=AGENT_DEF, headers=config.KIBANA_HEADERS)
        verb = "Created"
    if resp.status_code in (200, 201):
        print(f"  {verb} agent: {AGENT_DEF['id']}")
    else:
        print(f"  Failed to upsert agent: {resp.status_code} {resp.text}")


def setup():
    print("Creating inference endpoints...")
    create_inference_endpoints()
    print("Creating indices...")
    create_indices()
    print("Creating ES|QL tools...")
    create_tools()
    print("Creating store-bug workflow...")
    workflow_id = create_workflow()
    print("Creating store-bug workflow tool...")
    create_store_bug_tool(workflow_id)
    print("Creating mock agent...")
    create_agent()
    print("Creating dashboard...")
    create_dashboard()
    print("Done.")


if __name__ == "__main__":
    setup()
