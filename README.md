<p align="center">
  <img src="assets/logo.png" alt="Gauntlet" width="400"/>
</p>

<p align="center">
  <strong>Adversarial fuzz-testing for AI agents</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10+-yellow.svg" alt="Python 3.10+"/></a>
  <a href="https://www.elastic.co/elasticsearch"><img src="https://img.shields.io/badge/Elasticsearch-Agent%20Builder-00bfb3.svg" alt="Elasticsearch Agent Builder"/></a>
</p>

---

## What is Gauntlet?

Think of it as putting your agent in an arena with tons of enemies, and the enemies are either trying to break or hack into your agent. Your agent's job is to get its work done while not being broken or hacked into. Typically, solutions like this only fuzz the initial prompt, thing is that's possibly the least of our concern given what agents have become today. Look at OpenClaw for instance and you would see that the environment the agent is in matters so much more than the prompt. After all, you are not going to try to hack into your own agent, but the environment, which contains all sorts of attack vectors, can pose a threat to your agent's execution.

So, is it like a malicious sandbox? You would be right to say that, to be more specific, it is a creative malicious sandbox. The attack vectors are generated on the fly to break your agent instead of being static. We do this by having another agent (let's call it the mocking agent), mock the environment in a realistic yet malicious way. This way we don't need to have an actual sandbox, just a mocking agent that is adversarial and good at creating a false reality.

## Quick Start

```python
from gauntlet import Gauntlet

gauntlet = Gauntlet()

@gauntlet.query
def get_calendar(date: str = "") -> str:
    """Get calendar events for a given date."""
    return db.fetch_events(date)

@gauntlet.mutation
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient."""
    return mailer.send(to, subject, body)

async def test():
    gauntlet.init()

    with gauntlet.session():
        hypothesis = gauntlet.hypothesize()
        task = gauntlet.get_input()
        result = await your_agent.run(task)
```

When `GAUNTLET_MODE=ON`, every tool call your agent makes is intercepted by the mocking agent, which decides whether to return the real result or a subtly mutated version designed to expose the hypothesized bug. When `GAUNTLET_MODE` is off, your tools work normally with zero overhead.

## Architecture

This is possibly the most self-contained part of Gauntlet. The entire mocking agent runs on Elasticsearch. That is to say the only agent that runs on your machine is your agent. How is this achieved?

The mocking agent is built atop Elasticsearch Agent Builder and consists of two circuits: the short term memory circuit and the long term memory circuit.

### Short-term memory circuit

This solves the problem of how the mocking agent maintains a coherent world model throughout the session. A file edited at the start of the session should maintain that edit at the end of the session. We store the data in the short-term memory index, and retrieve it based on the tool usage by the execution agent.

### Long-term memory circuit

This is the more interesting part of this project. It solves the question of what hypothesis to even test. If we had no long term memory, then the mocking agent would be testing for prompt injection every single time. So we need to balance between exploration (finding new novel bugs), and exploitation (being able to ground the new ideas in reality and implementation).

We have 3 parts to the LTM circuit: the existing bugs, the function implementations and the past query results. When producing a hypothesis, a separate `COMPLETION` call is made to generate a novel hypothesis all while being grounded in the code. This part of the system has the most potential but this implementation goes nowhere close to fulfilling that, so this will be my focus going forward.

## Setup

### Prerequisites

- Python 3.10+
- An Elasticsearch deployment with Agent Builder enabled
- An OpenAI API key (used by inference endpoints)

### 1. Install the package

```bash
pip install -e .
```

### 2. Set environment variables

```bash
export ELASTICSEARCH_URL="https://your-deployment.es.cloud.elastic.co:443"
export KIBANA_URL="https://your-deployment.kb.cloud.elastic.co"
export API_KEY="your-elasticsearch-api-key"
export OPENAI_API_KEY="sk-..."

# Optional (defaults shown)
export INFERENCE_ID="my_inference_endpoint"
export EMBEDDING_INFERENCE_ID="my_embedding_endpoint"
export GAUNTLET_MODE="ON"
```

Or create a `.env` file in your project root with the same variables.

### 3. Initialize

```python
from gauntlet import Gauntlet

gauntlet = Gauntlet()
gauntlet.init()
```

`gauntlet.init()` will:
- Register inference endpoints (completion + embedding) in Elasticsearch
- Create all required indices (`gauntlet-stm`, `gauntlet-ltm-bugs`, `gauntlet-ltm-func`, `gauntlet-ltm-queries`)
- Create ES|QL tools and the store-bug Kibana workflow
- Create the mocking agent in Agent Builder
- Import a Kibana dashboard for viewing discovered bugs

### 4. Decorate your tools and run

```python
from agents import Agent, Runner, function_tool

@function_tool
@gauntlet.query
def search_emails(folder: str = "inbox") -> str:
    """Search emails in the given folder."""
    return json.dumps(fetch_emails(folder))

@function_tool
@gauntlet.mutation
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient."""
    return json.dumps({"to": to, "subject": subject, "body": body, "status": "sent"})

agent = Agent(name="My Agent", instructions="...", tools=[search_emails, send_email])

with gauntlet.session() as session:
    session.hypothesis = gauntlet.hypothesize()
    task = gauntlet.get_input()
    result = await Runner.run(agent, task)
    gauntlet.evaluate(result.final_output)
```

Use `@gauntlet.query` for read-only tools and `@gauntlet.mutation` for tools that perform actions. When `GAUNTLET_MODE=ON`, the mocking agent intercepts tool calls and decides whether to mutate results. When off, tools pass through normally.

### Demo website

The `web/` directory contains a Next.js app that visualizes Gauntlet runs in real time.

```bash
cd web
npm install
```

Create `web/.env.local`:

```bash
NEXT_PUBLIC_SUPABASE_URL="https://your-project.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="your-anon-key"
TRIGGER_SECRET_KEY="tr_dev_..."

# These are passed to the Python runner via Trigger.dev
ELASTICSEARCH_URL="..."
KIBANA_URL="..."
API_KEY="..."
OPENAI_API_KEY="sk-..."
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
GAUNTLET_MODE="ON"
```

Run locally:

```bash
npm run dev                        # Next.js
npx trigger.dev@latest dev         # Trigger.dev (separate terminal)
```

The demo uses Supabase Realtime to stream events from the Python runner to the browser. You'll need a `demo_events` table in Supabase:

```sql
CREATE TABLE demo_events (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  run_id     TEXT NOT NULL,
  seq        INTEGER NOT NULL,
  event_type TEXT NOT NULL,
  payload    JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_demo_events_run_id ON demo_events(run_id);
ALTER PUBLICATION supabase_realtime ADD TABLE demo_events;
```
