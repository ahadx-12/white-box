import type { Page } from "@playwright/test";
import { expect, test } from "@playwright/test";

const selectPack = async (page: Page, packName: string) => {
  await page.getByTestId("pack-selector").selectOption(packName);
};

const sendMessage = async (page: Page, message: string) => {
  await page.getByTestId("chat-input").fill(message);
  await page.getByTestId("send-button").click();
};

test("sync verification shows proof", async ({ page }) => {
  await page.goto("/");
  await selectPack(page, "general");
  await sendMessage(page, "What is 2+2?");

  await expect(page.getByTestId("proof-panel")).toContainText("Proof ID");
  await expect(page.getByTestId("proof-summary")).toBeVisible();
  await expect(page.getByTestId("message-assistant").last()).toContainText(
    /.+/,
  );
});

test("async verification resolves job", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("mode-async").click();
  await selectPack(page, "general");

  await sendMessage(page, "Explain why A kills B differs from B kills A");

  await expect(page.getByTestId("message-assistant").last()).toContainText(
    "Job",
  );
  await expect(page.getByTestId("proof-panel")).toContainText("Proof ID", {
    timeout: 60_000,
  });
  await expect(page.getByTestId("proof-summary")).toBeVisible();
});
