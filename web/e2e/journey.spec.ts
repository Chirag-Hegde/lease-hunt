import { expect, test } from "@playwright/test";

test("full journey: brief → run → results → listing → lease → negotiation → compare", async ({
  page,
}) => {
  // 1. Landing → demo run
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("team of AI agents");
  await page.getByRole("link", { name: /try the demo/i }).click();

  // 2. Mission Control: agents light up, run finishes (resume interrupt if asked)
  await page.waitForURL(/\/runs\//, { timeout: 30_000 });
  const analyzeButton = page.getByRole("button", { name: /^Analyze \d+$/ });
  try {
    await analyzeButton.click({ timeout: 15_000 });
  } catch {
    // interrupt may not fire if under threshold — fine
  }
  await expect(page.getByRole("link", { name: /explore results/i })).toBeVisible({
    timeout: 60_000,
  });

  // 3. Results Explorer: ranked list + sliders re-rank
  await page.getByRole("link", { name: /explore results/i }).click();
  await page.waitForURL(/\/results/);
  await expect(page.getByText(/listings, ranked by your weights/)).toBeVisible({
    timeout: 20_000,
  });
  const firstCard = page.locator("a[href^='/listings/']").first();
  await expect(firstCard).toBeVisible();

  // 4. Listing detail: scorecard sections present
  const listingHref = await firstCard.getAttribute("href");
  await page.goto(listingHref!);
  await expect(page.getByRole("heading", { name: "Commute" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Reputation" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Value" })).toBeVisible();

  // 5. Lease analyzer via a sample lease: highlights + findings
  await page.goto("/leases/upload");
  await page.getByText(/El Camino Lofts/i).first().click();
  await page.waitForURL(/\/leases\//, { timeout: 20_000 });
  await expect(page.getByText(/Not legal advice/i)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/high risk/i).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByLabel(/Flagged clause/).first()).toBeVisible({ timeout: 30_000 });

  // 6. Negotiation studio: drafts generate with leverage chips
  await page.goto(`${listingHref}/negotiate`);
  await expect(page.getByLabel("Email body")).not.toBeEmpty({ timeout: 30_000 });
  await expect(page.getByRole("tab", { name: "data-driven" })).toBeVisible();
  const chips = page.getByRole("checkbox", { name: /include leverage/i });
  expect(await chips.count()).toBeGreaterThan(0);

  // 7. Compare two listings
  await page.goto(listingHref!.replace("/listings/", "/compare?ids=") + ",demo0001");
  await expect(page.getByRole("heading", { name: "Compare" })).toBeVisible();
  await expect(page.getByText("True monthly cost")).toBeVisible({ timeout: 15_000 });
});
