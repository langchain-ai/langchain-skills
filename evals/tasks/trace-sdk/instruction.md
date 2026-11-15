The support assistant in `/app` runs as two services. `assistant.py` handles
each user turn and calls the tools service (`tools_service.py`) over HTTP for
documentation search and ticket creation. `python run_conversations.py` starts
the tools service, plays three recorded conversations, and stops the service.

Add LangSmith tracing to this app. Send its traces to the `development`
environment of the registered LangSmith agent whose ID is in the
`TARGET_AGENT_ID` environment variable. Each user turn should be a single trace
that includes the work the tools service does for that turn, and each
conversation should appear as one thread. Keep the assistant's behavior
unchanged.

Run the conversations, verify in LangSmith what you can, and report what you
changed and any limitations.
