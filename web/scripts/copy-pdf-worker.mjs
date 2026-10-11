// Copy the pdf.js worker into public/ so react-pdf can load it same-origin
// without webpack trying to parse the minified module.
import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const workerPath = join(
  dirname(require.resolve("pdfjs-dist/package.json")),
  "build",
  "pdf.worker.min.mjs",
);
mkdirSync("public", { recursive: true });
copyFileSync(workerPath, join("public", "pdf.worker.min.mjs"));
console.log("copied pdf.worker.min.mjs -> public/");
