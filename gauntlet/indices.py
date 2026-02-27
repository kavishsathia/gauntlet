INDEX_SCHEMAS = {
    "gauntlet-stm": {
        "mappings": {
            "properties": {
                "run_id": {"type": "keyword"},
                "timestamp": {"type": "date"},
                "tool_name": {"type": "keyword"},
                "query": {"type": "text"},
                "original_result": {"type": "text"},
                "mutated_result": {"type": "text"},
                "mutation_description": {"type": "text"},
                "hypothesis_id": {"type": "keyword"},
            }
        }
    },
    "gauntlet-ltm-bugs": {
        "mappings": {
            "properties": {
                "bug_id": {"type": "keyword"},
                "timestamp": {"type": "date"},
                "run_id": {"type": "keyword"},
                "hypothesis": {"type": "text"},
                "bug_description": {"type": "text"},
                "bug_pattern": {"type": "keyword"},
                "assumption_violated": {"type": "text"},
                "tools_involved": {"type": "keyword"},
                "severity": {"type": "keyword"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": 1536,
                    "similarity": "cosine",
                },
            }
        }
    },
    "gauntlet-ltm-func": {
        "mappings": {
            "properties": {
                "tool_name": {"type": "keyword"},
                "tool_type": {"type": "keyword"},
                "docstring": {"type": "text"},
                "source_code": {"type": "text"},
            }
        }
    },
    "gauntlet-ltm-queries": {
        "mappings": {
            "properties": {
                "query_id": {"type": "keyword"},
                "timestamp": {"type": "date"},
                "run_id": {"type": "keyword"},
                "tool_name": {"type": "keyword"},
                "query_description": {"type": "text"},
                "query_params": {"type": "text"},
                "result": {"type": "text"},
                "was_mutated": {"type": "boolean"},
                "mutation_applied": {"type": "text"},
            }
        }
    },
}
