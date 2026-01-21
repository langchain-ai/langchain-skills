# LangSmith Skills Tests

Integration tests to verify Claude Code can correctly use LangSmith skills.

## Test Agent (Generate Traces)

SQL agent that generates traces in LangSmith for testing dataset generation.

### Usage

```bash
# Single question
python tests/test_agent.py "How many customers are from Canada?"

# Interactive mode
python tests/test_agent.py --interactive

# Batch mode - generates 10 test traces
python tests/test_agent.py --batch
```

### Questions in Batch Mode

- How many customers are from Canada?
- What are the top 5 most expensive tracks?
- List all albums by the artist 'AC/DC'
- What is the total revenue from invoices in 2009?
- Which employee has the most customers?
- What are the top 3 most popular genres by number of tracks?
- Find all customers who have spent more than $40
- List all tracks longer than 5 minutes
- What is the average track length by genre?
- Show all invoices from customers in the USA

## Skill Tests

Each test validates that Claude Code can use a specific LangSmith skill.

### 1. Trace Query Test (`test_trace_query.py`)

**Task:** List 5 recent traces, get details about the first one, store trace ID in `/tmp/test_trace_id.txt`

**Validates:** Trace ID is valid UUID, trace exists in LangSmith, trace is recent

```bash
python tests/test_trace_query.py
```

### 2. Dataset Generation Test (`test_dataset_generation.py`)

**Task:** Generate small test dataset (5 examples, final_response type), save to `/tmp/test_dataset.json` (file only, no upload)

**Validates:** Valid JSON structure, correct format (inputs/outputs/expected_response), has examples

```bash
python tests/test_dataset_generation.py
```

### 3. Dataset Upload Test (`test_dataset_upload.py`)

**Task:** Generate and upload dataset (3 examples, trajectory type) to LangSmith as "Test Dataset - DELETE ME"

**Validates:** Dataset exists in LangSmith, has examples, correct trajectory structure

```bash
python tests/test_dataset_upload.py
```

### 4. Evaluator Upload Test (`test_evaluator_upload.py`)

**Task:** Create evaluator function (length check), upload to LangSmith as "Test Length Check - DELETE ME"

**Validates:** Correct function signature (run, example), evaluator exists in LangSmith

```bash
python tests/test_evaluator_upload.py
```

## Running Tests with Claude Code

### Option 1: Direct task
```
Read test_trace_query.py, complete the task in the docstring, then run validation.
```

### Option 2: All tests
```
Run all three LangSmith skill tests. For each, read the task, complete it, then validate.
```

## Expected Output

```
============================================================
LangSmith Trace Query Test - Validation
============================================================
✓ Trace ID file exists
✓ Trace ID is valid UUID format
✓ Trace exists in LangSmith
✓ Trace is recent (2 days old)

============================================================
✅ ALL TESTS PASSED
============================================================
```

## Cleanup

```bash
# Trace test - no cleanup needed (read-only)

# Dataset generation test (file only)
rm /tmp/test_dataset.json /tmp/test_dataset_info.txt

# Dataset upload test (LangSmith)
# Delete dataset from LangSmith (requires langsmith SDK)
python -c "from langsmith import Client; Client().delete_dataset(dataset_name='Test Dataset - DELETE ME')"
rm /tmp/test_dataset_upload_name.txt

# Evaluator test (includes temp dataset)
python config/skills/langsmith-evaluator/scripts/upload_evaluators.py delete "Test Length Check - DELETE ME"
python -c "from langsmith import Client; Client().delete_dataset(dataset_name='Evaluator Test Dataset - DELETE ME')"
rm /tmp/test_evaluator.py /tmp/test_evaluator_name.txt /tmp/test_evaluator_dataset_name.txt
```

## Workflow: Generate → Validate

1. **Generate traces:**
   ```bash
   python tests/test_agent.py --batch
   ```

2. **Generate datasets:**
   ```bash
   python config/skills/langsmith-dataset/scripts/generate_datasets.py \
     --type trajectory --project skills --limit 10 \
     --output /tmp/trajectory_ds.json
   ```

3. **View datasets:**
   ```bash
   python config/skills/langsmith-dataset/scripts/query_datasets.py \
     view-file /tmp/trajectory_ds.json --limit 3
   ```
