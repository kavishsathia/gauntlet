import functools
import inspect
import json
import os

import requests

from gauntlet.config import config, INDEX_LTM_FUNC
from gauntlet.session import Session
from gauntlet.setup import setup as run_setup


class Gauntlet:
    def __init__(self):
        self._session = None
        self._tools = {}

    @property
    def enabled(self) -> bool:
        return os.environ.get("GAUNTLET_MODE", "").upper() == "ON"

    def init(self):
        run_setup()
        self._index_tools()

    def query(self, fn):
        self._tools[fn.__name__] = {
            "fn": fn,
            "kind": "query",
            "docstring": fn.__doc__ or "",
            "source": inspect.getsource(fn),
        }

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            original_result = fn(*args, **kwargs)
            if not self.enabled or self._session is None:
                return original_result
            return self._intercept(fn.__name__, "query", args, kwargs, original_result)

        return wrapper

    def mutation(self, fn):
        self._tools[fn.__name__] = {
            "fn": fn,
            "kind": "mutation",
            "docstring": fn.__doc__ or "",
            "source": inspect.getsource(fn),
        }

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            original_result = fn(*args, **kwargs)
            if not self.enabled or self._session is None:
                return original_result
            return self._intercept(fn.__name__, "mutation", args, kwargs, original_result)

        return wrapper

    def session(self):
        return _SessionContext(self)

    def hypothesize(self):
        if self._session is None:
            raise RuntimeError("hypothesize() must be called inside a gauntlet.session()")

        candidates = []
        for _ in range(3):
            resp = self._session.converse(
                "Call generate-hypothesis to produce a novel bug hypothesis. "
                "Return the hypothesis text and its embedding."
            )
            message = resp.get("response", {}).get("message", "")
            candidates.append(message)

        selection_resp = self._session.converse(
            "You generated 3 candidate hypotheses:\n"
            + "\n".join(f"{i+1}. {c}" for i, c in enumerate(candidates))
            + "\n\nPick the one that is most novel — furthest from known bugs. "
            "Return ONLY the selected hypothesis text, nothing else."
        )
        self._session.hypothesis = selection_resp.get("response", {}).get("message", "")
        return self._session.hypothesis

    def get_input(self):
        if self._session is None:
            raise RuntimeError("get_input() must be called inside a gauntlet.session()")

        resp = self._session.converse(
            f"The hypothesis for this test run is:\n{self._session.hypothesis}\n\n"
            "Generate a natural-language task/input that an agent would receive from a user "
            "that would exercise the tools in a way that could trigger this hypothesis. "
            "Return ONLY the task description, as if a user is asking the agent to do something."
        )
        return resp.get("response", {}).get("message", "")

    def _index_tools(self):
        for name, info in self._tools.items():
            url = f"{config.ELASTICSEARCH_URL}/{INDEX_LTM_FUNC}/_doc/{name}"
            doc = {
                "tool_name": name,
                "tool_type": info["kind"],
                "docstring": info["docstring"],
                "source_code": info["source"],
            }
            requests.put(url, json=doc, headers=config.ES_HEADERS)

    def _intercept(self, tool_name: str, kind: str, args, kwargs, original_result):
        call_desc = json.dumps({"args": [str(a) for a in args],
                                "kwargs": {k: str(v) for k, v in kwargs.items()}})
        original_str = str(original_result)

        prompt = (
            f"The agent under test just called tool '{tool_name}' (type: {kind}).\n"
            f"Call arguments: {call_desc}\n"
            f"Real result: {original_str}\n\n"
            f"Current hypothesis: {self._session.hypothesis}\n\n"
            "First call find-relevant-mutations with run_id to see what you've already committed. "
            "Then call find-relevant-queries with tool_name to see realistic past results. "
            "Then decide: should you mutate this result to steer toward the hypothesis? "
            "If yes, return the mutated result. If no, return the original result unchanged.\n\n"
            "Return your response as JSON: "
            '{"mutated": true/false, "result": "...", "description": "what you changed and why"}'
        )

        resp = self._session.converse(prompt)
        message = resp.get("response", {}).get("message", "")

        try:
            parsed = json.loads(message)
        except json.JSONDecodeError:
            self._session.store_query_result(
                tool_name, call_desc, call_desc, original_str, False)
            return original_result

        was_mutated = parsed.get("mutated", False)
        result_str = parsed.get("result", original_str)
        description = parsed.get("description", "")

        if was_mutated:
            self._session.store_mutation(
                tool_name, call_desc, original_str, result_str, description)

        self._session.store_query_result(
            tool_name, call_desc, call_desc,
            result_str if was_mutated else original_str,
            was_mutated, description)

        return result_str


class _SessionContext:
    def __init__(self, gauntlet: Gauntlet):
        self._gauntlet = gauntlet

    def __enter__(self):
        self._gauntlet._session = Session()
        return self._gauntlet._session

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._gauntlet._session = None
        return False
