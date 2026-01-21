#!/usr/bin/env python3
"""
Test: Verify Claude Code can query LangSmith traces

TASK FOR CLAUDE CODE:
====================
1. Use the langsmith-trace skill to list the 5 most recent traces
2. Use the skill to get details about the first trace (most recent)
3. Store the trace ID in /tmp/test_trace_id.txt

VALIDATION:
===========
This script checks:
- The trace ID file was created
- The trace ID is valid (UUID format)
- The trace exists in LangSmith and can be retrieved
"""

import os
import sys
import re
from pathlib import Path
from langsmith import Client
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def validate_uuid(uuid_string):
    """Check if string is valid UUID."""
    uuid_pattern = re.compile(
        r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(uuid_string))

def main():
    print("=" * 60)
    print("LangSmith Trace Query Test - Validation")
    print("=" * 60)

    # Check if trace ID file exists
    trace_id_file = Path("/tmp/test_trace_id.txt")
    if not trace_id_file.exists():
        print("❌ FAILED: /tmp/test_trace_id.txt not found")
        print("   Claude Code should have created this file with a trace ID")
        sys.exit(1)

    print("✓ Trace ID file exists")

    # Read trace ID
    trace_id = trace_id_file.read_text().strip()
    print(f"  Trace ID: {trace_id}")

    # Validate UUID format
    if not validate_uuid(trace_id):
        print(f"❌ FAILED: '{trace_id}' is not a valid UUID")
        sys.exit(1)

    print("✓ Trace ID is valid UUID format")

    # Verify trace exists in LangSmith
    try:
        client = Client()
        run = client.read_run(trace_id)
        print(f"✓ Trace exists in LangSmith")
        print(f"  Name: {run.name}")
        print(f"  Start time: {run.start_time}")

        # Check if it's actually a recent trace (within last 30 days)
        if run.start_time:
            age = datetime.now(run.start_time.tzinfo) - run.start_time
            if age > timedelta(days=30):
                print(f"⚠️  WARNING: Trace is {age.days} days old (expected recent trace)")
            else:
                print(f"✓ Trace is recent ({age.days} days old)")

    except Exception as e:
        print(f"❌ FAILED: Could not retrieve trace from LangSmith")
        print(f"   Error: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print("\nClaude Code successfully:")
    print("- Queried recent traces using langsmith-trace skill")
    print("- Extracted a valid trace ID")
    print("- The trace exists and is accessible in LangSmith")

if __name__ == "__main__":
    main()
