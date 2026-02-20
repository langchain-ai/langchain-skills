#!/usr/bin/env npx tsx
/**
 * Query and view LangSmith datasets and local dataset files.
 */

import { Client } from "langsmith";
import { Command, Option } from "commander";
import chalk from "chalk";
import Table from "cli-table3";
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

export interface Example {
  inputs?: Record<string, unknown>;
  outputs?: Record<string, unknown>;
  [key: string]: unknown;
}

export function displayExamples(
  examples: Example[],
  fmt: string,
  limit: number,
): void {
  const sliced = examples.slice(0, limit);

  if (fmt === "json") {
    console.log(JSON.stringify(sliced, null, 2));
  } else {
    for (let i = 0; i < sliced.length; i++) {
      const ex = sliced[i];
      console.log(chalk.bold(`Example ${i + 1}:`));

      if (ex.inputs !== undefined && ex.outputs !== undefined) {
        // LangSmith format with inputs/outputs
        console.log(chalk.blue("─── Inputs ───"));
        console.log(JSON.stringify(ex.inputs, null, 2));

        if (ex.outputs) {
          console.log(chalk.green("─── Outputs ───"));
          console.log(JSON.stringify(ex.outputs, null, 2));
        }
      } else {
        // Regular JSON format
        console.log(JSON.stringify(ex, null, 2));
      }
      console.log();
    }
  }
}

// ============================================================================
// CLI
// ============================================================================

const program = new Command();

program
  .name("query_datasets")
  .description("Query and view datasets")
  .version("1.0.0");

// list-datasets command
program
  .command("list-datasets")
  .description("List all LangSmith datasets")
  .action(async () => {
    const client = getClient();
    const datasets: Array<{
      name: string;
      id: string;
      description?: string;
      example_count?: number;
    }> = [];

    for await (const ds of client.listDatasets({ limit: 100 })) {
      datasets.push({
        name: ds.name,
        id: ds.id,
        description: ds.description,
        example_count: ds.example_count,
      });
    }

    if (datasets.length === 0) {
      console.log(chalk.yellow("No datasets found"));
      return;
    }

    const table = new Table({
      head: [
        chalk.bold("Name"),
        chalk.bold("ID"),
        chalk.bold("Description"),
        chalk.bold("Examples"),
      ],
      style: { head: [], border: [] },
    });

    for (const ds of datasets) {
      table.push([
        chalk.cyan(ds.name),
        chalk.dim(ds.id.substring(0, 16) + "..."),
        chalk.yellow((ds.description || "").substring(0, 50)),
        chalk.green(String(ds.example_count || 0)),
      ]);
    }

    console.log(chalk.bold("LangSmith Datasets"));
    console.log(table.toString());
  });

// show command
program
  .command("show <datasetName>")
  .description("Show examples from a LangSmith dataset")
  .option("--limit <n>", "Number of examples to show", "5")
  .addOption(
    new Option("--format <format>", "Output format")
      .choices(["pretty", "json"])
      .default("pretty"),
  )
  .action(async (datasetName, opts) => {
    const client = getClient();
    const limit = parseInt(opts.limit);

    let dataset;
    try {
      dataset = await client.readDataset({ datasetName });
    } catch {
      console.log(chalk.red(`Error: Dataset '${datasetName}' not found`));
      return;
    }

    const examples: Example[] = [];
    for await (const ex of client.listExamples({
      datasetId: dataset.id,
      limit,
    })) {
      examples.push({
        inputs: ex.inputs,
        outputs: ex.outputs,
      });
    }

    if (examples.length === 0) {
      console.log(chalk.yellow(`No examples in dataset '${datasetName}'`));
      return;
    }

    console.log(chalk.cyan("Dataset:") + ` ${dataset.name}`);
    console.log(chalk.dim(`Total examples: ${dataset.example_count}`) + "\n");
    displayExamples(examples, opts.format, limit);
  });

// view-file command
program
  .command("view-file <filePath>")
  .description("View examples from a local dataset file (JSON or CSV)")
  .option("--limit <n>", "Number of examples to show", "5")
  .addOption(
    new Option("--format <format>", "Output format")
      .choices(["pretty", "json"])
      .default("pretty"),
  )
  .action((filePath, opts) => {
    const resolvedPath = path.resolve(filePath);
    const limit = parseInt(opts.limit);

    if (!fs.existsSync(resolvedPath)) {
      console.log(chalk.red(`Error: File not found: ${filePath}`));
      return;
    }

    const ext = path.extname(resolvedPath);

    if (ext === ".json") {
      const content = fs.readFileSync(resolvedPath, "utf-8");
      let data = content.trim() ? JSON.parse(content) : [];
      data = Array.isArray(data) ? data : [data];

      console.log(chalk.cyan("File:") + ` ${path.basename(resolvedPath)}`);
      console.log(chalk.dim(`Total: ${data.length}`) + "\n");
      displayExamples(data, opts.format, limit);
    } else if (ext === ".csv") {
      const content = fs.readFileSync(resolvedPath, "utf-8");
      const lines = content.split("\n").filter((l) => l.trim());
      if (lines.length === 0) {
        console.log(chalk.yellow("Empty CSV file"));
        return;
      }

      const headers = lines[0].split(",");
      const rows: Record<string, string>[] = [];

      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(",");
        const row: Record<string, string> = {};
        for (let j = 0; j < headers.length; j++) {
          row[headers[j]] = values[j] || "";
        }
        rows.push(row);
      }

      console.log(chalk.cyan("File:") + ` ${path.basename(resolvedPath)}`);
      console.log(chalk.dim(`Total: ${rows.length}`) + "\n");

      if (opts.format === "json") {
        console.log(JSON.stringify(rows.slice(0, limit), null, 2));
      } else {
        const table = new Table({
          head: headers.map((h) => chalk.cyan(h)),
          style: { head: [], border: [] },
        });

        for (const row of rows.slice(0, limit)) {
          table.push(
            Object.values(row).map((v) => String(v).substring(0, 100)),
          );
        }
        console.log(table.toString());
      }
    } else {
      console.log(chalk.red(`Error: Unsupported file type '${ext}'`));
    }
  });

// structure command
program
  .command("structure <filePath>")
  .description("Analyze and show the structure of a dataset file")
  .action((filePath) => {
    const resolvedPath = path.resolve(filePath);

    if (!fs.existsSync(resolvedPath)) {
      console.log(chalk.red(`Error: File not found: ${filePath}`));
      return;
    }

    console.log(chalk.cyan("File:") + ` ${path.basename(resolvedPath)}`);

    const ext = path.extname(resolvedPath);

    if (ext === ".json") {
      const content = fs.readFileSync(resolvedPath, "utf-8");
      let data = content.trim() ? JSON.parse(content) : [];
      data = Array.isArray(data) ? data : [data];

      console.log(chalk.cyan("Format:") + " JSON");
      console.log(chalk.cyan("Examples:") + ` ${data.length}\n`);

      if (data.length > 0) {
        console.log(chalk.bold("Structure:"));
        console.log(JSON.stringify(data[0], null, 2).substring(0, 500) + "\n");

        const allKeys = new Set<string>();
        for (const ex of data) {
          if (typeof ex === "object" && ex !== null) {
            for (const key of Object.keys(ex)) {
              allKeys.add(key);
            }
          }
        }

        console.log(chalk.bold("Fields:"));
        for (const key of Array.from(allKeys).sort()) {
          const count = data.filter(
            (ex: unknown) =>
              typeof ex === "object" && ex !== null && key in (ex as object),
          ).length;
          const pct = ((count / data.length) * 100).toFixed(0);
          console.log(`  ${key}: ${count}/${data.length} (${pct}%)`);
        }
      }
    } else if (ext === ".csv") {
      const content = fs.readFileSync(resolvedPath, "utf-8");
      const lines = content.split("\n").filter((l) => l.trim());

      if (lines.length === 0) {
        console.log(chalk.yellow("Empty CSV file"));
        return;
      }

      const headers = lines[0].split(",");
      const rows = lines.slice(1);

      console.log(chalk.cyan("Format:") + " CSV");
      console.log(chalk.cyan("Rows:") + ` ${rows.length}\n`);

      console.log(chalk.bold("Columns:"));
      for (const col of headers) {
        const nonEmpty = rows.filter((row) => {
          const values = row.split(",");
          const idx = headers.indexOf(col);
          return values[idx] && values[idx].trim();
        }).length;
        const pct =
          rows.length > 0 ? ((nonEmpty / rows.length) * 100).toFixed(0) : 0;
        console.log(`  ${col}: ${nonEmpty}/${rows.length} (${pct}%)`);
      }
    } else {
      console.log(chalk.red(`Error: Unsupported file type '${ext}'`));
    }
  });

// export command
program
  .command("export <datasetName> <outputFile>")
  .description("Export LangSmith dataset to local file")
  .option("--limit <n>", "Number of examples to export", "100")
  .action(async (datasetName, outputFile, opts) => {
    const client = getClient();
    const limit = parseInt(opts.limit);

    let dataset;
    try {
      dataset = await client.readDataset({ datasetName });
    } catch {
      console.log(chalk.red(`Error: Dataset '${datasetName}' not found`));
      return;
    }

    const examples: Example[] = [];
    for await (const ex of client.listExamples({
      datasetId: dataset.id,
      limit,
    })) {
      examples.push({
        inputs: ex.inputs,
        outputs: ex.outputs,
      });
    }

    if (examples.length === 0) {
      console.log(chalk.yellow(`No examples in dataset '${datasetName}'`));
      return;
    }

    const outputPath = path.resolve(outputFile);
    fs.writeFileSync(outputPath, JSON.stringify(examples, null, 2));
    console.log(
      chalk.green("✓") +
        ` Exported ${examples.length} examples to ${outputFile}`,
    );
  });

// Only run CLI when executed directly (not when imported)
const isMainModule =
  process.argv[1] &&
  (process.argv[1].endsWith("query_datasets.ts") ||
    process.argv[1].endsWith("query_datasets.js"));

if (isMainModule) {
  program.parse();
}
