#!/usr/bin/env npx tsx
/**
 * Upload JavaScript evaluators to LangSmith.
 *
 * This TypeScript CLI uploads JavaScript code evaluators.
 * For Python evaluators, use upload_evaluators.py instead.
 */

import { Client } from "langsmith";
import { Command } from "commander";
import chalk from "chalk";
import Table from "cli-table3";
import * as dotenv from "dotenv";
import * as fs from "fs";
import * as readline from "readline";

dotenv.config();

// ============================================================================
// Configuration
// ============================================================================

export const LANGSMITH_API_KEY = process.env.LANGSMITH_API_KEY;
export const LANGSMITH_API_URL =
  process.env.LANGSMITH_API_URL || "https://api.smith.langchain.com";
export const LANGSMITH_WORKSPACE_ID = process.env.LANGSMITH_WORKSPACE_ID;

// Only validate API key when running as CLI (not when imported for testing)
const isMainModule =
  process.argv[1] &&
  (process.argv[1].endsWith("upload_evaluators.ts") ||
    process.argv[1].endsWith("upload_evaluators.js"));

if (isMainModule && !LANGSMITH_API_KEY) {
  console.error(
    chalk.red("Error: LANGSMITH_API_KEY environment variable is required"),
  );
  process.exit(1);
}

// ============================================================================
// Types
// ============================================================================

export interface CodeEvaluator {
  code: string;
  language: string;
}

export interface EvaluatorPayload {
  display_name: string;
  evaluators: CodeEvaluator[];
  sampling_rate: number;
  target_dataset_ids?: string[];
  target_project_ids?: string[];
}

export interface Rule {
  id: string;
  display_name: string;
  sampling_rate: number;
  target_dataset_ids?: string[];
  target_project_ids?: string[];
}

// ============================================================================
// API Helpers
// ============================================================================

export function getHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "x-api-key": LANGSMITH_API_KEY!,
    "Content-Type": "application/json",
  };
  if (LANGSMITH_WORKSPACE_ID) {
    headers["x-tenant-id"] = LANGSMITH_WORKSPACE_ID;
  }
  return headers;
}

export async function getRules(): Promise<Rule[]> {
  const url = `${LANGSMITH_API_URL}/runs/rules`;
  const response = await fetch(url, { headers: getHeaders() });
  if (!response.ok) {
    throw new Error(`Failed to get rules: ${response.statusText}`);
  }
  return response.json() as Promise<Rule[]>;
}

export async function evaluatorExists(name: string): Promise<boolean> {
  const rules = await getRules();
  return rules.some((rule) => rule.display_name === name);
}

async function resolveDatasetId(datasetName: string): Promise<string | null> {
  try {
    const client = new Client({ apiKey: LANGSMITH_API_KEY });
    const dataset = await client.readDataset({ datasetName });
    return dataset.id;
  } catch (e) {
    console.log(
      chalk.yellow(`Warning: Could not find dataset '${datasetName}': ${e}`),
    );
    return null;
  }
}

async function resolveProjectId(projectName: string): Promise<string | null> {
  try {
    const client = new Client({ apiKey: LANGSMITH_API_KEY });
    for await (const project of client.listProjects()) {
      if (project.name === projectName) {
        return project.id;
      }
    }
    console.log(
      chalk.yellow(`Warning: Could not find project '${projectName}'`),
    );
    return null;
  } catch (e) {
    console.log(
      chalk.yellow(`Warning: Error finding project '${projectName}': ${e}`),
    );
    return null;
  }
}

// ============================================================================
// Evaluator Operations
// ============================================================================

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

export async function deleteEvaluator(
  name: string,
  confirm = true,
): Promise<boolean> {
  const rules = await getRules();
  const rule = rules.find((r) => r.display_name === name);

  if (!rule) {
    console.log(chalk.yellow(`Evaluator '${name}' not found`));
    return false;
  }

  if (confirm) {
    console.log(chalk.yellow(`About to delete evaluator: '${name}'`));
    const confirmed = await promptConfirm("Are you sure?");
    if (!confirmed) {
      console.log(chalk.yellow("Deletion cancelled"));
      return false;
    }
  }

  const deleteUrl = `${LANGSMITH_API_URL}/runs/rules/${rule.id}`;
  const response = await fetch(deleteUrl, {
    method: "DELETE",
    headers: getHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to delete: ${response.statusText}`);
  }

  console.log(chalk.green(`✓ Deleted evaluator '${name}'`));
  return true;
}

function extractJavaScriptFunction(
  fileContent: string,
  functionName: string,
): string | null {
  // Match JavaScript/TypeScript function definitions
  // Handles: function name(), async function name(), const name = () =>, const name = async () =>
  const patterns = [
    // async function functionName(...)  { ... }
    new RegExp(
      `(async\\s+function\\s+${functionName}\\s*\\([^)]*\\)\\s*\\{[\\s\\S]*?\\n\\})`,
      "m",
    ),
    // function functionName(...) { ... }
    new RegExp(
      `(function\\s+${functionName}\\s*\\([^)]*\\)\\s*\\{[\\s\\S]*?\\n\\})`,
      "m",
    ),
    // const functionName = async (...) => { ... }
    new RegExp(
      `(const\\s+${functionName}\\s*=\\s*async\\s*\\([^)]*\\)\\s*=>\\s*\\{[\\s\\S]*?\\n\\})`,
      "m",
    ),
    // const functionName = (...) => { ... }
    new RegExp(
      `(const\\s+${functionName}\\s*=\\s*\\([^)]*\\)\\s*=>\\s*\\{[\\s\\S]*?\\n\\})`,
      "m",
    ),
  ];

  for (const pattern of patterns) {
    const match = fileContent.match(pattern);
    if (match) {
      let source = match[1].trim();
      // Rename function to performEval as required by LangSmith for JS
      source = source.replace(
        new RegExp(`(async\\s+)?function\\s+${functionName}\\s*\\(`),
        "$1function performEval(",
      );
      source = source.replace(
        new RegExp(`const\\s+${functionName}\\s*=`),
        "function performEval",
      );
      // Handle arrow function conversion to regular function
      source = source.replace(
        /function performEval\s*async\s*\(([^)]*)\)\s*=>\s*\{/,
        "async function performEval($1) {",
      );
      source = source.replace(
        /function performEval\s*\(([^)]*)\)\s*=>\s*\{/,
        "function performEval($1) {",
      );
      return source;
    }
  }

  return null;
}

async function createCodePayload(options: {
  name: string;
  source: string;
  sampleRate: number;
  targetDataset?: string;
  targetProject?: string;
  replace: boolean;
  skipConfirm: boolean;
}): Promise<EvaluatorPayload | null> {
  // Check if exists
  if (await evaluatorExists(options.name)) {
    if (!options.replace) {
      console.log(
        chalk.yellow(
          `Evaluator '${options.name}' already exists. Use --replace to overwrite.`,
        ),
      );
      return null;
    } else {
      if (!options.skipConfirm) {
        console.log(
          chalk.yellow(`Evaluator '${options.name}' already exists.`),
        );
        const confirmed = await promptConfirm("Replace existing evaluator?");
        if (!confirmed) {
          console.log(chalk.yellow("Upload cancelled"));
          return null;
        }
      }
      await deleteEvaluator(options.name, false);
    }
  }

  // Resolve targets
  const datasetIds: string[] = [];
  const projectIds: string[] = [];

  if (options.targetDataset) {
    const datasetId = await resolveDatasetId(options.targetDataset);
    if (datasetId) {
      datasetIds.push(datasetId);
    }
  }

  if (options.targetProject) {
    const projectId = await resolveProjectId(options.targetProject);
    if (projectId) {
      projectIds.push(projectId);
    }
  }

  return {
    display_name: options.name,
    evaluators: [{ code: options.source, language: "javascript" }],
    sampling_rate: options.sampleRate,
    target_dataset_ids: datasetIds.length > 0 ? datasetIds : undefined,
    target_project_ids: projectIds.length > 0 ? projectIds : undefined,
  };
}

export async function createEvaluator(
  payload: EvaluatorPayload,
): Promise<boolean> {
  const url = `${LANGSMITH_API_URL}/runs/rules`;

  const data: Record<string, unknown> = {
    display_name: payload.display_name,
    sampling_rate: payload.sampling_rate,
    code_evaluators: payload.evaluators.map((e) => ({
      code: e.code,
      language: e.language,
    })),
  };

  if (payload.target_dataset_ids && payload.target_dataset_ids.length === 1) {
    data.dataset_id = payload.target_dataset_ids[0];
  }
  if (payload.target_project_ids && payload.target_project_ids.length === 1) {
    data.session_id = payload.target_project_ids[0];
  }

  const response = await fetch(url, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  });

  if (response.ok) {
    console.log(chalk.green(`✓ Uploaded evaluator '${payload.display_name}'`));
    return true;
  } else {
    const text = await response.text();
    console.log(
      chalk.red(`✗ Failed to upload '${payload.display_name}': ${text}`),
    );
    return false;
  }
}

// ============================================================================
// CLI
// ============================================================================

const program = new Command();

program
  .name("upload_evaluators")
  .description("Upload and manage JavaScript evaluators in LangSmith")
  .version("1.0.0");

// list command
program
  .command("list")
  .description("List all evaluators")
  .action(async () => {
    const rules = await getRules();

    if (rules.length === 0) {
      console.log(chalk.yellow("No evaluators found"));
      return;
    }

    const table = new Table({
      head: [
        chalk.bold("Name"),
        chalk.bold("Sampling Rate"),
        chalk.bold("Targets"),
      ],
      style: { head: [], border: [] },
    });

    for (const rule of rules) {
      const name = rule.display_name || "";
      const rate = rule.sampling_rate || 1.0;

      const targets: string[] = [];
      if (rule.target_dataset_ids && rule.target_dataset_ids.length > 0) {
        targets.push(`${rule.target_dataset_ids.length} datasets`);
      }
      if (rule.target_project_ids && rule.target_project_ids.length > 0) {
        targets.push(`${rule.target_project_ids.length} projects`);
      }

      table.push([
        chalk.cyan(name),
        chalk.green(`${(rate * 100).toFixed(0)}%`),
        chalk.yellow(targets.length > 0 ? targets.join(", ") : "All runs"),
      ]);
    }

    console.log(chalk.bold("LangSmith Evaluators"));
    console.log(table.toString());
  });

// delete command
program
  .command("delete <name>")
  .description("Delete an evaluator by name")
  .option("--yes", "Skip confirmation prompt")
  .action(async (name, opts) => {
    await deleteEvaluator(name, !opts.yes);
  });

// upload command
program
  .command("upload <evaluatorFile>")
  .description("Upload a JavaScript evaluator from a .js or .ts file")
  .requiredOption("--name <name>", "Display name for evaluator")
  .requiredOption("--function <name>", "Function name to extract from file")
  .option("--dataset <name>", "Target dataset name")
  .option("--project <name>", "Target project name")
  .option("--sample-rate <rate>", "Sampling rate (0.0-1.0)", "1.0")
  .option("--replace", "Replace if exists")
  .option("--yes", "Skip confirmation prompts")
  .action(async (evaluatorFile, opts) => {
    // Read the file
    if (!fs.existsSync(evaluatorFile)) {
      console.log(chalk.red(`File not found: ${evaluatorFile}`));
      return;
    }

    const fileContent = fs.readFileSync(evaluatorFile, "utf-8");

    // Extract the function source
    const source = extractJavaScriptFunction(fileContent, opts.function);
    if (!source) {
      console.log(
        chalk.red(`Function '${opts.function}' not found in ${evaluatorFile}`),
      );
      return;
    }

    // Create payload
    const payload = await createCodePayload({
      name: opts.name,
      source,
      sampleRate: parseFloat(opts.sampleRate),
      targetDataset: opts.dataset,
      targetProject: opts.project,
      replace: opts.replace || false,
      skipConfirm: opts.yes || false,
    });

    if (payload) {
      await createEvaluator(payload);
    }
  });

if (isMainModule) {
  program.parse();
}
