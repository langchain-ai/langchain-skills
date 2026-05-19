import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  test: {
    include: ["tests/**/*.test.ts"],
  },
  resolve: {
    alias: {
      "#swarm": path.resolve(import.meta.dirname, "config/skills/swarm/scripts"),
    },
  },
});
