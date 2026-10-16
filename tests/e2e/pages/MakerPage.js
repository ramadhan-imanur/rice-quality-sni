// @ts-check
const { expect } = require('@playwright/test');

class MakerPage {
  /**
   * @param {import('@playwright/test').Page} page
   */
  constructor(page) {
    this.page = page;

    // Simulation & Kalkulator
    this.inputKadarAir = page.locator('#sim_kadar_air');
    this.inputButirPatah = page.locator('#sim_butir_patah');
    this.inputButirMenir = page.locator('#sim_butir_menir');
    this.inputBendaAsing = page.locator('#sim_benda_asing');
    this.btnSimSubmit = page.locator('#btn-sim-submit');
    this.resultContent = page.locator('#sim-result-content');
    this.gradeTitle = page.locator('#sim-grade-title');
    this.priceNet = page.locator('#sim-price-net');

    // Preset buttons
    this.presetPremium = page.locator('button[data-preset="premium_ideal"]');
    this.presetSubstandar = page.locator('button[data-preset="substandar_air"]');

    // Computer Vision
    this.btnCvDemo = page.locator('#btn-cv-demo');
    this.cvResultBox = page.locator('#cv-result-box');
    this.cvStatTotal = page.locator('#cv-stat-total');
    this.btnApplyCv = page.locator('#btn-apply-cv');

    // Maker Form Pengajuan Batch
    this.formMaker = page.locator('#maker-batch-form');
    this.inputNama = page.locator('#m_petani_nama');
    this.inputNik = page.locator('#m_petani_nik');
    this.inputKontak = page.locator('#m_kontak');
    this.inputVarietas = page.locator('#m_varietas');
    this.inputTonase = page.locator('#m_tonase');
    this.inputAsalLahan = page.locator('#m_asal_lahan');
    this.inputTanggalPanen = page.locator('#m_tanggal_panen');
    this.btnSubmitBatch = page.locator('#maker-batch-form button[type="submit"]');
    this.makerSubmissionsTbody = page.locator('#maker-submissions-tbody');
  }

  async applyPreset(presetType) {
    if (presetType === 'premium') {
      await this.presetPremium.click();
    } else if (presetType === 'substandar') {
      await this.presetSubstandar.click();
    }
  }

  async runSimulation(ka, bp, mn, ba) {
    if (ka !== undefined) await this.inputKadarAir.fill(String(ka));
    if (bp !== undefined) await this.inputButirPatah.fill(String(bp));
    if (mn !== undefined) await this.inputButirMenir.fill(String(mn));
    if (ba !== undefined) await this.inputBendaAsing.fill(String(ba));
    await this.btnSimSubmit.click();
  }

  async runCvDemo() {
    await this.btnCvDemo.click();
    await expect(this.cvResultBox).toBeVisible({ timeout: 10000 });
    await expect(this.cvStatTotal).not.toHaveText('0');
  }

  async applyCvToForm() {
    await this.btnApplyCv.click();
    const ka = await this.inputKadarAir.inputValue();
    const bp = await this.inputButirPatah.inputValue();
    expect(parseFloat(ka)).toBeGreaterThan(0);
    expect(parseFloat(bp)).toBeGreaterThan(0);
  }

  async submitBatch(data) {
    await this.inputNama.fill(data.nama);
    await this.inputNik.fill(data.nik);
    await this.inputKontak.fill(data.kontak);
    await this.inputVarietas.fill(data.varietas);
    await this.inputTonase.fill(String(data.tonase));
    await this.inputAsalLahan.fill(data.asalLahan);
    await this.inputTanggalPanen.fill(data.tanggalPanen);

    this.page.once('dialog', async (dialog) => {
      expect(dialog.message()).toContain('berhasil');
      await dialog.accept();
    });

    await this.btnSubmitBatch.click();
  }
}

module.exports = { MakerPage };
