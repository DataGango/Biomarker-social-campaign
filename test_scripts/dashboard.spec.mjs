import { expect, test } from "@playwright/test";

test("health endpoint reports a ready research index and refresh cadence", async ({ request }) => {
  const healthResponse = await request.get("/api/health");
  expect(healthResponse.status()).toBe(200);
  const health = await healthResponse.json();
  expect(health.ok).toBe(true);
  expect(health.indexed_chunks).toBeGreaterThan(0);

  const statusResponse = await request.get("/api/status");
  expect(statusResponse.status()).toBe(200);
  expect(statusResponse.headers()["cache-control"]).toBe("no-store");
  const status = await statusResponse.json();
  expect(status.refresh_interval_seconds).toBe(3 * 60 * 60);
  expect(status.source_count).toBeGreaterThan(0);
  expect(status.indexed_source_count).toBeGreaterThan(0);
  expect(status.cached_sources.length).toBe(status.source_count);
});

test("dashboard displays live refresh status", async ({ page }) => {
  await page.goto("/dashboard.html");
  await expect(page.locator("#refresh-message")).toContainText(/Next web scrape|Scraping NCI and ACS/);
  await expect(page.locator("#cached-source-count")).not.toHaveText("—");
  await expect(page.locator("#indexed-chunk-count")).not.toHaveText("—");
});

test("diagnosis figures distinguish the NCI baseline from illustrative future scenarios", async ({ page }) => {
  await page.goto("/");
  const estimates = page.getByRole("region", { name: "Annual U.S. diagnoses · ages 0–19" });
  await expect(estimates).toContainText("2024 · NCI estimate");
  await expect(estimates).toContainText("2025 · scenario");
  await expect(estimates).toContainText("2026 · scenario");
  await expect(estimates).toContainText("not NCI estimates or model-based projections");
});

test("root route is the accessible dashboard landing page", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("Childhood Cancer Research Dashboard");
  await expect(page.getByRole("main")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1, name: /Childhood cancer/ })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Dashboard sections" })).toBeVisible();

  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
});

test("mobile landing page has no horizontal overflow and keeps touch navigation visible", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: /Childhood cancer/ })).toBeVisible();
  const dimensions = await page.evaluate(() => ({
    documentWidth: document.documentElement.scrollWidth,
    viewportWidth: document.documentElement.clientWidth,
    navHeight: document.querySelector(".nav").getBoundingClientRect().height,
  }));
  expect(dimensions.documentWidth).toBeLessThanOrEqual(dimensions.viewportWidth);
  expect(dimensions.navHeight).toBeGreaterThanOrEqual(48);
});

test("assistant shows an answer and its source after submission", async ({ page }) => {
  await page.route("**/api/ask", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        answer: "Childhood cancer outcomes vary by cancer type and clinical factors [S1].",
        sources: [{ id: "S1", url: "https://www.cancer.gov/types/childhood-cancers/child-adolescent-cancers-fact-sheet" }],
      }),
    });
  });
  await page.goto("/");
  await page.getByLabel("Your question").fill("What affects childhood cancer outcomes?");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.locator("#chat-log")).toContainText("Childhood cancer outcomes vary");
  await expect(page.locator("#chat-log a")).toHaveAttribute("href", /cancer.gov/);
});

test("poster maker loads the childhood cancer awareness prompt preset", async ({ page }) => {
  await page.goto("/poster-agent/");
  await expect(page.getByLabel("Start from a reviewed prompt")).toHaveValue("childhood-cancer");
  const brief = page.getByLabel("What should the poster say and feel like?");
  await expect(brief).toHaveValue(/childhood cancer includes many distinct diseases/);
  await expect(brief).toHaveValue(/not medical advice/);
  expect((await brief.inputValue()).length).toBeLessThanOrEqual(1500);
  await page.getByRole("button", { name: "Create poster" }).click();
  await expect(page.locator("#preview")).toBeVisible();
  await expect(page.locator("#status")).toContainText("Reviewed childhood-cancer poster ready");
  await expect(page.locator("#preview")).toHaveAttribute("srcdoc", /Childhood cancer is not one disease/);
});

test("poster API creates the childhood-cancer preset without an LLM key", async ({ request }) => {
  const response = await request.post("/api/poster/generate", {
    data: {
      preset: "childhood-cancer",
      prompt: "Childhood cancer awareness poster for families.",
    },
  });
  expect(response.status()).toBe(200);
  const result = await response.json();
  expect(result.generation_mode).toBe("reviewed-template");
  expect(result.poster.title).toContain("Childhood cancer is not one disease");
  expect(result.poster.sources).toContainEqual(expect.stringContaining("cancer.gov/types/childhood-cancers"));
  expect(result.html).toContain("not diagnosis, treatment advice");
});

test("treatment planning guide is reachable and keeps individualized decisions with clinicians", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Treatment plan guide" }).click();
  await expect(page).toHaveURL(/treatment-plan\.html$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Understanding a treatment plan");
  await expect(page.getByText(/does not recommend a treatment/i)).toBeVisible();
  await expect(page.getByRole("link", { name: /National Cancer Institute.*Clinical Trials/s })).toBeVisible();
});

test("care directory opens from dashboard and links the state-filterable COG locator", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Find care by state" }).click();
  await expect(page).toHaveURL(/care-locations\.html$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Find childhood cancer care by state");
  await expect(page.getByTitle(/Children’s Oncology Group member institution locator/)).toHaveAttribute(
    "src",
    "https://childrensoncologygroup.org/patients-families/member-institutions/",
  );
  await expect(page.getByRole("link", { name: "Open official locator" })).toHaveAttribute("target", "_blank");
  await expect(page.getByText(/Not every listed center is a pediatric treatment facility/)).toBeVisible();
});

test("fundraising episode is linked across dashboard, care, and treatment pages and media plays", async ({ page, request }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Fundraising episode" }).click();
  await expect(page).toHaveURL(/fundraising-episode\.html$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Fundraising with trust and purpose");
  await expect(page.locator("#episode-audio source")).toHaveAttribute("src", "/media/fundraising-episode-01.m4a");
  await expect(page.locator("#episode-video source")).toHaveAttribute("src", "/media/fundraising-episode-01.mp4");
  await expect(page.getByRole("heading", { name: "Episode transcript" })).toBeVisible();
  await expect(page.getByText(/Do not use private patient information/)).toBeVisible();

  const audio = await request.get("/media/fundraising-episode-01.m4a");
  const video = await request.get("/media/fundraising-episode-01.mp4");
  expect(audio.status()).toBe(200);
  expect(audio.headers()["content-type"]).toContain("audio/mp4");
  expect(video.status()).toBe(200);
  expect(video.headers()["content-type"]).toContain("video/mp4");

  await page.goto("/treatment-plan.html");
  await expect(page.getByRole("link", { name: "Fundraising episode" })).toHaveAttribute("href", "/fundraising-episode.html");
  await page.goto("/care-locations.html");
  await expect(page.getByRole("link", { name: "Fundraising episode" })).toHaveAttribute("href", "/fundraising-episode.html");
});

test("Global Health and Technology Radio links from dashboard and fundraiser and shows saved episodes", async ({ page, request }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Global Health & Technology Radio" }).click();
  await expect(page).toHaveURL(/radio-channel\.html$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Global Health & Technology Radio");
  await expect(page.getByText(/no live stream or automatic daily broadcast is running yet/i)).toBeVisible();
  await expect(page.locator("#radio-audio source")).toHaveAttribute("src", "/media/fundraising-episode-01.m4a");
  await expect(page.getByRole("link", { name: /Childhood cancer, in context/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /tiny robots guide cancer medicine/ })).toBeVisible();
  await expect(page.getByText(/Guest submissions are not enabled yet/)).toBeVisible();

  const audioResponse = await request.get("/media/fundraising-episode-01.m4a");
  expect(audioResponse.status()).toBe(200);
  expect(audioResponse.headers()["content-type"]).toContain("audio/mp4");

  await page.goto("/fundraising.html");
  await expect(page.getByRole("link", { name: "Global Health & Technology Radio" })).toHaveAttribute("href", "/radio-channel.html");
});

test("dashboard and scraped source cache support conditional revalidation", async ({ request }) => {
  for (const path of ["/dashboard.html", "/data/childhood_cancer_test.txt"]) {
    const initial = await request.get(path);
    expect(initial.status(), path).toBe(200);
    expect(initial.headers()["cache-control"], path).toContain("max-age=300");
    const lastModified = initial.headers()["last-modified"];
    expect(lastModified, path).toBeTruthy();

    const cached = await request.get(path, {
      headers: { "If-Modified-Since": lastModified },
    });
    expect(cached.status(), path).toBe(304);
  }
});
