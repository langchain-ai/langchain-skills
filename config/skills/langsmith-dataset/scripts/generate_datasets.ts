#!/usr/bin/env npx tsx
/**
 * Generate evaluation datasets from exported trace files.
 *
 * Workflow:
 *   1. Export traces using langsmith-trace skill: query_traces.ts export ./traces
 *   2. Generate datasets from those traces: generate_datasets.ts --input ./traces --type final_response
 *
 * Dataset types:
 *   - final_response: Full conversation with expected output
 *   - single_step: Single node inputs/outputs
 *   - trajectory: Tool/node call sequence
 *   - rag: Question/chunks/answer/citations
 */

import { Client } from "langsmith";
import { Command, Option } from "commander";
import chalk from "chalk";
import * as dotenv from "dotenv";
import * as fs from "fs";
import * as path from "path";
import * as readline from "readline";

dotenv.config();

// ============================================================================
// Types
// ============================================================================

export interface RunData {
  run_id?: string;
  id?: string;
  trace_id?: string;
  name?: string;
  run_type?: string;
  parent_run_id?: string | null;
  start_time?: string | Date | null;
  inputs?: Record<string, unknown> | null;
  outputs?: Record<string, unknown> | null;
}

export type TraceData = [string, RunData, RunData[]]; // [trace_id, root_run, all_runs]

// ============================================================================
// Trace Loading
// ============================================================================

function dictToObj(d: Record<string, unknown>): RunData {
  const obj: RunData = { ...d } as RunData;
  // Parse datetime strings
  if (typeof obj.start_time === "string") {
    try {
      obj.start_time = new Date(obj.start_time);
    } catch {
      obj.start_time = null;
    }
  }
  return obj;
}

export function loadTracesFromDir(
  inputDir: string,
  sort = "newest",
): TraceData[] {
  const traces: TraceData[] = [];
  const dirPath = path.resolve(inputDir);

  if (!fs.existsSync(dirPath)) {
    console.log(chalk.yellow(`No directory found at ${inputDir}`));
    return traces;
  }

  const files = fs.readdirSync(dirPath);
  const jsonlFiles = files.filter((f) => f.endsWith(".jsonl")).sort();
  const jsonFiles = files.filter((f) => f.endsWith(".json")).sort();

  if (jsonlFiles.length === 0 && jsonFiles.length === 0) {
    console.log(chalk.yellow(`No JSONL/JSON files found in ${inputDir}`));
    return traces;
  }

  // Process JSONL files (one run per line, group by trace_id)
  for (const fileName of jsonlFiles) {
    try {
      const filePath = path.join(dirPath, fileName);
      const content = fs.readFileSync(filePath, "utf-8");
      const runsByTrace: Map<string, RunData[]> = new Map();

      for (const line of content.split("\n")) {
        if (line.trim()) {
          const runData = JSON.parse(line) as Record<string, unknown>;
          const traceId =
            (runData.trace_id as string) || path.basename(fileName, ".jsonl");
          if (!runsByTrace.has(traceId)) {
            runsByTrace.set(traceId, []);
          }
          runsByTrace.get(traceId)!.push(dictToObj(runData));
        }
      }

      for (const [traceId, runs] of runsByTrace) {
        if (runs.length > 0) {
          const root = runs.find((r) => !r.parent_run_id) || runs[0];
          traces.push([traceId, root, runs]);
        }
      }
    } catch (e) {
      console.log(chalk.yellow(`Warning: Skipping ${fileName}: ${e}`));
    }
  }

  // Process legacy JSON files
  for (const fileName of jsonFiles) {
    try {
      const filePath = path.join(dirPath, fileName);
      const content = fs.readFileSync(filePath, "utf-8");
      const data = JSON.parse(content);

      const traceId = data.trace_id || path.basename(fileName, ".json");
      const runsData = data.runs || [];

      if (runsData.length === 0) continue;

      const runs = runsData.map((r: Record<string, unknown>) => dictToObj(r));
      const root = runs.find((r: RunData) => !r.parent_run_id) || runs[0];
      traces.push([traceId, root, runs]);
    } catch (e) {
      console.log(chalk.yellow(`Warning: Skipping ${fileName}: ${e}`));
    }
  }

  // Sort traces
  return sortTraces(traces, sort);
}

export function loadTracesFromFile(
  inputFile: string,
  sort = "newest",
): TraceData[] {
  const traces: TraceData[] = [];
  const filePath = path.resolve(inputFile);

  if (!fs.existsSync(filePath)) {
    console.log(chalk.yellow(`File not found: ${inputFile}`));
    return traces;
  }

  const content = fs.readFileSync(filePath, "utf-8");

  if (inputFile.endsWith(".jsonl")) {
    const runsByTrace: Map<string, RunData[]> = new Map();

    for (const line of content.split("\n")) {
      if (line.trim()) {
        const runData = JSON.parse(line) as Record<string, unknown>;
        const traceId = (runData.trace_id as string) || "unknown";
        if (!runsByTrace.has(traceId)) {
          runsByTrace.set(traceId, []);
        }
        runsByTrace.get(traceId)!.push(dictToObj(runData));
      }
    }

    for (const [traceId, runs] of runsByTrace) {
      if (runs.length > 0) {
        const root = runs.find((r) => !r.parent_run_id) || runs[0];
        traces.push([traceId, root, runs]);
      }
    }
  } else {
    // Legacy JSON format
    const data = JSON.parse(content);
    const items = Array.isArray(data) ? data : [data];

    for (const item of items) {
      const traceId = item.trace_id || "unknown";
      const runsData = item.runs || [];

      if (runsData.length === 0) continue;

      const runs = runsData.map((r: Record<string, unknown>) => dictToObj(r));
      const root = runs.find((r: RunData) => !r.parent_run_id) || runs[0];
      traces.push([traceId, root, runs]);
    }
  }

  return sortTraces(traces, sort);
}

function sortTraces(traces: TraceData[], sort: string): TraceData[] {
  if (sort === "newest") {
    return traces.sort((a, b) => {
      const aTime =
        a[1].start_time instanceof Date ? a[1].start_time.getTime() : 0;
      const bTime =
        b[1].start_time instanceof Date ? b[1].start_time.getTime() : 0;
      return bTime - aTime;
    });
  } else if (sort === "oldest") {
    return traces.sort((a, b) => {
      const aTime =
        a[1].start_time instanceof Date ? a[1].start_time.getTime() : 0;
      const bTime =
        b[1].start_time instanceof Date ? b[1].start_time.getTime() : 0;
      return aTime - bTime;
    });
  } else if (sort === "alphabetical") {
    return traces.sort((a, b) => a[0].localeCompare(b[0]));
  } else if (sort === "reverse-alphabetical") {
    return traces.sort((a, b) => b[0].localeCompare(a[0]));
  }
  return traces;
}

// ============================================================================
// Extraction Helpers
// ============================================================================

const COMMON_INPUT_FIELDS = [
  "query",
  "input",
  "question",
  "message",
  "prompt",
  "text",
];
const COMMON_OUTPUT_FIELDS = ["answer", "output", "response", "result"];

interface Message {
  type?: string;
  role?: string;
  content?: string;
}

function extractFromMessages(
  messages: unknown[],
  role?: string,
): string | null {
  if (!messages || !Array.isArray(messages)) return null;

  if (role === "human" || role === "user") {
    for (const msg of messages) {
      if (typeof msg === "object" && msg !== null) {
        const m = msg as Message;
        if (m.type === "human" || m.role === "user") {
          return m.content || "";
        }
      } else if (typeof msg === "string") {
        return msg;
      }
    }
  } else if (role === "ai" || role === "assistant") {
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i];
      if (typeof msg === "object" && msg !== null) {
        const m = msg as Message;
        if (m.type === "ai" || m.role === "assistant") {
          const content = m.content || "";
          if (content && content !== "None") {
            return content;
          }
        }
      }
    }
  } else {
    // Return last message content
    const last = messages[messages.length - 1];
    if (typeof last === "object" && last !== null) {
      return (last as Message).content || JSON.stringify(last);
    } else if (typeof last === "string") {
      return last;
    }
  }

  return null;
}

function extractValue(
  data: Record<string, unknown> | null,
  fields?: string[],
  commonFields?: string[],
  messageRole?: string,
  fallbackToRaw = true,
): unknown {
  if (!data) return null;

  // Priority 1: User-specified fields
  if (fields) {
    for (const field of fields) {
      if (data[field]) return data[field];
    }
  }

  // Priority 2: Messages array
  if (data.messages && Array.isArray(data.messages)) {
    const content = extractFromMessages(data.messages, messageRole);
    if (content) return content;
  }

  // Priority 3: Common fields
  if (commonFields) {
    for (const field of commonFields) {
      if (data[field]) return data[field];
    }
  }

  // Priority 4: Fallback to raw
  if (fallbackToRaw) {
    const values = Object.values(data);
    if (values.length === 1 && typeof values[0] === "string") {
      return values[0];
    }
    for (const val of values) {
      if (typeof val === "string" && val) {
        return val;
      }
    }
    return data;
  }

  return null;
}

function extractTraceInputs(
  root: RunData,
  inputFields?: string[],
  asDict = true,
): unknown {
  const inputs = root.inputs || {};

  if (Object.keys(inputs).length === 0) {
    return asDict ? {} : null;
  }

  if (inputFields) {
    return extractValue(
      inputs,
      inputFields,
      COMMON_INPUT_FIELDS,
      "human",
      true,
    );
  }

  if (asDict) {
    return inputs;
  }

  return extractValue(inputs, undefined, COMMON_INPUT_FIELDS, "human", true);
}

function extractTraceOutput(
  root: RunData,
  outputFields?: string[],
  messagesOnly = false,
): unknown {
  const outputs = root.outputs || {};

  if (Object.keys(outputs).length === 0) {
    return null;
  }

  const result = extractValue(
    outputs,
    outputFields,
    messagesOnly ? undefined : COMMON_OUTPUT_FIELDS,
    "ai",
    !messagesOnly,
  );

  if (typeof result === "object" && result !== null) {
    return JSON.stringify(result);
  }

  return result;
}

function extractFinalOutput(runs: RunData[], outputFields?: string[]): string {
  const sortedRuns = [...runs].sort((a, b) => {
    const aTime = a.start_time instanceof Date ? a.start_time.getTime() : 0;
    const bTime = b.start_time instanceof Date ? b.start_time.getTime() : 0;
    return bTime - aTime;
  });

  for (const run of sortedRuns) {
    const outputs = run.outputs;
    if (!outputs) continue;

    const result = extractValue(
      typeof outputs === "object" ? outputs : { output: outputs },
      outputFields,
      COMMON_OUTPUT_FIELDS,
      "ai",
      true,
    );

    if (result) {
      if (typeof result === "object") {
        return JSON.stringify(result);
      }
      return String(result);
    }
  }

  return "";
}

function extractToolSequence(runs: RunData[], depth?: number): string[] {
  const parentMap = new Map<string, string | null>();
  for (const r of runs) {
    const runId = r.run_id || r.id || "";
    parentMap.set(runId, r.parent_run_id || null);
  }

  function getDepth(runId: string): number {
    let d = 0;
    let current: string | null = runId;
    while (current && parentMap.get(current)) {
      d++;
      current = parentMap.get(current) || null;
    }
    return d;
  }

  const result: string[] = [];
  const sortedRuns = [...runs].sort((a, b) => {
    const aTime = a.start_time instanceof Date ? a.start_time.getTime() : 0;
    const bTime = b.start_time instanceof Date ? b.start_time.getTime() : 0;
    return aTime - bTime;
  });

  for (const r of sortedRuns) {
    const runType = r.run_type;
    const runId = r.run_id || r.id || "";
    if (
      runType === "tool" &&
      (depth === undefined || getDepth(runId) <= depth)
    ) {
      result.push((r.name || "unknown").toLowerCase());
    }
  }

  return result;
}

function getNodeIo(
  runs: RunData[],
  runName?: string,
): Array<{
  node_name: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  run_id: string;
}> {
  const target = runName ? runs.filter((r) => r.name === runName) : runs;
  const results: Array<{
    node_name: string;
    inputs: Record<string, unknown>;
    outputs: Record<string, unknown>;
    run_id: string;
  }> = [];

  const sortedTarget = [...target].sort((a, b) => {
    const aTime = a.start_time instanceof Date ? a.start_time.getTime() : 0;
    const bTime = b.start_time instanceof Date ? b.start_time.getTime() : 0;
    return aTime - bTime;
  });

  for (const run of sortedTarget) {
    const outputs = run.outputs;
    if (outputs) {
      results.push({
        node_name: run.name || "unknown",
        inputs: (run.inputs as Record<string, unknown>) || {},
        outputs: outputs as Record<string, unknown>,
        run_id: String(run.run_id || run.id || ""),
      });
    }
  }

  return results;
}

function extractDocuments(outputs: unknown): string[] {
  if (!outputs) return [];

  let docs: unknown[];

  if (
    typeof outputs === "object" &&
    outputs !== null &&
    !Array.isArray(outputs)
  ) {
    const o = outputs as Record<string, unknown>;
    const docsData = o.documents || o.output || outputs;
    docs = Array.isArray(docsData) ? docsData : [docsData];
  } else {
    docs = Array.isArray(outputs) ? outputs : [outputs];
  }

  const results: string[] = [];
  for (const doc of docs) {
    if (typeof doc === "object" && doc !== null) {
      const d = doc as Record<string, unknown>;
      if (d.page_content) {
        results.push(String(d.page_content));
      } else if (d.content || d.text) {
        results.push(String(d.content || d.text));
      } else {
        results.push(JSON.stringify(doc));
      }
    } else if (typeof doc === "string") {
      results.push(doc);
    } else {
      results.push(String(doc));
    }
  }

  return results;
}

function findRetrievalData(runs: RunData[]): {
  query: string;
  retrieved_chunks: string[];
  answer: string;
} {
  const data = { query: "", retrieved_chunks: [] as string[], answer: "" };

  const retRuns = runs.filter((r) => r.run_type === "retriever");

  const sortedRetRuns = [...retRuns].sort((a, b) => {
    const aTime = a.start_time instanceof Date ? a.start_time.getTime() : 0;
    const bTime = b.start_time instanceof Date ? b.start_time.getTime() : 0;
    return aTime - bTime;
  });

  for (const run of sortedRetRuns) {
    const inputs = run.inputs;
    if (inputs && typeof inputs === "object" && !data.query) {
      const query = extractValue(
        inputs,
        undefined,
        COMMON_INPUT_FIELDS,
        "human",
        false,
      );
      data.query = query ? String(query) : "";
    }

    const outputs = run.outputs;
    if (outputs) {
      data.retrieved_chunks.push(...extractDocuments(outputs));
    }
  }

  data.answer = extractFinalOutput(runs);
  return data;
}

// ============================================================================
// Dataset Generation
// ============================================================================

interface DatasetExample {
  trace_id: string;
  inputs?: Record<string, unknown>;
  outputs?: Record<string, unknown>;
  run_id?: string;
  node_name?: string;
  occurrence?: number;
  question?: string;
  retrieved_chunks?: string;
  answer?: string;
  cited_chunks?: string;
  [key: string]: unknown; // Index signature for dynamic access
}

function generateDataset(
  traces: TraceData[],
  datasetType: string,
  options: {
    runName?: string;
    depth?: number;
    inputFields?: string[];
    outputFields?: string[];
    messagesOnly?: boolean;
    samplePerTrace?: number;
  },
): DatasetExample[] {
  const dataset: DatasetExample[] = [];

  for (const [traceId, root, runs] of traces) {
    if (datasetType === "rag") {
      const ragData = findRetrievalData(runs);
      if (!(ragData.query && ragData.answer)) continue;
      dataset.push({
        trace_id: traceId,
        question: ragData.query,
        retrieved_chunks: ragData.retrieved_chunks.join("\n\n"),
        answer: ragData.answer,
        cited_chunks: JSON.stringify(ragData.retrieved_chunks.slice(0, 3)),
      });
    } else {
      const rootInputs = extractTraceInputs(
        root,
        options.inputFields,
        !options.inputFields,
      );

      if (
        !rootInputs ||
        (typeof rootInputs === "object" &&
          Object.keys(rootInputs as object).length === 0)
      ) {
        continue;
      }

      let inputs: Record<string, unknown>;
      if (options.inputFields && typeof rootInputs !== "object") {
        inputs = { expected_input: rootInputs };
      } else {
        inputs = rootInputs as Record<string, unknown>;
      }

      if (datasetType === "final_response") {
        const output = extractTraceOutput(
          root,
          options.outputFields,
          options.messagesOnly,
        );
        if (!output) continue;
        const outputs = { expected_response: output };
        dataset.push({ trace_id: traceId, inputs, outputs });
      } else if (datasetType === "single_step") {
        const nodeIoList = getNodeIo(runs, options.runName);
        if (nodeIoList.length === 0) continue;

        let sampled = nodeIoList;
        if (
          options.samplePerTrace &&
          nodeIoList.length > options.samplePerTrace
        ) {
          // Random sample
          const shuffled = [...nodeIoList].sort(() => Math.random() - 0.5);
          sampled = shuffled.slice(0, options.samplePerTrace);
        }

        for (let idx = 0; idx < sampled.length; idx++) {
          const nodeIo = sampled[idx];
          dataset.push({
            trace_id: traceId,
            run_id: nodeIo.run_id,
            node_name: nodeIo.node_name,
            occurrence: idx + 1,
            inputs: nodeIo.inputs,
            outputs: { expected_output: nodeIo.outputs },
          });
        }
      } else if (datasetType === "trajectory") {
        const tools = extractToolSequence(runs, options.depth);
        if (tools.length === 0) continue;
        const outputs = { expected_trajectory: tools };
        dataset.push({ trace_id: traceId, inputs, outputs });
      }
    }
  }

  return dataset;
}

// ============================================================================
// Export Functions
// ============================================================================

function getClient(): Client {
  const apiKey = process.env.LANGSMITH_API_KEY;
  if (!apiKey) {
    console.error(chalk.red("Error: LANGSMITH_API_KEY not set"));
    process.exit(1);
  }
  return new Client({ apiKey });
}

function exportToFile(dataset: DatasetExample[], outputPath: string): void {
  if (dataset.length === 0) {
    console.log(chalk.yellow("No data to export"));
    return;
  }

  if (outputPath.endsWith(".csv")) {
    // CSV export
    const allKeys = new Set<string>();
    for (const ex of dataset) {
      for (const key of Object.keys(ex)) {
        allKeys.add(key);
      }
    }
    const fieldnames = Array.from(allKeys).sort();

    const lines = [fieldnames.join(",")];
    for (const ex of dataset) {
      const row = fieldnames.map((f) => {
        const val = (ex as Record<string, unknown>)[f];
        if (val === undefined || val === null) return "";
        const str = typeof val === "object" ? JSON.stringify(val) : String(val);
        return str.includes(",") || str.includes('"') || str.includes("\n")
          ? `"${str.replace(/"/g, '""')}"`
          : str;
      });
      lines.push(row.join(","));
    }
    fs.writeFileSync(outputPath, lines.join("\n"));
  } else {
    // JSON export
    fs.writeFileSync(outputPath, JSON.stringify(dataset, null, 2));
  }

  console.log(
    chalk.green("✓") + ` Exported ${dataset.length} examples to ${outputPath}`,
  );
}

async function exportToLangsmith(
  client: Client,
  dataset: DatasetExample[],
  datasetName: string,
  datasetType: string,
): Promise<void> {
  let ds;
  try {
    ds = await client.createDataset(datasetName, {
      description: `${datasetType} evaluation dataset (auto-generated)`,
    });
    console.log(chalk.green("✓") + ` Created dataset: ${datasetName}`);
  } catch {
    ds = await client.readDataset({ datasetName });
    console.log(chalk.yellow(`Using existing: ${datasetName}`));
  }

  let inputs: Record<string, unknown>[];
  let outputs: Record<string, unknown>[];

  if (datasetType === "rag") {
    inputs = dataset.map((ex) => ({
      question: ex.question,
      retrieved_chunks: ex.retrieved_chunks,
    }));
    outputs = dataset.map((ex) => ({
      answer: ex.answer,
      cited_chunks: ex.cited_chunks,
    }));
  } else {
    inputs = dataset.map((ex) => ex.inputs || {});
    outputs = dataset.map((ex) => ex.outputs || {});
  }

  await client.createExamples({ inputs, outputs, datasetId: ds.id });
  console.log(chalk.green("✓") + ` Added ${dataset.length} examples`);
}

async function promptConfirm(message: string): Promise<boolean> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  return new Promise((resolve) => {
    rl.question(`${message} (y/n): `, (answer) => {
      rl.close();
      resolve(answer.toLowerCase().trim() === "y");
    });
  });
}

// ============================================================================
// CLI
// ============================================================================

const program = new Command();

program
  .name("generate_datasets")
  .description(
    `Generate evaluation datasets from exported JSONL trace files.

Workflow:
  1. Export traces: query_traces.ts export ./traces --project myproject --include-io
  2. Generate dataset: generate_datasets.ts --input ./traces --type final_response -o dataset.json

Dataset types:
  final_response - Full conversation with expected output
  single_step    - Single node inputs/outputs (use --run-name)
  trajectory     - Tool call sequence (use --depth)
  rag            - Question/chunks/answer/citations`,
  )
  .version("1.0.0")
  .requiredOption(
    "-i, --input <path>",
    "Input traces: directory of JSONL files or single JSONL file",
  )
  .addOption(
    new Option("-t, --type <type>", "Dataset type to generate")
      .choices(["final_response", "single_step", "trajectory", "rag"])
      .makeOptionMandatory(),
  )
  .requiredOption("-o, --output <path>", "Output file (JSON or CSV)")
  .option("--upload <name>", "Upload to LangSmith dataset with this name")
  .option("--run-name <name>", "For single_step: target specific node name")
  .option("--depth <n>", "For trajectory: max hierarchy depth", parseInt)
  .option(
    "--input-fields <fields>",
    "Comma-separated input keys to extract (e.g., 'query,question')",
  )
  .option(
    "--output-fields <fields>",
    "Comma-separated output keys to extract (e.g., 'answer,response')",
  )
  .option("--messages-only", "For final_response: only extract from messages")
  .option(
    "--sample-per-trace <n>",
    "For single_step: max examples per trace",
    parseInt,
  )
  .addOption(
    new Option("--sort <order>", "Sort order for traces")
      .choices(["newest", "oldest", "alphabetical", "reverse-alphabetical"])
      .default("newest"),
  )
  .option("--replace", "Replace existing file/dataset")
  .option("--yes", "Skip confirmation prompts")
  .action(async (opts) => {
    const inputPath = path.resolve(opts.input);
    const outputPath = path.resolve(opts.output);

    // Check output exists
    if (fs.existsSync(outputPath) && !opts.replace) {
      console.log(
        chalk.yellow(`File ${outputPath} exists. Use --replace to overwrite.`),
      );
      return;
    }

    // Load traces
    let traces: TraceData[];
    const stats = fs.statSync(inputPath);
    if (stats.isDirectory()) {
      traces = loadTracesFromDir(inputPath, opts.sort);
    } else if (stats.isFile()) {
      traces = loadTracesFromFile(inputPath, opts.sort);
    } else {
      console.log(chalk.red(`Error: ${inputPath} not found`));
      return;
    }

    if (traces.length === 0) {
      console.log(chalk.yellow("No valid traces found"));
      return;
    }

    console.log(
      chalk.green("✓") +
        ` Loaded ${traces.length} traces from ${inputPath} (sorted: ${opts.sort})`,
    );

    // Generate dataset
    const inputFieldsList = opts.inputFields?.split(",");
    const outputFieldsList = opts.outputFields?.split(",");
    const dataset = generateDataset(traces, opts.type, {
      runName: opts.runName,
      depth: opts.depth,
      inputFields: inputFieldsList,
      outputFields: outputFieldsList,
      messagesOnly: opts.messagesOnly,
      samplePerTrace: opts.samplePerTrace,
    });

    if (dataset.length === 0) {
      console.log(chalk.yellow("No valid examples found in traces"));
      return;
    }

    // Export
    exportToFile(dataset, outputPath);

    // Upload to LangSmith if requested
    if (opts.upload) {
      const client = getClient();
      if (opts.replace) {
        try {
          const existing = await client.readDataset({
            datasetName: opts.upload,
          });
          if (!opts.yes) {
            console.log(
              chalk.yellow(`About to delete dataset: '${opts.upload}'`),
            );
            const confirmed = await promptConfirm("Are you sure?");
            if (!confirmed) {
              console.log(chalk.yellow("Upload cancelled"));
              return;
            }
          }
          await client.deleteDataset({ datasetId: existing.id });
          console.log(chalk.yellow(`Deleted existing dataset: ${opts.upload}`));
        } catch {
          // Dataset doesn't exist, that's fine
        }
      }
      await exportToLangsmith(client, dataset, opts.upload, opts.type);
    }
  });

// Only run CLI when executed directly (not when imported)
const isMainModule =
  process.argv[1] &&
  (process.argv[1].endsWith("generate_datasets.ts") ||
    process.argv[1].endsWith("generate_datasets.js"));

if (isMainModule) {
  program.parse();
}
