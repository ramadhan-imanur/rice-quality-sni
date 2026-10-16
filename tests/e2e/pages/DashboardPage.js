// @ts-check
const { expect } = require('@playwright/test');

class DashboardPage {
  /**
   * @param {import('@playwright/test').Page} page
   */
  constructor(page) {
    this.page = page;
    this.disclaimerBanner = page.locator('.sim-alert-banner');
    this.tabs = page.locator('.tab-btn');
    this.tabSimulation = page.locator('.tab-btn[data-tab="tab-simulation"]');
    this.tabMaker = page.locator('.tab-btn[data-tab="tab-maker"]');
    this.tabChecker = page.locator('.tab-btn[data-tab="tab-checker"]');
    this.tabCertificates = page.locator('.tab-btn[data-tab="tab-certificates"]');

    this.contentSimulation = page.locator('#tab-simulation');
    this.contentMaker = page.locator('#tab-maker');
    this.contentChecker = page.locator('#tab-checker');
    this.contentCertificates = page.locator('#tab-certificates');
  }

  async goto() {
    await this.page.goto('/');
  }

  async verifyLegalDisclaimer() {
    await expect(this.disclaimerBanner).toBeVisible();
    await expect(this.disclaimerBanner).toContainText(/Bukan Sertifikat KAN/i);
  }

  async switchTab(tabName) {
    switch (tabName) {
      case 'simulation':
        await this.tabSimulation.click();
        await expect(this.contentSimulation).toHaveClass(/active/);
        break;
      case 'maker':
        await this.tabMaker.click();
        await expect(this.contentMaker).toHaveClass(/active/);
        break;
      case 'checker':
        await this.tabChecker.click();
        await expect(this.contentChecker).toHaveClass(/active/);
        break;
      case 'certificates':
        await this.tabCertificates.click();
        await expect(this.contentCertificates).toHaveClass(/active/);
        break;
      default:
        throw new Error(`Tab "${tabName}" tidak dikenal.`);
    }
  }
}

module.exports = { DashboardPage };
