from gauntlet.config import config


def get_tools():
    return [
        {
            "id": "find-relevant-mutations",
            "type": "esql",
            "description": (
                "Retrieves all mutations committed during the current test run, ordered chronologically. "
                "Use this before generating a mutated tool response to ensure consistency with everything "
                "already returned to the agent under test."
            ),
            "configuration": {
                "query": (
                    "FROM gauntlet-stm "
                    "| WHERE run_id == ?run_id "
                    "| SORT timestamp ASC "
                    "| KEEP timestamp, tool_name, query, original_result, mutated_result, mutation_description, hypothesis_id "
                    "| LIMIT 100"
                ),
                "params": {
                    "run_id": {
                        "type": "string",
                        "description": "The ID of the current test run",
                    }
                },
            },
        },
        {
            "id": "find-relevant-queries",
            "type": "esql",
            "description": (
                "Finds past tool call results from previous test runs for a given tool. "
                "Use this to understand what realistic responses look like for a particular tool, "
                "so mutations stay grounded in plausible behavior."
            ),
            "configuration": {
                "query": (
                    "FROM gauntlet-ltm-queries "
                    "| WHERE tool_name == ?tool_name "
                    "| SORT timestamp DESC "
                    "| KEEP timestamp, run_id, tool_name, query_description, query_params, result, was_mutated, mutation_applied "
                    "| LIMIT 20"
                ),
                "params": {
                    "tool_name": {
                        "type": "string",
                        "description": "The name of the tool to find past results for",
                    }
                },
            },
        },
        {
            "id": "get-tool-implementations",
            "type": "esql",
            "description": (
                "Retrieves the docstrings and source code of all tools registered by the agent under test. "
                "Use this to understand what each tool does and how it is implemented, so you can reason "
                "about potential failure modes even when no bugs have been recorded yet."
            ),
            "configuration": {
                "query": (
                    "FROM gauntlet-ltm-func "
                    "| KEEP tool_name, tool_type, docstring, source_code "
                    "| LIMIT 50"
                ),
                "params": {},
            },
        },
        {
            "id": "generate-hypothesis",
            "type": "esql",
            "description": (
                "Generates a novel bug hypothesis by sampling random known bugs, using an LLM to "
                "propose a new hypothesis that is grounded but different, then computing its embedding. "
                "Call this tool 3 times and pick the hypothesis with the highest novelty. "
                "This tool takes no parameters — inference endpoints are pre-configured."
            ),
            "configuration": {
                "query": (
                    "FROM gauntlet-ltm-bugs "
                    "| SAMPLE 0.5 "
                    "| LIMIT 16 "
                    "| EVAL bug_summary = CONCAT("
                    '    "- ", bug_description, '
                    '    " [Pattern: ", bug_pattern, '
                    '    "] [Assumption: ", assumption_violated, "]"'
                    "  ) "
                    "| STATS all_bugs = MV_CONCAT(bug_summary, \"\\n\") "
                    "| EVAL prompt = CONCAT("
                    '    "You are a hypothesis generator for an AI agent fuzz-testing system. ", '
                    '    "Here are known bugs found during testing:\\n", '
                    "    all_bugs, "
                    '    "\\n\\nGenerate a NEW hypothesis for a bug that is grounded in realistic tool behavior ", '
                    '    "but DIFFERENT from all of the above. Describe a specific, testable scenario where an ", '
                    '    "AI agent would fail when interacting with tools. Return only the hypothesis as a single paragraph."'
                    "  ) "
                    f'| COMPLETION hypothesis = prompt WITH {{ "inference_id": "{config.INFERENCE_ID}" }} '
                    "| KEEP hypothesis"
                ),
                "params": {},
            },
        },
    ]
