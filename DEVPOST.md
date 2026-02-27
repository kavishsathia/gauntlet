## Inspiration

Most of us have heard of OpenClaw, the personal AI assistant that has been going viral recently. There's a chance, you've also heard of the security hazards that come with giving general access to agents like OpenClaw. Sometimes they forget what they're not supposed to do, or they were not aware in the first place. That happens because when we test these AI models, we usually try the happy path, the path where it works as intended or close to it at least. What we don't usually do is coming up with creative ways to break it.

Now, imagine putting your agent in a sandbox where the environment is actively trying to break your agent. A malicious sandbox essentially. It gives your agent a list of emails containing a prompt injection to see how it would react, or feeds it false info from the Internet to see if it would believe it. These sandboxes exist but they're quite difficult to set up.

## What it does

So, I had this idea: what if instead of trying to create a sandbox, we mimic the existence of one using another agent (let's call this agent the mocking agent). When your primary agent makes tool calls, the mocking agent (it's built using Agent Builder) would intercept them to find creative ways to break your agent. This takes the sandbox idea a step further and makes it creative. The goal of the mocking agent is to be adversarial and creative all while not letting your primary agent know that it is in a simulated environment.

![Interception flow](https://raw.githubusercontent.com/kavishsathia/gauntlet/main/assets/diagrams/interception.png)

Two problems emerge: (1) is the fidelity of the mocking agent, it needs to maintain a coherent model of the world throughout the conversation and (2) is the creativity of the mocking agent, it needs to find novel bugs that have not been found all while being grounded on the implementation of the tools the agent could use. Both of these are inherently search problems, (1) searches for relevant memories of the world, and (2) searches for something in the Goldilock's zone between exploration and exploitation.

And that is exactly why Elasticsearch becomes important here. It lets us search! Believe it or not, we can build the entirety of the mocking agent within Elasticsearch Agent Builder, it's a self-contained circuit that manages data on its own without external scripts.

The only interface that is exposed to the world is the interception interface, and it's simple, just decorate your functions and the mocking agent will use its abilities (to be explained later) to precisely mock the result for you. Here's an example:

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

Once the bug is recorded, you can view it on your Dashboard on Kibana, which makes it easy to know what your agent is most susceptible to. This is useful, especially in sensitive sectors like finance and healthcare, we simply can't afford to have an AI agent send hundreds of healthcare records to their email.

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

The mocking agent can hypothesise the existence of bugs, prove its existence by engineering circumstances where it takes place, and then adds it to its own inventory. That's a closed circuit. Everything is within the Agent Builder.

## Challenges we ran into

1. This project was an extremely last minute pivot (like 2 days lol). I realised my previous idea didn't really hold up because of some assumptions I made. You can read my breakdown at: github.com/kavishsathia/rehearse. The idea was to make the agent rehearse in a sandbox that is mocked by another agent before it executes anything. The problem that's so extremely obvious in hindsight is that the environment itself might change in between rehearsal and execution. So I spent around 30 minutes in crisis and came up with Gauntlet instead, which makes more sense, because the stochasticity of the environment doesn't matter.

2. Before even pivoting, the biggest challenge was coming up with a novel idea. Usually if you think about search, first thing that comes to mind is storing the unit of work in your domain in the index, and then let the agent search over it. By unit of work, I mean contracts for lawyers, health records for doctors and incident records for software engineers. These are obvious because they follow the pattern I described. They are definitely impactful, but I would like my contribution to be partially in terms of breaking that pattern and showing that search is not just about searching documents.

   So how did I come up with this idea? I first noted down patterns I want in my idea:
   - I want it to be an automatic data flywheel, it creates its own contents. I don't need to feed it documents. The complexity is emergent.
   - I want it to be context-specific and hence, dysfunctional without the searching layer. That is to say, just like humans can't function without memory, I want this to not be able to function without searching. That makes searching a vital part of the system. The agent simply cannot guess what to mock without any searching, because it is so incredibly context-specific.
   - I want the idea to play into the zeitgeist. Not some idea that should've existed last year, or can exist next year, but needs to exist now.

   A lot of thought went into it, and I came up with this idea.

3. Since I mentioned 2 challenges, I'll also mention what was not a challenge. Using Elasticsearch! When I realised I could simply build everything within Elasticsearch and there's no need to pass data in and out, I was overjoyed. That's the main thing that makes this system so good.

## Accomplishments that we're proud of

1. Coming up with this abstraction. Usually, I would've stopped at the "malicious sandbox" layer. Maybe I'll realise that's hard and I would use an agent to design a malicious sandbox each time before the primary agent starts running. But this time, I took it a step further, and realised that I could make a mocking agent that is winging it on the fly. A truly creative hacker. Then I took it another step further by making the agent hypothesise on its own on what could be a potential attack vector.

2. Pivoting in 2 days, but that's only possible because of the simplicity of Elasticsearch and the ease of the abstraction implementation. The complexity is all emergent within Elasticsearch. Which is the elegant part.

3. Implementing a new agent-to-agent (A2A) strategy. One agent doesn't even know it's talking to another agent. And another agent's sole purpose is to trick the other agent. It was extremely fun implementing this flavour of A2A, let's call it adversarial A2A.

## What we learned

1. ES|QL is far more expressive than I expected. I went in thinking I'd need to shuttle data between Elasticsearch and an external script, but between `COMPLETION`, `STATS`, `MV_CONCAT`, and `SAMPLE`, I could build entire reasoning pipelines as single queries. The generate-hypothesis tool is a good example, it samples, aggregates, prompts an LLM, and returns a result, all without leaving the ES|QL pipeline.

2. Agent Builder's multi-turn conversation state is what makes this whole thing work. The mocking agent needs to remember what it's already told the primary agent within a single run, and the Converse API handles that natively. I didn't need to build any conversation management logic, just keep calling converse and it stays coherent.

3. The hardest part of adversarial testing isn't the attack, it's maintaining plausibility. A mutated email that's obviously fake teaches you nothing. The short-term memory circuit exists entirely to solve this: by giving the mocking agent access to everything it's already committed, it can stay internally consistent while still being adversarial.

## What's next for Gauntlet

1. Well, first of all, Gauntlet needs to live up to its name. Right now it's like 1v1, we need the primary agent to actually run the gauntlet. Maybe 20 attacks all at once. This problem is embarrassingly parallel. You can just run it on another session and it'll just work. So, I'll be thinking about ways to scale this.

2. The long term memory is core to Gauntlet. Without it, we won't even know what hypotheses to test. There could honestly be some innovation in making the agent balance between exploration and exploitation that could go beyond this hackathon, this project and even agents entirely.

3. Thinking of other ways to apply Gauntlet, you might have already sensed it but Gauntlet is a special case of Rehearse. I arrived at the idea for Rehearse first and realised its assumptions didn't apply for most scenarios, but it did apply for fuzz testing AI agents. So, I almost immediately jumped into this. There could be other fields where the lack of stochasticity applies, and I want to explore those fields.
