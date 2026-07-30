# Multi-turn Simulation

The Harbor adapter sends ordinary messages through one unchanged Harness session. A Harness turn may contain any number of model or tool calls before returning a response.

```text
instruction.md -> Harness -> next user message -> same Harness session -> repeat
                                      |
                                      +-> stop
```

Choose one track:

- **Scripted conversation:** predefined messages for stable job steps. Example: “Inspect the failing checkout test” → “Implement the fix” → “Run the tests.”
- **LLM-simulated user:** generated messages when the user must answer, correct, reject, or stop based on the Harness response. Example: a traveler rejects an unsuitable flight and confirms a valid one.

Use [runner.py](runner.py) for both tracks: `run_scripted_conversation` sends fixed turns and `run_llm_user_conversation` alternates the Harness with [model_user.py](model_user.py). The LLM user receives an approved contract, visible transcript, and user-visible state; only malformed JSON is retried.

## Harbor wiring

Copy [runner.py](runner.py), [model_user.py](model_user.py), and [harbor_example.py](harbor_example.py) into `evals/harbor_agents/multi_turn/`, then subclass `MultiTurnHarborAgent`. Implement its explicit repository bindings:

1. `create_harness_session`: start the real Harness once and return an object whose `send` method preserves that session.
2. `scripted_followups` or `user_contract`: choose one simulation track.
3. `SIMULATOR_MODEL` and `call_user_model`: record the model name and connect its approved client when using an LLM user.
4. `read_user_observation`: return only state the simulated user could see; return `{}` when the transcript is sufficient.

The wrapper returns `HarnessReply(message, evidence)`. `message` is delivered to the user. `evidence` is JSON-safe activity directly recorded during that Harness turn, such as tool calls, results, state changes, and usage. Never infer tool use from prose or include credentials in `public_config`, observations, or evidence.

```python
class FlightSession:
    def __init__(self, real_agent, thread_id):
        self.real_agent = real_agent
        self.session_id = thread_id
        self.public_config = {"model": "agent-model", "tools": ["search", "book"]}

    async def send(self, user_message):
        result = await self.real_agent.send(user_message, thread_id=self.session_id)
        return HarnessReply(result.text, {"tool_calls": result.observed_tool_calls})

class FlightAdapter(MultiTurnHarborAgent):
    SIMULATOR_MODEL = "gpt-5.5"

    def user_contract(self) -> str:
        return """You are Sam, changing an August 12 return flight.
You know username sam. Require departure after 11am and added cost at most $100.
Answer questions, reject invalid options, and stop after confirmed booking or unrecoverable failure."""

    async def create_harness_session(self, environment, context):
        return FlightSession(real_agent, thread_id=self.logs_dir.parent.name)

    async def call_user_model(self, system, payload):
        return await approved_llm_json(system=system, prompt=payload)

    async def read_user_observation(self, environment):
        state = await booking_state(environment)
        return {"booking_confirmed": state["booked"] is not None}
```

`instruction.md` is the first Harness input. The adapter then alternates completed Harness turns and user messages; it does not add tools or prompts to the Harness. A stop decision adds no message and makes no further Harness call. Stopping never means success: the Verifier alone assigns reward.

## Calibrate and audit

Run the real Harness through behavior relevant to the task: a correct result, a wrong result, clarification, and unrecoverable failure when applicable. Inspect whether the simulated user responds and stops credibly. Revise the contract or simulator model and show representative conversations to the user. Do not duplicate the contract as brittle keyword checks.

When the user supplies real threads, use only observed facts, reactions, and stopping behavior relevant to this task to calibrate the simulated user. Do not copy identities, messages, or production records into the simulation.

The adapter writes `interaction.json` and chronological ATIF `trajectory.json`, including partial evidence on Harness or simulator failure. Confirm that one session was reused, future messages were not preloaded, no Harness call followed stop, artifacts and Verifier output are readable, and the Verifier measures the Harness rather than the simulator.
