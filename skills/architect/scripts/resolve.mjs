// Resolves repo:// line ranges with OpenWiki's own evidence resolver, so C4 evidence ages and
// relocates exactly like OpenWiki claims. Reads {root, items: [{resource, version}]} from stdin,
// writes [{current: {resource, version} | null} | {error}] to stdout.
// OPENWIKI_CLI must point to openwiki's dist/cli/cli.js (pinned version; internal module).
import { readFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const cli = process.env.OPENWIKI_CLI;
if (!cli) {
  console.error("OPENWIKI_CLI is not set");
  process.exit(2);
}
const dist = path.dirname(path.dirname(cli));
const pinned = process.env.OPENWIKI_PINNED_VERSION ?? "0.7.2";
let version;
try {
  version = JSON.parse(readFileSync(path.join(path.dirname(dist), "package.json"), "utf8")).version;
} catch {
  version = undefined;
}
if (version !== pinned) {
  console.error(`OpenWiki ${version} found, ${pinned} pinned: evidence versions are not comparable`);
  process.exit(2);
}
const resolverPath = path.join(dist, "claims", "evidence", "repository", "resolver.js");
const { RepositoryEvidenceResolver } = await import(pathToFileURL(resolverPath).href);

let input = "";
for await (const chunk of process.stdin) input += chunk;
const { root, items } = JSON.parse(input);
const resolver = new RepositoryEvidenceResolver({ rootDir: path.resolve(root) });

const out = [];
for (const { resource, version } of items) {
  try {
    const result = await resolver.resolve(resource, version ?? undefined);
    out.push({ current: result ? result.evidence : null });
  } catch (error) {
    out.push({ error: String(error?.message ?? error) });
  }
}
process.stdout.write(JSON.stringify(out));
