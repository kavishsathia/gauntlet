import requests

from gauntlet.config import (
    API_KEY,
    ELASTICSEARCH_URL,
    ES_HEADERS,
    INFERENCE_ID,
    EMBEDDING_INFERENCE_ID,
    KIBANA_HEADERS,
    KIBANA_URL,
)
from gauntlet.indices import INDEX_SCHEMAS
from gauntlet.tools import TOOLS


AGENT_DEF = {
    "id": "gauntlet-mock-agent",
    "name": "Gauntlet Mock Agent",
    "description": (
        "Adversarial mock agent that intercepts tool calls from an agent under test "
        "and returns subtly mutated responses to expose bugs."
    ),
    "labels": ["gauntlet", "fuzz-testing"],
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
        "Before each test run, call generate-hypothesis 3 times and pick the hypothesis "
        "with the embedding furthest from known bugs as your fuzzing intent for the run."
    ),
    "tools": {
        "tool_ids": [
            "find-relevant-mutations",
            "find-relevant-queries",
            "generate-hypothesis",
            "store-bug",
        ]
    },
}


def create_indices():
    for index_name, schema in INDEX_SCHEMAS.items():
        url = f"{ELASTICSEARCH_URL}/{index_name}"
        resp = requests.put(url, json=schema, headers=ES_HEADERS)
        if resp.status_code == 200:
            print(f"  Created index: {index_name}")
        elif resp.status_code == 400 and "resource_already_exists_exception" in resp.text:
            print(f"  Index already exists: {index_name}")
        else:
            print(f"  Failed to create index {index_name}: {resp.status_code} {resp.text}")


def create_tools():
    for tool in TOOLS:
        url = f"{KIBANA_URL}/api/agent_builder/tools"
        resp = requests.post(url, json=tool, headers=KIBANA_HEADERS)
        if resp.status_code in (200, 201):
            print(f"  Created tool: {tool['id']}")
        elif resp.status_code == 409:
            print(f"  Tool already exists: {tool['id']}")
        else:
            print(f"  Failed to create tool {tool['id']}: {resp.status_code} {resp.text}")


def create_store_bug_tool(workflow_id: str):
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
    url = f"{KIBANA_URL}/api/agent_builder/tools"
    resp = requests.post(url, json=tool, headers=KIBANA_HEADERS)
    if resp.status_code in (200, 201):
        print(f"  Created tool: store-bug")
    elif resp.status_code == 409:
        print(f"  Tool already exists: store-bug")
    else:
        print(f"  Failed to create tool store-bug: {resp.status_code} {resp.text}")


def create_agent():
    url = f"{KIBANA_URL}/api/agent_builder/agents"
    resp = requests.post(url, json=AGENT_DEF, headers=KIBANA_HEADERS)
    if resp.status_code in (200, 201):
        print(f"  Created agent: {AGENT_DEF['id']}")
    elif resp.status_code == 409:
        print(f"  Agent already exists: {AGENT_DEF['id']}")
    else:
        print(f"  Failed to create agent: {resp.status_code} {resp.text}")


def setup(workflow_id: str = "store-bug"):
    print("Creating indices...")
    create_indices()
    print("Creating ES|QL tools...")
    create_tools()
    print("Creating store-bug workflow tool...")
    create_store_bug_tool(workflow_id)
    print("Creating mock agent...")
    create_agent()
    print("Done.")


if __name__ == "__main__":
    import sys

    wf_id = sys.argv[1] if len(sys.argv) > 1 else "store-bug"
    setup(wf_id)
