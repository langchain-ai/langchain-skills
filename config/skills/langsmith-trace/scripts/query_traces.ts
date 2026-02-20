#!/usr/bin/env npx tsx
/**
 * LangSmith Trace Query Tool - Query and export traces and runs.
 *
 * Two command groups with consistent behavior:
 *
 *   traces  - Operations on trace trees (root run + all children)
 *             Filters apply to the ROOT RUN, then full hierarchy is fetched.
 *             Always returns complete trace trees.
 *
 *   runs    - Operations on individual runs (flat list)
 *             Filters apply to ANY MATCHING RUN.
 *             Returns flat list of runs without hierarchy.
 *
 * Examples:
 *   # TRACES - always includes hierarchy
 *   query_traces.ts traces list --limit 5 --min-latency 2.0
 *   query_traces.ts traces get <trace-id>
 *   query_traces.ts traces export ./output --limit 10
 *
 *   # RUNS - flat list of individual runs
 *   query_traces.ts runs list --run-type llm --limit 20
 *   query_traces.ts runs get <run-id>
 *   query_traces.ts runs export ./output --run-type tool
 */

import { Client, Run } from "langsmith";
import { Command, Option } from "commander";
import chalk from "chalk";
import Table from "cli-table3";
import ora from "ora";
import * as dotenv from "dotenv";
import * as fs from "fs";
import * as path from "path";

dotenv.config();

// ============================================================================
// Helpers
// ============================================================================

export function getClient(): Client {
  const apiKey = process.env.LANGSMITH_API_KEY;
  if (!apiKey) {
    console.error(chalk.red("Error: LANGSMITH_API_KEY not set"));
    process.exit(1);
  }
  return new Client({ apiKey });
}

/**
 * Create a spinner that only shows for non-JSON output formats.
 * This prevents spinner text from polluting JSON output.
 */
function createSpinner(
  text: string,
  format?: string,
): { start: () => void; stop: () => void; text: string } {
  if (format === "json" || format === "jsonl") {
    // Return a no-op spinner for JSON output
    return {
      start: () => {},
      stop: () => {},
      text: "",
    };
  }
  const spinner = ora(text);
  return {
    start: () => spinner.start(),
    stop: () => spinner.stop(),
    get text() {
      return spinner.text;
    },
    set text(value: string) {
      spinner.text = value;
    },
  };
}

export interface QueryParams {
  projectName?: string;
  traceId?: string;
  limit?: number;
  startTime?: Date;
  runType?: string;
  isRoot?: boolean;
  error?: boolean;
  filter?: string;
}

export function buildQueryParams(options: {
  project?: string;
  traceIds?: string;
  limit?: number;
  lastNMinutes?: number;
  since?: string;
  runType?: string;
  isRoot: boolean;
  error?: boolean;
  name?: string;
  rawFilter?: string;
  minLatency?: number;
  maxLatency?: number;
  minTokens?: number;
  tags?: string;
}): QueryParams {
  const params: QueryParams = {};
  const filterParts: string[] = [];

  // Project (always include if available)
  if (options.project || process.env.LANGSMITH_PROJECT) {
    params.projectName = options.project || process.env.LANGSMITH_PROJECT;
  }

  // Trace IDs - filter to specific traces
  if (options.traceIds) {
    const ids = options.traceIds.split(",").map((t) => t.trim());
    if (ids.length === 1) {
      params.traceId = ids[0];
    } else {
      // Multiple trace IDs - use filter query
      const idsStr = ids.map((id) => `"${id}"`).join(", ");
      filterParts.push(`in(trace_id, [${idsStr}])`);
    }
  }

  // Limit
  if (options.limit) {
    params.limit = options.limit;
  }

  // Time filters
  if (options.lastNMinutes) {
    params.startTime = new Date(Date.now() - options.lastNMinutes * 60 * 1000);
  } else if (options.since) {
    params.startTime = new Date(options.since);
  }

  // Run type
  if (options.runType) {
    params.runType = options.runType;
  }

  // Is root
  if (options.isRoot) {
    params.isRoot = true;
  }

  // Error status
  if (options.error !== undefined) {
    params.error = options.error;
  }

  // Name pattern
  if (options.name) {
    filterParts.push(`search(name, "${options.name}")`);
  }

  // Latency filters (in seconds)
  if (options.minLatency !== undefined) {
    filterParts.push(`gte(latency, ${options.minLatency})`);
  }
  if (options.maxLatency !== undefined) {
    filterParts.push(`lte(latency, ${options.maxLatency})`);
  }

  // Token filter
  if (options.minTokens !== undefined) {
    filterParts.push(`gte(total_tokens, ${options.minTokens})`);
  }

  // Tags filter (comma-separated, any match)
  if (options.tags) {
    const tagList = options.tags.split(",").map((t) => t.trim());
    if (tagList.length === 1) {
      filterParts.push(`has(tags, "${tagList[0]}")`);
    } else {
      // Multiple tags - OR them together
      const tagFilters = tagList.map((t) => `has(tags, "${t}")`);
      filterParts.push(`or(${tagFilters.join(", ")})`);
    }
  }

  // Raw filter query (advanced)
  if (options.rawFilter) {
    filterParts.push(options.rawFilter);
  }

  // Combine all filter parts with AND
  if (filterParts.length > 0) {
    if (filterParts.length === 1) {
      params.filter = filterParts[0];
    } else {
      params.filter = `and(${filterParts.join(", ")})`;
    }
  }

  return params;
}

function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "N/A";
  return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(2)}s`;
}

function getTraceId(run: Run): string {
  return run.trace_id?.toString() || run.id.toString();
}

function calcDuration(run: Run): number | null {
  if (run.start_time && run.end_time) {
    const start = new Date(run.start_time).getTime();
    const end = new Date(run.end_time).getTime();
    return end - start;
  }
  return null;
}

export interface ExtractedRun {
  run_id: string;
  trace_id: string;
  name: string;
  run_type: string;
  parent_run_id: string | null;
  start_time: string | null;
  end_time: string | null;
  status?: string | null;
  duration_ms?: number | null;
  custom_metadata?: Record<string, unknown>;
  token_usage?: {
    prompt_tokens: number | null;
    completion_tokens: number | null;
    total_tokens: number | null;
  };
  costs?: {
    prompt_cost: number | null;
    completion_cost: number | null;
    total_cost: number | null;
  };
  inputs?: Record<string, unknown> | null;
  outputs?: Record<string, unknown> | null;
  error?: string | null;
}

export function extractRun(
  run: Run,
  includeMetadata = false,
  includeIo = false,
): ExtractedRun {
  const data: ExtractedRun = {
    run_id: run.id.toString(),
    trace_id: getTraceId(run),
    name: run.name,
    run_type: run.run_type,
    parent_run_id: run.parent_run_id?.toString() || null,
    start_time: run.start_time ? new Date(run.start_time).toISOString() : null,
    end_time: run.end_time ? new Date(run.end_time).toISOString() : null,
  };

  if (includeMetadata) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const runAny = run as any;
    data.status = run.status || null;
    data.duration_ms = calcDuration(run);
    data.custom_metadata =
      ((run.extra as Record<string, unknown>)?.metadata as Record<
        string,
        unknown
      >) || {};
    data.token_usage = {
      prompt_tokens: runAny.prompt_tokens ?? null,
      completion_tokens: runAny.completion_tokens ?? null,
      total_tokens: runAny.total_tokens ?? null,
    };
    data.costs = {
      prompt_cost: runAny.prompt_cost ?? null,
      completion_cost: runAny.completion_cost ?? null,
      total_cost: runAny.total_cost ?? null,
    };
  }

  if (includeIo) {
    data.inputs = run.inputs || null;
    data.outputs = run.outputs || null;
    data.error = run.error || null;
  }

  return data;
}

function outputJson(data: unknown, filePath?: string): void {
  const jsonStr = JSON.stringify(data, null, 2);
  if (filePath) {
    fs.writeFileSync(filePath, jsonStr);
    console.log(chalk.green("✓") + ` Saved to ${filePath}`);
  } else {
    console.log(jsonStr);
  }
}

function printTree(
  runs: Run[],
  parentId: string | null = null,
  indent = 0,
  visited = new Set<string>(),
): void {
  const children = runs
    .filter((r) => {
      const pId = r.parent_run_id?.toString() || null;
      return pId === parentId;
    })
    .sort((a, b) => {
      const aTime = a.start_time ? new Date(a.start_time).getTime() : 0;
      const bTime = b.start_time ? new Date(b.start_time).getTime() : 0;
      return aTime - bTime;
    });

  for (const run of children) {
    const runId = run.id.toString();
    if (visited.has(runId)) continue;
    visited.add(runId);

    const prefix = "  ".repeat(indent);
    const duration = calcDuration(run);
    const durationStr = duration !== null ? ` (${Math.round(duration)}ms)` : "";

    console.log(
      `${prefix}└── ${chalk.cyan(run.name)} (${run.run_type})${durationStr}`,
    );
    console.log(`${prefix}    run_id: ${chalk.dim(run.id)}`);
    if (run.parent_run_id) {
      console.log(`${prefix}    parent: ${chalk.dim(run.parent_run_id)}`);
    }

    printTree(runs, runId, indent + 1, visited);
  }
}

function printRunsTable(
  runs: Run[],
  includeMetadata = false,
  showTraceId = true,
): void {
  const headers = ["Time", "Name", "Type"];
  if (showTraceId) headers.push("Trace ID");
  headers.push("Run ID");
  if (includeMetadata) {
    headers.push("Duration", "Status");
  }

  const table = new Table({
    head: headers.map((h) => chalk.bold(h)),
    style: { head: [], border: [] },
  });

  const sortedRuns = [...runs].sort((a, b) => {
    const aTime = a.start_time ? new Date(a.start_time).getTime() : 0;
    const bTime = b.start_time ? new Date(b.start_time).getTime() : 0;
    return bTime - aTime; // Most recent first
  });

  for (const run of sortedRuns) {
    const row: string[] = [
      run.start_time
        ? new Date(run.start_time).toLocaleTimeString("en-US", {
            hour12: false,
          })
        : "N/A",
      (run.name || "N/A").substring(0, 40),
      run.run_type || "N/A",
    ];
    if (showTraceId) {
      row.push(getTraceId(run).substring(0, 16) + "...");
    }
    row.push(run.id.toString().substring(0, 16) + "...");
    if (includeMetadata) {
      row.push(formatDuration(calcDuration(run)));
      row.push(run.status || "N/A");
    }
    table.push(row);
  }

  console.log(table.toString());
}

// ============================================================================
// Shared filter options
// ============================================================================

function addCommonFilterOptions(cmd: Command, includeRunType = true): Command {
  cmd
    .option("--trace-ids <ids>", "Comma-separated trace IDs to filter")
    .option("-n, --limit <n>", "Max results to return", parseInt)
    .option(
      "--project <name>",
      "Project name (overrides LANGSMITH_PROJECT env)",
    )
    .option("--last-n-minutes <n>", "Only from last N minutes", parseInt)
    .option("--since <timestamp>", "Only since ISO timestamp");

  if (includeRunType) {
    cmd.addOption(
      new Option("--run-type <type>", "Filter by run type").choices([
        "llm",
        "chain",
        "tool",
        "retriever",
        "prompt",
        "parser",
      ]),
    );
  }

  cmd
    .option("--error", "Only runs with errors")
    .option("--no-error", "Only runs without errors")
    .option("--name <pattern>", "Filter by name pattern (case-insensitive)")
    .option(
      "--min-latency <seconds>",
      "Min latency in seconds (e.g., 5 for >= 5s)",
      parseFloat,
    )
    .option(
      "--max-latency <seconds>",
      "Max latency in seconds (e.g., 10 for <= 10s)",
      parseFloat,
    )
    .option(
      "--min-tokens <n>",
      "Min total tokens (e.g., 1000 for >= 1000)",
      parseInt,
    )
    .option("--tags <tags>", "Filter by tags (comma-separated, matches any)")
    .option(
      "--filter <query>",
      "Raw LangSmith filter query (for feedback, metadata, etc.)",
    );

  return cmd;
}

// ============================================================================
// Main CLI
// ============================================================================

const program = new Command();

program
  .name("query_traces")
  .description(
    `LangSmith Trace Query Tool

Two command groups with consistent behavior:

TRACES - Operations on trace trees (root + all child runs)
  traces list    List traces with hierarchy
  traces get     Get single trace by ID
  traces export  Export traces to JSONL files

RUNS - Operations on individual runs (flat)
  runs list      List runs (flat)
  runs get       Get single run by ID
  runs export    Export runs to JSONL files

Key difference:
  - traces: Filters apply to ROOT RUN, returns full hierarchy
  - runs: Filters apply to ANY RUN, returns flat list`,
  )
  .version("1.0.0");

// ============================================================================
// TRACES Commands
// ============================================================================

const traces = program
  .command("traces")
  .description(
    "Operations on trace trees (root run + all children). Filters apply to ROOT RUN.",
  );

// traces list
const tracesListCmd = traces
  .command("list")
  .description("List traces matching filters")
  .addOption(
    new Option("--format <format>", "Output format")
      .choices(["json", "pretty"])
      .default("pretty"),
  )
  .option("--include-metadata", "Include timing/tokens/costs")
  .option("--show-hierarchy", "Expand each trace to show run tree")
  .action(async (opts) => {
    const client = getClient();

    const params = buildQueryParams({
      project: opts.project,
      traceIds: opts.traceIds,
      limit: opts.limit || 20,
      lastNMinutes: opts.lastNMinutes,
      since: opts.since,
      runType: undefined, // Not applicable for traces
      isRoot: true, // Always filter root runs for traces
      error:
        opts.error === false ? false : opts.error === true ? true : undefined,
      name: opts.name,
      rawFilter: opts.filter,
      minLatency: opts.minLatency,
      maxLatency: opts.maxLatency,
      minTokens: opts.minTokens,
      tags: opts.tags,
    });

    const spinner = createSpinner("Fetching traces...", opts.format);
    spinner.start();
    const rootRuns: Run[] = [];

    try {
      for await (const run of client.listRuns(params)) {
        rootRuns.push(run);
      }
    } finally {
      spinner.stop();
    }

    if (rootRuns.length === 0) {
      console.log(chalk.yellow("No traces found"));
      return;
    }

    rootRuns.sort((a, b) => {
      const aTime = a.start_time ? new Date(a.start_time).getTime() : 0;
      const bTime = b.start_time ? new Date(b.start_time).getTime() : 0;
      return bTime - aTime;
    });

    if (opts.showHierarchy) {
      console.log(
        chalk.green("✓") +
          ` Found ${rootRuns.length} trace(s). Fetching hierarchy...\n`,
      );

      for (const root of rootRuns) {
        const tid = getTraceId(root);
        const fetchParams: QueryParams = { traceId: tid };
        if (opts.project || process.env.LANGSMITH_PROJECT) {
          fetchParams.projectName =
            opts.project || process.env.LANGSMITH_PROJECT;
        }

        const allRuns: Run[] = [];
        for await (const run of client.listRuns(fetchParams)) {
          allRuns.push(run);
        }

        console.log(chalk.bold("TRACE:") + ` ${tid}`);
        console.log(
          `  Root: ${chalk.cyan(root.name)} (${allRuns.length} runs)`,
        );
        if (opts.includeMetadata) {
          console.log(`  Duration: ${formatDuration(calcDuration(root))}`);
        }
        printTree(allRuns, root.id.toString(), 1);
        console.log();
      }
    } else if (opts.format === "json") {
      const data = rootRuns.map((r) =>
        extractRun(r, opts.includeMetadata, false),
      );
      outputJson(data);
    } else {
      console.log(chalk.green("✓") + ` Found ${rootRuns.length} trace(s)\n`);
      printRunsTable(rootRuns, opts.includeMetadata, true);
      console.log(
        chalk.dim("\nTip: Use --show-hierarchy to expand each trace"),
      );
    }
  });

addCommonFilterOptions(tracesListCmd, false);

// traces get
traces
  .command("get <traceId>")
  .description("Get a specific trace by ID with full hierarchy")
  .option("--project <name>", "Project name")
  .addOption(
    new Option(
      "--format <format>",
      "Output format (jsonl for dataset-compatible)",
    )
      .choices(["json", "jsonl", "pretty"])
      .default("pretty"),
  )
  .option("-o, --output <path>", "Output file")
  .option("--include-metadata", "Include timing/tokens/costs")
  .option("--include-io", "Include inputs/outputs")
  .option("--full", "Include everything (metadata + inputs/outputs)")
  .action(async (traceId, opts) => {
    const client = getClient();

    const includeMetadata = opts.full || opts.includeMetadata;
    const includeIo = opts.full || opts.includeIo;

    const params: QueryParams = { traceId };
    if (opts.project || process.env.LANGSMITH_PROJECT) {
      params.projectName = opts.project || process.env.LANGSMITH_PROJECT;
    }

    const spinner = createSpinner("Fetching trace...", opts.format);
    spinner.start();
    const runs: Run[] = [];

    try {
      for await (const run of client.listRuns(params)) {
        runs.push(run);
      }
    } finally {
      spinner.stop();
    }

    if (runs.length === 0) {
      console.log(chalk.red(`No runs found for trace ${traceId}`));
      return;
    }

    const rootRuns = runs.filter((r) => r.parent_run_id === null);

    if (opts.format === "pretty") {
      console.log(chalk.green("✓") + ` Found ${runs.length} run(s) in trace\n`);
      for (const root of rootRuns) {
        console.log(chalk.bold("ROOT:") + ` ${root.name} (run_id: ${root.id})`);
        printTree(runs, root.id.toString(), 1);
        console.log();
      }
    } else if (opts.format === "jsonl") {
      const lines = runs.map((r) =>
        JSON.stringify(extractRun(r, includeMetadata, includeIo)),
      );
      const content = lines.join("\n");
      if (opts.output) {
        fs.writeFileSync(opts.output, content + "\n");
        console.log(
          chalk.green("✓") + ` Saved ${runs.length} runs to ${opts.output}`,
        );
      } else {
        console.log(content);
      }
    } else {
      const data = {
        trace_id: traceId,
        run_count: runs.length,
        runs: runs.map((r) => extractRun(r, includeMetadata, includeIo)),
      };
      outputJson(data, opts.output);
    }
  });

// traces export
const tracesExportCmd = traces
  .command("export <outputDir>")
  .description("Export traces to JSONL files (one file per trace)")
  .option("--include-metadata", "Include timing/tokens/costs")
  .option("--include-io", "Include inputs/outputs")
  .option("--full", "Include everything (metadata + inputs/outputs)")
  .option(
    "--filename-pattern <pattern>",
    "Filename pattern",
    "{trace_id}.jsonl",
  )
  .action(async (outputDir, opts) => {
    const includeMetadata = opts.full || opts.includeMetadata;
    const includeIo = opts.full || opts.includeIo;

    const client = getClient();
    const outputPath = path.resolve(outputDir);
    fs.mkdirSync(outputPath, { recursive: true });

    let traceIdList: string[];

    if (opts.traceIds) {
      traceIdList = opts.traceIds.split(",").map((t: string) => t.trim());
      console.log(
        chalk.cyan(`Exporting ${traceIdList.length} specified trace(s)...`),
      );
    } else {
      // Query for root traces first
      const rootParams = buildQueryParams({
        project: opts.project,
        traceIds: undefined,
        limit: opts.limit || 10,
        lastNMinutes: opts.lastNMinutes,
        since: opts.since,
        runType: undefined,
        isRoot: true,
        error:
          opts.error === false ? false : opts.error === true ? true : undefined,
        name: opts.name,
        rawFilter: opts.filter,
        minLatency: opts.minLatency,
        maxLatency: opts.maxLatency,
        minTokens: opts.minTokens,
        tags: opts.tags,
      });

      const spinner = createSpinner("Querying traces...", opts.format);
      spinner.start();
      const rootRuns: Run[] = [];

      try {
        for await (const run of client.listRuns(rootParams)) {
          rootRuns.push(run);
        }
      } finally {
        spinner.stop();
      }

      if (rootRuns.length === 0) {
        console.log(chalk.yellow("No traces found"));
        return;
      }

      rootRuns.sort((a, b) => {
        const aTime = a.start_time ? new Date(a.start_time).getTime() : 0;
        const bTime = b.start_time ? new Date(b.start_time).getTime() : 0;
        return bTime - aTime;
      });

      traceIdList = rootRuns.map((r) => getTraceId(r));
      console.log(
        chalk.green("✓") +
          ` Found ${traceIdList.length} trace(s). Fetching full hierarchy...`,
      );
    }

    // Fetch and export each trace
    const results: Array<[string, Run[]]> = [];
    const exportSpinner = createSpinner(
      `Fetching 0/${traceIdList.length}...`,
      opts.format,
    );
    exportSpinner.start();

    for (let i = 0; i < traceIdList.length; i++) {
      const tid = traceIdList[i];
      exportSpinner.text = `Fetching ${i + 1}/${traceIdList.length}...`;

      try {
        const fetchParams: QueryParams = { traceId: tid };
        if (opts.project || process.env.LANGSMITH_PROJECT) {
          fetchParams.projectName =
            opts.project || process.env.LANGSMITH_PROJECT;
        }

        const traceRuns: Run[] = [];
        for await (const run of client.listRuns(fetchParams)) {
          traceRuns.push(run);
        }

        if (traceRuns.length > 0) {
          results.push([tid, traceRuns]);
        }
      } catch (e) {
        console.warn(chalk.yellow(`\nWarning: Failed ${tid}: ${e}`));
      }
    }

    exportSpinner.stop();

    if (results.length === 0) {
      console.log(chalk.yellow("No traces exported"));
      return;
    }

    console.log(
      chalk.cyan(`Saving ${results.length} trace(s) to ${outputPath}/`),
    );

    for (let idx = 0; idx < results.length; idx++) {
      const [tid, traceRuns] = results[idx];
      let filename = opts.filenamePattern
        .replace("{trace_id}", tid)
        .replace("{index}", String(idx + 1));

      if (!filename.endsWith(".jsonl")) {
        filename = filename.includes(".")
          ? filename.replace(/\.[^.]+$/, ".jsonl")
          : filename + ".jsonl";
      }

      const filePath = path.join(outputPath, filename);
      const lines = traceRuns.map((run) =>
        JSON.stringify(extractRun(run, includeMetadata, includeIo)),
      );
      fs.writeFileSync(filePath, lines.join("\n") + "\n");

      console.log(
        `  ${chalk.green("✓")} ${tid.substring(0, 16)}... → ${filename} (${traceRuns.length} runs)`,
      );
    }

    console.log(
      `\n${chalk.green("✓")} Exported ${results.length} trace(s) to ${outputPath}/`,
    );
  });

addCommonFilterOptions(tracesExportCmd, false);

// ============================================================================
// RUNS Commands
// ============================================================================

const runs = program
  .command("runs")
  .description(
    "Operations on individual runs (flat list). Filters apply to ANY RUN.",
  );

// runs list
const runsListCmd = runs
  .command("list")
  .description("List runs matching filters (flat list)")
  .addOption(
    new Option("--format <format>", "Output format")
      .choices(["json", "pretty"])
      .default("pretty"),
  )
  .option("--include-metadata", "Include timing/tokens/costs")
  .action(async (opts) => {
    const client = getClient();

    const params = buildQueryParams({
      project: opts.project,
      traceIds: opts.traceIds,
      limit: opts.limit || 50,
      lastNMinutes: opts.lastNMinutes,
      since: opts.since,
      runType: opts.runType,
      isRoot: false,
      error:
        opts.error === false ? false : opts.error === true ? true : undefined,
      name: opts.name,
      rawFilter: opts.filter,
      minLatency: opts.minLatency,
      maxLatency: opts.maxLatency,
      minTokens: opts.minTokens,
      tags: opts.tags,
    });

    const spinner = createSpinner("Fetching runs...", opts.format);
    spinner.start();
    const allRuns: Run[] = [];

    try {
      for await (const run of client.listRuns(params)) {
        allRuns.push(run);
      }
    } finally {
      spinner.stop();
    }

    if (allRuns.length === 0) {
      console.log(chalk.yellow("No runs found"));
      return;
    }

    allRuns.sort((a, b) => {
      const aTime = a.start_time ? new Date(a.start_time).getTime() : 0;
      const bTime = b.start_time ? new Date(b.start_time).getTime() : 0;
      return bTime - aTime;
    });

    if (opts.format === "json") {
      const data = allRuns.map((r) =>
        extractRun(r, opts.includeMetadata, false),
      );
      outputJson(data);
    } else {
      console.log(chalk.green("✓") + ` Found ${allRuns.length} run(s)\n`);
      printRunsTable(allRuns, opts.includeMetadata, true);
    }
  });

addCommonFilterOptions(runsListCmd, true);

// runs get
runs
  .command("get <runId>")
  .description("Get a specific run by ID")
  .option("--project <name>", "Project name")
  .addOption(
    new Option("--format <format>", "Output format")
      .choices(["json", "pretty"])
      .default("pretty"),
  )
  .option("-o, --output <path>", "Output file")
  .option("--include-metadata", "Include timing/tokens/costs")
  .option("--include-io", "Include inputs/outputs")
  .option("--full", "Include everything (metadata + inputs/outputs)")
  .action(async (runId, opts) => {
    const client = getClient();

    const includeMetadata = opts.full || opts.includeMetadata;
    const includeIo = opts.full || opts.includeIo;

    let run: Run;
    try {
      run = await client.readRun(runId);
    } catch (e) {
      console.log(chalk.red(`Error fetching run ${runId}: ${e}`));
      return;
    }

    if (opts.format === "pretty") {
      console.log(chalk.green("✓") + " Found run\n");
      console.log(chalk.bold("Run:") + ` ${run.name}`);
      console.log(`  ID: ${chalk.dim(run.id)}`);
      console.log(`  Trace ID: ${chalk.dim(getTraceId(run))}`);
      console.log(`  Type: ${run.run_type}`);
      console.log(`  Parent: ${run.parent_run_id || "None (root)"}`);
      if (includeMetadata) {
        console.log(`  Duration: ${formatDuration(calcDuration(run))}`);
        console.log(`  Status: ${run.status || "N/A"}`);
      }
      if (includeIo) {
        console.log("\n" + chalk.bold("Inputs:"));
        if (run.inputs) {
          console.log(JSON.stringify(run.inputs, null, 2));
        }
        console.log("\n" + chalk.bold("Outputs:"));
        if (run.outputs) {
          console.log(JSON.stringify(run.outputs, null, 2));
        }
      }
    } else {
      const data = extractRun(run, includeMetadata, includeIo);
      outputJson(data, opts.output);
    }
  });

// runs export
const runsExportCmd = runs
  .command("export <outputFile>")
  .description("Export runs to a single JSONL file (flat list)")
  .option("--include-metadata", "Include timing/tokens/costs")
  .option("--include-io", "Include inputs/outputs")
  .option("--full", "Include everything (metadata + inputs/outputs)")
  .action(async (outputFile, opts) => {
    const includeMetadata = opts.full || opts.includeMetadata;
    const includeIo = opts.full || opts.includeIo;

    const client = getClient();
    let outputPath = path.resolve(outputFile);

    // Ensure parent directory exists
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });

    const params = buildQueryParams({
      project: opts.project,
      traceIds: opts.traceIds,
      limit: opts.limit || 100,
      lastNMinutes: opts.lastNMinutes,
      since: opts.since,
      runType: opts.runType,
      isRoot: false,
      error:
        opts.error === false ? false : opts.error === true ? true : undefined,
      name: opts.name,
      rawFilter: opts.filter,
      minLatency: opts.minLatency,
      maxLatency: opts.maxLatency,
      minTokens: opts.minTokens,
      tags: opts.tags,
    });

    // Export always uses "pretty" format with a spinner since output goes to file
    const spinner = createSpinner("Fetching runs...", "pretty");
    spinner.start();
    const allRuns: Run[] = [];

    try {
      for await (const run of client.listRuns(params)) {
        allRuns.push(run);
      }
    } finally {
      spinner.stop();
    }

    if (allRuns.length === 0) {
      console.log(chalk.yellow("No runs found"));
      return;
    }

    allRuns.sort((a, b) => {
      const aTime = a.start_time ? new Date(a.start_time).getTime() : 0;
      const bTime = b.start_time ? new Date(b.start_time).getTime() : 0;
      return bTime - aTime;
    });

    // Ensure .jsonl extension
    if (!outputPath.endsWith(".jsonl")) {
      outputPath = outputPath.replace(/\.[^.]+$/, ".jsonl");
      if (!outputPath.endsWith(".jsonl")) {
        outputPath += ".jsonl";
      }
    }

    const lines = allRuns.map((run) =>
      JSON.stringify(extractRun(run, includeMetadata, includeIo)),
    );
    fs.writeFileSync(outputPath, lines.join("\n") + "\n");

    console.log(
      chalk.green("✓") + ` Exported ${allRuns.length} run(s) to ${outputPath}`,
    );
  });

addCommonFilterOptions(runsExportCmd, true);

// ============================================================================
// Parse and run (only when executed directly, not when imported)
// ============================================================================

// Check if this file is being run directly (not imported)
const isMainModule =
  process.argv[1] &&
  (process.argv[1].endsWith("query_traces.ts") ||
    process.argv[1].endsWith("query_traces.js"));

if (isMainModule) {
  program.parse();
}
