// @ts-check
const { expect } = require('@playwright/test');

class CheckerPage {
  /**
   * @param {import('@playwright/test').Page} page
   */
  constructor(page) {
    this.page = page;
    this.testButtons = page.locator('.btn-open-test');
    this.modalLab = page.locator('#modal-lab-test');
    this.inputKadarAir = page.locator('#lab_kadar_air');
    this.inputButirPatah = page.locator('#lab_butir_patah');
    this.inputButirMenir = page.locator('#lab_butir_menir');
    this.inputBendaAsing = page.locator('#lab_benda_asing');
    this.btnSubmitVerification = page.locator('#lab-test-form button[type="submit"]');
    this.tabCertificates = page.locator('#tab-certificates');
    this.certTbody = page.locator('#certificates-tbody');
  }

  async openFirstPendingTest() {
    await expect(this.testButtons.first()).toBeVisible({ timeout: 10000 });
    await this.testButtons.first().click();
    await expect(this.modalLab).toBeVisible();
  }

  async verifyAndIssueCertificate(params) {
    await this.inputKadarAir.fill(String(params.kadarAir));
    await this.inputButirPatah.fill(String(params.butirPatah));
    await this.inputButirMenir.fill(String(params.butirMenir));
    await this.inputBendaAsing.fill(String(params.bendaAsing));

    this.page.once('dialog', async (dialog) => {
      expect(dialog.message()).toContain('Berhasil Diterbitkan');
      await dialog.accept();
    });

    await this.btnSubmitVerification.click();
    await expect(this.tabCertificates).toHaveClass(/active/, { timeout: 10000 });
    await expect(this.certTbody).toBeVisible();
  }
}

module.exports = { CheckerPage };
