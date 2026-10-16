// @ts-check
const { test, expect } = require('@playwright/test');
const { DashboardPage } = require('./pages/DashboardPage');
const { MakerPage } = require('./pages/MakerPage');
const { CheckerPage } = require('./pages/CheckerPage');
const { VerifyPage } = require('./pages/VerifyPage');

test.describe('E2E Flow Sistem Taksasi Mutu Beras SNI 6128:2020 (POM Architecture)', () => {

  test('TC-E2E-01: Header, Legal Disclaimer & Tab Navigation', async ({ page }) => {
    const dashboard = new DashboardPage(page);
    await dashboard.goto();

    await expect(page).toHaveTitle(/Sistem Taksasi Mutu Beras Digital/i);
    await dashboard.verifyLegalDisclaimer();

    // Verifikasi navigasi 4 tab
    await dashboard.switchTab('maker');
    await dashboard.switchTab('checker');
    await dashboard.switchTab('certificates');
    await dashboard.switchTab('simulation');
  });

  test('TC-E2E-02: Kalkulator Mutu Beras SNI & Taksasi Harga (Maker Self-Assessment)', async ({ page }) => {
    const dashboard = new DashboardPage(page);
    const maker = new MakerPage(page);
    await dashboard.goto();

    // 1. Preset Premium Ideal
    await maker.applyPreset('premium');
    await expect(maker.inputKadarAir).toHaveValue('12.5');
    await expect(maker.inputButirPatah).toHaveValue('8');
    await expect(maker.inputButirMenir).toHaveValue('0.2');
    await expect(maker.inputBendaAsing).toHaveValue('0.005');

    await maker.btnSimSubmit.click();
    await expect(maker.resultContent).toBeVisible();
    await expect(maker.gradeTitle).toContainText('PREMIUM');
    await expect(maker.priceNet).toContainText('15.800');

    // 2. Preset Substandar Air
    await maker.applyPreset('substandar');
    await maker.btnSimSubmit.click();
    await expect(maker.gradeTitle).toContainText('SUBSTANDAR');
    await expect(maker.resultContent).toContainText('Penalti');
  });

  test('TC-E2E-03: Inspeksi Citra Computer Vision (CV Engine)', async ({ page }) => {
    const dashboard = new DashboardPage(page);
    const maker = new MakerPage(page);
    await dashboard.goto();

    await maker.runCvDemo();
    await maker.applyCvToForm();
  });

  test('TC-E2E-04: Maker Workflow - Pengajuan Batch Sampel Petani', async ({ page }) => {
    const dashboard = new DashboardPage(page);
    const maker = new MakerPage(page);
    await dashboard.goto();

    await dashboard.switchTab('maker');

    const testPetani = 'Petani E2E Test ' + Date.now();
    const testVarietas = 'Menthik Wangi ' + Math.floor(Math.random() * 1000);

    await maker.submitBatch({
      nama: testPetani,
      nik: '3311012304750001',
      kontak: '081299998888',
      varietas: testVarietas,
      tonase: 3500,
      asalLahan: 'Sawah Blok B, Sukoharjo',
      tanggalPanen: '2026-10-15',
    });

    await expect(maker.makerSubmissionsTbody).toContainText(testVarietas, { timeout: 10000 });
  });

  test('TC-E2E-05: Checker Workflow - Uji Lab & Penerbitan Lembar Taksasi (CoA)', async ({ page }) => {
    const dashboard = new DashboardPage(page);
    const checker = new CheckerPage(page);
    await dashboard.goto();

    await dashboard.switchTab('checker');
    await checker.openFirstPendingTest();

    await checker.verifyAndIssueCertificate({
      kadarAir: 13.2,
      butirPatah: 11.0,
      butirMenir: 0.3,
      bendaAsing: 0.007,
    });
  });

  test('TC-E2E-06: Public Verification & Privacy Protection (UU PDP No. 27/2022)', async ({ page }) => {
    const verify = new VerifyPage(page);
    await verify.goto();

    await expect(page).toHaveTitle(/Verifikasi/i);

    const res = await page.request.get('/api/certificates');
    const data = await res.json();
    expect(data.certificates).toBeDefined();

    if (data.certificates && data.certificates.length > 0) {
      const firstCert = data.certificates[0];
      const certNo = firstCert.nomor_taksasi || firstCert.nomor_sertifikat;

      await verify.verifyCertificate(certNo);
      await expect(verify.statusTitle).toContainText('LEMBAR TAKSASI SAH');

      const nikText = await verify.detPetaniNik.textContent();
      expect(nikText).toMatch(/\*+/); // Masked PII
    }
  });

  test('TC-E2E-07: Unhappy Path - Boundary & Invalid Input Handling', async ({ page }) => {
    const dashboard = new DashboardPage(page);
    const maker = new MakerPage(page);
    await dashboard.goto();

    // Browser HTML5 validation or application error handling on negative moisture
    await maker.runSimulation(-5.0, 10.0, 1.0, 0.01);
    // Since input has min="0", either browser validation or response error prevents invalid state
    const validity = await maker.inputKadarAir.evaluate((el) => /** @type {HTMLInputElement} */ (el).checkValidity());
    expect(validity).toBe(false);
  });

  test('TC-E2E-08: Unhappy Path - Non-Existent Certificate Lookup', async ({ page }) => {
    const verify = new VerifyPage(page);
    await verify.goto();

    await verify.verifyCertificate('TKS-99999999-NOTFOUND');
    await expect(verify.statusTitle).toContainText('TIDAK TERDAFTAR');
    await expect(verify.statusBanner).toHaveClass(/not_found/);
  });

  test('TC-E2E-09: Unhappy Path - Anti-Fraud Tampered HMAC Signature Detection', async ({ page }) => {
    const verify = new VerifyPage(page);
    const res = await page.request.get('/api/certificates');
    const data = await res.json();

    if (data.certificates && data.certificates.length > 0) {
      const cert = data.certificates[0];
      const certNo = cert.nomor_taksasi || cert.nomor_sertifikat;
      const fakeSig = 'deadbeef0000111122223333';

      await verify.verifyDirectUrl(certNo, fakeSig);
      await expect(verify.statusTitle).toContainText('DIMANIPULASI');
      await expect(verify.statusBanner).toHaveClass(/tampered/);
    }
  });

});
