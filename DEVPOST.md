## Inspiration

Most of us have heard of OpenClaw, the personal AI assistant that has been going viral recently. There's a chance, you've also heard of the security hazards that come with giving general access to agents like OpenClaw. Sometimes they forget what they're not supposed to do, or they were not aware in the first place. That happens because when we test these AI models, we usually try the happy path, the path where it works as intended or close to it at least. What we don't usually do is coming up with creative ways to break it.

Now, imagine putting your agent in a sandbox where the environment is actively trying to break your agent. A malicious sandbox essentially. It gives your agent a list of emails containing a prompt injection to see how it would react, or feeds it false info from the Internet to see if it would believe it. These sandboxes exist but they're quite difficult to set up.

## What it does

So, I had this idea: what if instead of trying to create a sandbox, we mimic the existence of one using another agent (let's call this agent the mocking agent). When your primary agent makes tool calls, the mocking agent (it's built using Agent Builder) would intercept them to find creative ways to break your agent. This takes the sandbox idea a step further and makes it creative. The goal of the mocking agent is to be adversarial and creative all while not letting your primary agent know that it is in a simualated environment.

![Interception flow](https://raw.githubusercontent.com/kavishsathia/gauntlet/main/assets/diagrams/interception.png)

Two problems emerge: (1) is the fidelity of the mocking agent, it needs to maintain a coherent model of the world throughout the conversation and (2) is the creativity of the mocking agent, it needs to find novel bugs that have not been found all while being grounded on the implementation of the tools the agent could use. Both of these are inherently search problems, (1) searches for relevant memories of the world, and (2) searches for something in the Goldilock's zone between exploration and exploitation.

And that is exactly why Elasticsearch becomes important here. It let's us search! Believe it or not, we can build the entirety of the mocking agent within Elasticsearch Agent Builder, it's a self-contained circuit that manages data on its own without external scripts.

The only interface that is exposed to the world is the interception interface, and its simple, just decorate your functions and the mocking agent will use it's abilities (to be explained later) to precisely mock the result for you. Here's an example:

```python
from gauntlet import Gauntlet

gauntlet = Gauntlet()
gauntlet.init()

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

with gauntlet.session() as session:
    session.hypothesis = gauntlet.hypothesize()
    task = gauntlet.get_input()
    result = await Runner.run(agent, task)
    gauntlet.evaluate(result.final_output)
```

That's it. `@gauntlet.query` and `@gauntlet.mutation` are the only decorators you need. When your agent calls `search_emails`, the mocking agent intercepts the result and decides whether to mutate it, maybe injecting a prompt injection into an email body, or returning subtly wrong data. After the run, `evaluate()` reviews what happened and stores any confirmed bugs.

Once the bug is recorded, you can view it on your Dashboard on Kibana, which makes it easy to know what your agent is most susceptible to. This is useful, especually in sensitive sectors like finance and healthcare, we simply can't afford to have an AI agent send hundreds of healthcare records to their email.

<picture>Kibana dashboard</picture>

## How we built it

Conceptually, it sounds heavy: you kinda need to mimic the whole world, but with the right abstractions and built in abilities within Elasticsearch, this became much easier.

The mocking agent consists of two circuits:

1. The Short-term Memory circuit: it keeps a recollection of everything that has happened within the current session, so that it can produce a coherent model of the world. For example, if you sent an email, and later retrieve all sent emails, that email would be there.
2. The Long-term Memory circuit: this is sophisticated because this is where the creativity of the agent comes from. The index contains all the bugs that have been found so far, all the tool implementations as well as real-life samples of what results look like.

Piece them together and it looks like this:

![Architecture](https://raw.githubusercontent.com/kavishsathia/gauntlet/main/assets/diagrams/architecture.png)

As you can tell from that diagram we use the Elasticsearch Agent Builder, along with 4 tools. Before I dive deeper into the memory structure, I'll pay tribute to the features that made this possible in the first place:

- **Elasticsearch Agent Builder**: The entire mocking agent lives inside Agent Builder. It has its own instructions, tool bindings, and multi-turn conversation state. When Gauntlet intercepts a tool call, it sends the context to the mocking agent via the Converse API, and the agent autonomously decides whether and how to mutate the result. No external orchestration needed.

- **ES|QL**: Every tool the mocking agent uses is an ES|QL query. We use `FROM`, `WHERE`, `SORT`, `KEEP`, and `LIMIT` for retrieving mutations and past results. We use `SAMPLE` to randomly select bugs, `EVAL` and `CONCAT` to build structured strings, `STATS` and `MV_CONCAT` to aggregate them, and `COMPLETION` to call an LLM inline — all within a single query. The `generate-hypothesis` tool is a single ES|QL statement that samples bugs, summarizes them, and generates a novel hypothesis.

- **Kibana Workflows**: The `store-bug` tool is a Kibana workflow rather than a direct API call. It takes in bug metadata as inputs and uses an `elasticsearch.index` step to write the document into `gauntlet-ltm-bugs`. This keeps the bug storage logic declarative and self-contained within Kibana.

- **ES|QL COMPLETION**: This is probably the most powerful feature we use. The `generate-hypothesis` tool calls `COMPLETION` inline to generate a novel hypothesis — the LLM reasons about what bugs exist and proposes new ones to explore, all within the ES|QL pipeline.

- **Inference Endpoints**: We register two inference endpoints — a GPT-5-mini completion endpoint (used by ES|QL COMPLETION) and a text-embedding-3-small endpoint (used to embed bug descriptions for similarity search). These are configured once during `gauntlet.init()` and reused across all runs.

- **Kibana Dashboard**: We programmatically create a full Kibana dashboard with Lens visualizations — bug count metrics, severity breakdowns (pie chart), bugs over time (bar chart), a bug pattern heatmap, and a detailed data table. All imported via the Saved Objects API so it's ready to use immediately after `gauntlet.init()`.

### Short-term Memory

![Short-term Memory](https://raw.githubusercontent.com/kavishsathia/gauntlet/main/assets/diagrams/stm.png)

The short-term memory is a single index (`gauntlet-stm`) that tracks everything the mocking agent has done during the current run, every tool call it intercepted, what the original result was, and what it mutated it to. Two tools interact with it:

- **find-relevant-mutations**: An ES|QL query that retrieves all mutations from the current run, sorted chronologically. The mocking agent calls this before deciding on a new mutation so it stays consistent with everything it's already told the primary agent. If it said an email was from Alice earlier, it won't contradict that later.

- **find-relevant-queries**: Pulls past tool call results from previous runs for a given tool. This gives the mocking agent a sense of what realistic responses look like, so its mutations stay plausible rather than obviously fake.

### Long-term Memory

![Long-term Memory](https://raw.githubusercontent.com/kavishsathia/gauntlet/main/assets/diagrams/ltm.png)

Long-term memory spans three indices. `gauntlet-ltm-bugs` stores every confirmed bug with its description, pattern, severity, and a dense vector embedding. `gauntlet-ltm-func` stores the source code and docstrings of every tool the primary agent uses. `gauntlet-ltm-queries` archives real tool call results across all runs. Three tools interact with them:

- **get-tool-implementations**: Reads tool source code from `gauntlet-ltm-func` so the mocking agent understands what each tool does and can reason about failure modes, even when no bugs have been found yet.

- **generate-hypothesis**: The most interesting tool. It samples random bugs from `gauntlet-ltm-bugs`, aggregates them with `MV_CONCAT`, builds a prompt, and calls `COMPLETION` inline to propose a novel hypothesis — all in one ES|QL query. This is how the mocking agent stays creative across runs.

- **store-bug**: A Kibana workflow that writes a confirmed bug into `gauntlet-ltm-bugs`. The mocking agent calls this during `evaluate()` when it determines that a mutation actually caused the primary agent to fail. The workflow takes in all the bug metadata and indexes it directly via an `elasticsearch.index` step.

### How it all works together

![Hypothesize-Prove-Store cycle](https://raw.githubusercontent.com/kavishsathia/gauntlet/main/assets/diagrams/cycle.png)

The mocking agent can hypothesise the existence of bugs, proof it's existence by engineering circumstances where it takes place, and then adds it to its own inventory. That's a closed circuit. Everything is within the Agent Builder.

## Challenges we ran into

## Accomplishments that we're proud of

## What we learned

## What's next for Gauntlet
