/**
 * README screenshot generator (not a test). Run with:
 *   SCREENSHOTS=1 npx playwright test e2e/screenshots.spec.ts
 * Writes PNGs to ../docs/screenshots/.
 */
import { expect, test } from "@playwright/test";

const OUT = "../docs/screenshots";

test.skip(!process.env.SCREENSHOTS, "screenshot generation is opt-in");

test.use({ viewport: { width: 1440, height: 900 }, colorScheme: "light" });

test("capture screenshots", async ({ page }) => {
  test.setTimeout(180_000);

  await page.goto("/");
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${OUT}/landing.png`, fullPage: false });

  // Demo run → Mission Control
  await page.goto("/demo");
  await page.waitForURL(/\/runs\//, { timeout: 30_000 });
  const runUrl = page.url();
  const analyze = page.getByRole("button", { name: /^Analyze \d+$/ });
  try {
    await analyze.waitFor({ timeout: 10_000 });
    await page.screenshot({ path: `${OUT}/interrupt.png` });
    await analyze.click();
  } catch {
    /* no interrupt */
  }
  await expect(page.getByRole("link", { name: /explore results/i })).toBeVisible({
    timeout: 60_000,
  });
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/mission-control.png` });

  await page.goto(`${runUrl}/results`);
  await expect(page.getByText(/listings, ranked/)).toBeVisible({ timeout: 20_000 });
  await page.waitForTimeout(2500); // map tiles
  await page.screenshot({ path: `${OUT}/results-explorer.png` });

  await page.goto(`${runUrl}/trace`);
  await expect(page.getByRole("heading", { name: "Agent Trace" })).toBeVisible();
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/trace-viewer.png` });

  // Lease analyzer on the kitchen-sink sample
  await page.goto("/leases/upload");
  await page.getByText(/El Camino Lofts/i).first().click();
  await page.waitForURL(/\/leases\//, { timeout: 20_000 });
  await expect(page.getByLabel(/Flagged clause/).first()).toBeVisible({ timeout: 40_000 });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${OUT}/lease-analyzer.png` });

  // Negotiation studio for the top listing
  await page.goto(`${runUrl}/results`);
  const firstCard = page.locator("a[href^='/listings/']").first();
  const listingHref = await firstCard.getAttribute("href");
  await page.goto(`${listingHref}/negotiate`);
  await expect(page.getByLabel("Email body")).not.toBeEmpty({ timeout: 30_000 });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/negotiation-studio.png` });
});
