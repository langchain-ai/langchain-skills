Add an online evaluator to the LangSmith tracing project identified by
`TARGET_PROJECT_ID` in the environment.

The assistant behind this project answers product questions and can create
support tickets. Conversations span several turns. Once a conversation has
finished, an LLM judge should score whether the user's issue was resolved by
the end of the conversation and explain its reasoning. It should evaluate each
conversation thread as a whole, not individual turns.

Use the available sample traces to understand the data. Configure the
evaluator in the workspace, verify what you can, and report what you created
and any limitations.
