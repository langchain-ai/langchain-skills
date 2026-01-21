#!/usr/bin/env python3
"""
Simple Text-to-SQL Test Agent

Uses DeepAgents to create a proper agent with unified traces.
"""

import os
import sys
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

# Load environment variables
load_dotenv()


def create_sql_agent():
    """Create a SQL Deep Agent with proper trace hierarchy."""
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Connect to Chinook database
    db_path = os.path.join(script_dir, "chinook.db")
    db = SQLDatabase.from_uri(
        f"sqlite:///{db_path}",
        sample_rows_in_table_info=3
    )

    # Initialize OpenAI model
    model = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY")
    )

    # Create SQL toolkit
    toolkit = SQLDatabaseToolkit(db=db, llm=model)
    sql_tools = toolkit.get_tools()

    # Agent instructions (from deepagents text-to-sql-agent example)
    agent_instructions = """# Text-to-SQL Agent

You are a Deep Agent that interfaces with SQL databases.

## Core Responsibilities
- Explore the available database tables
- Examine relevant table schemas
- Generate syntactically correct SQL queries
- Execute queries and analyze results
- Format answers in a clear, readable way

## Database
You are working with a SQLite database containing the Chinook dataset - data about a digital media store: artists, albums, tracks, customers, invoices, employees.

## Operational Parameters
- Query results default to 5 rows unless user specifies otherwise
- Results should be ordered by relevant columns
- Only retrieve necessary columns
- Verify SQL syntax before execution

## Critical Restrictions
**READ-ONLY ACCESS**: NEVER execute INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE. Only SELECT operations are permitted.

## Schema Exploration
When you need to understand database structure:
1. List tables using `sql_db_list_tables` to see what's available
2. Examine schemas via `sql_db_schema` to understand columns, data types, and sample rows
3. Identify relationships by tracing foreign key connections
4. Note: Table names in Chinook are singular and capitalized (Customer, not customers); foreign keys end with "Id"

## Query Writing
For simple queries:
1. Identify the relevant table
2. Retrieve schema via `sql_db_schema`
3. Compose SELECT statement with appropriate clauses
4. Execute through `sql_db_query`
5. Present formatted results

For complex queries (multi-table):
1. Plan the approach - list required tables, map relationships, plan JOIN structure
2. Examine each table's schema
3. Construct query using SELECT, FROM/JOIN, WHERE, GROUP BY, ORDER BY, LIMIT
4. Use table aliases for readability

## Best Practices
- Select only necessary columns
- Apply LIMIT 5 by default
- Use table aliases for readability
- Always verify read-only constraints"""

    # Create Deep Agent with instructions in system prompt
    agent = create_deep_agent(
        model=model,
        system_prompt=agent_instructions,
        tools=sql_tools,
        subagents=[],
        backend=FilesystemBackend(root_dir=script_dir)
    )

    return agent


def run_agent(question: str, verbose: bool = True):
    """Run the agent with a question."""
    agent = create_sql_agent()

    if verbose:
        print(f"\n🤔 Question: {question}\n")

    try:
        result = agent.invoke({
            "messages": [{"role": "user", "content": question}]
        })

        # Extract final answer
        final_message = result["messages"][-1]
        answer = final_message.content if hasattr(final_message, 'content') else str(final_message)

        if verbose:
            print(f"✅ Answer: {answer}\n")
        return answer
    except Exception as e:
        if verbose:
            print(f"❌ Error: {e}\n")
        raise


def interactive_mode():
    """Run agent in interactive mode."""
    print("🎵 Chinook Database Assistant (Interactive Mode)")
    print("Ask questions about the music store database. Type 'exit' to quit.\n")

    while True:
        try:
            question = input("❓ Your question: ").strip()

            if not question:
                continue

            if question.lower() in ['exit', 'quit', 'q']:
                print("👋 Goodbye!")
                break

            run_agent(question, verbose=True)

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}\n")


def batch_test_questions():
    """Run a batch of test questions to generate traces."""
    test_questions = [
        "How many customers are from Canada?",
        "What are the top 5 most expensive tracks?",
        "List all albums by the artist 'AC/DC'",
        "What is the total revenue from invoices in 2009?",
        "Which employee has the most customers?",
        "What are the top 3 most popular genres by number of tracks?",
        "Find all customers who have spent more than $40",
        "List all tracks longer than 5 minutes",
        "What is the average track length by genre?",
        "Show all invoices from customers in the USA",
    ]

    print(f"🧪 Running {len(test_questions)} test questions to generate traces...\n")

    results = []
    for i, question in enumerate(test_questions, 1):
        print(f"[{i}/{len(test_questions)}] {question}")
        try:
            answer = run_agent(question, verbose=False)
            results.append({"question": question, "answer": answer, "success": True})
            print(f"✅ Success\n")
        except Exception as e:
            results.append({"question": question, "error": str(e), "success": False})
            print(f"❌ Error: {e}\n")

    # Summary
    successes = sum(1 for r in results if r["success"])
    print(f"\n📊 Summary: {successes}/{len(test_questions)} successful")

    return results


if __name__ == "__main__":
    # Check for required env vars
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not set")
        print("Please set it in your .env file")
        sys.exit(1)

    # Check if database exists
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "chinook.db")
    if not os.path.exists(db_path):
        print("❌ Error: chinook.db not found")
        print(f"Expected location: {db_path}")
        print("Download it with:")
        print(f"  curl -L https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite -o {db_path}")
        sys.exit(1)

    # Parse arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--interactive" or sys.argv[1] == "-i":
            interactive_mode()
        elif sys.argv[1] == "--batch" or sys.argv[1] == "-b":
            batch_test_questions()
        else:
            # Single question mode
            question = " ".join(sys.argv[1:])
            run_agent(question, verbose=True)
    else:
        print("Usage:")
        print("  python test_agent.py 'Your question here'")
        print("  python test_agent.py --interactive")
        print("  python test_agent.py --batch")
