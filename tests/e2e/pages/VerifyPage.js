// @ts-check
const { expect } = require('@playwright/test');

class VerifyPage {
  /**
   * @param {import('@playwright/test').Page} page
   */
  constructor(page) {
    this.page = page;
    this.inputQuery = page.locator('#cert_query');
    this.btnSubmit = page.locator('#verify-form button[type="submit"]');
    this.resultBox = page.locator('#verify-result');
    this.statusBanner = page.locator('#status-banner');
    this.statusTitle = page.locator('#status-title');
    this.statusDesc = page.locator('#status-desc');
    this.detPetaniNik = page.locator('#det-petani-nik');
  }

  async goto() {
    await this.page.goto('/verify.html');
  }

  async verifyCertificate(certId) {
    await this.inputQuery.fill(certId);
    await this.btnSubmit.click();
    await expect(this.resultBox).toBeVisible({ timeout: 10000 });
  }

  async verifyDirectUrl(certId, sig) {
    let url = `/verify.html?id=${encodeURIComponent(certId)}`;
    if (sig) {
      url += `&sig=${encodeURIComponent(sig)}`;
    }
    await this.page.goto(url);
    await expect(this.resultBox).toBeVisible({ timeout: 10000 });
  }
}

module.exports = { VerifyPage };
