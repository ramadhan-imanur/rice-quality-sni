// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('E2E Flow Sistem Taksasi Mutu Beras SNI 6128:2020', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to base URL
    await page.goto('/');
  });

  test('TC-E2E-01: Header, Legal Disclaimer & Tab Navigation', async ({ page }) => {
    // 1. Periksa judul dokumen
    await expect(page).toHaveTitle(/Sistem Taksasi Mutu Beras Digital/i);

    // 2. Periksa Banner Disclaimer Non-Sertifikat KAN (UU No. 20/2014 & KAN compliance)
    const disclaimerBanner = page.locator('.sim-alert-banner');
    await expect(disclaimerBanner).toBeVisible();
    await expect(disclaimerBanner).toContainText(/Bukan Sertifikat KAN/i);

    // 3. Verifikasi Keberadaan 4 Tab Navigasi
    const tabs = page.locator('.tab-btn');
    await expect(tabs).toHaveCount(4);
    await expect(tabs.nth(0)).toContainText('Simulasi & Kamera CV');
    await expect(tabs.nth(1)).toContainText('Pengajuan Batch Petani');
    await expect(tabs.nth(2)).toContainText('Pengujian Lab Analis');
    await expect(tabs.nth(3)).toContainText('Arsip Lembar Taksasi');

    // 4. Uji pergantian tab aktif
    await tabs.nth(1).click();
    await expect(page.locator('#tab-maker')).toHaveClass(/active/);
    await tabs.nth(2).click();
    await expect(page.locator('#tab-checker')).toHaveClass(/active/);
    await tabs.nth(3).click();
    await expect(page.locator('#tab-certificates')).toHaveClass(/active/);
    await tabs.nth(0).click();
    await expect(page.locator('#tab-simulation')).toHaveClass(/active/);
  });

  test('TC-E2E-02: Kalkulator Mutu Beras SNI & Taksasi Harga (Maker Self-Assessment)', async ({ page }) => {
    // 1. Uji tombol preset Premium Ideal
    const btnPresetPremium = page.locator('button[data-preset="premium_ideal"]');
    await btnPresetPremium.click();

    // Verifikasi input otomatis terisi (Preset Premium Ideal: Kadar Air 12.5%, Patah 8.0%, Menir 0.2%, Kotoran 0.005%)
    await expect(page.locator('#sim_kadar_air')).toHaveValue('12.5');
    await expect(page.locator('#sim_butir_patah')).toHaveValue('8');
    await expect(page.locator('#sim_butir_menir')).toHaveValue('0.2');
    await expect(page.locator('#sim_benda_asing')).toHaveValue('0.005');

    // 2. Klik Hitung Taksasi Mutu & Harga
    await page.locator('#btn-sim-submit').click();

    // 3. Verifikasi Hasil Muncul
    const resultContent = page.locator('#sim-result-content');
    await expect(resultContent).toBeVisible();
    await expect(page.locator('#sim-grade-title')).toContainText('PREMIUM');
    await expect(page.locator('#sim-price-net')).toContainText('15.800');

    // 4. Uji Kasus Substandar Basah
    const btnPresetSub = page.locator('button[data-preset="substandar_air"]');
    await btnPresetSub.click();
    await page.locator('#btn-sim-submit').click();

    await expect(page.locator('#sim-grade-title')).toContainText('SUBSTANDAR');
    await expect(page.locator('#sim-result-content')).toContainText('Penalti');
  });

  test('TC-E2E-03: Inspeksi Citra Computer Vision (CV Engine)', async ({ page }) => {
    // 1. Klik Tombol Coba Sampel Demo
    const btnDemo = page.locator('#btn-cv-demo');
    await expect(btnDemo).toBeVisible();
    await btnDemo.click();

    // 2. Verifikasi Hasil Analisis Citra Muncul
    const cvResultBox = page.locator('#cv-result-box');
    await expect(cvResultBox).toBeVisible({ timeout: 10000 });

    // Periksa metrik butir terdeteksi
    const statTotal = page.locator('#cv-stat-total');
    await expect(statTotal).not.toHaveText('0');

    // 3. Terapkan Hasil ke Formulir
    const btnApply = page.locator('#btn-apply-cv');
    await expect(btnApply).toBeVisible();
    await btnApply.click();

    // Verifikasi parameter fisik formulir terisi nilai hasil deteksi CV
    const kadarAir = await page.locator('#sim_kadar_air').inputValue();
    const butirPatah = await page.locator('#sim_butir_patah').inputValue();
    expect(parseFloat(kadarAir)).toBeGreaterThan(0);
    expect(parseFloat(butirPatah)).toBeGreaterThan(0);
  });

  test('TC-E2E-04: Maker Workflow - Pengajuan Batch Sampel Petani', async ({ page }) => {
    // 1. Pindah ke Tab Pengajuan Batch
    await page.locator('.tab-btn[data-tab="tab-maker"]').click();

    // 2. Isi Formulir Pengajuan
    const testPetani = 'Petani E2E Test ' + Date.now();
    const testVarietas = 'Menthik Wangi ' + Math.floor(Math.random() * 1000);
    await page.locator('#m_petani_nama').fill(testPetani);
    await page.locator('#m_petani_nik').fill('3311012304750001');
    await page.locator('#m_kontak').fill('081299998888');
    await page.locator('#m_varietas').fill(testVarietas);
    await page.locator('#m_tonase').fill('3500');
    await page.locator('#m_asal_lahan').fill('Sawah Blok B, Sukoharjo');
    await page.locator('#m_tanggal_panen').fill('2026-10-15');

    // Listen dialog/alert
    page.once('dialog', async (dialog) => {
      expect(dialog.message()).toContain('berhasil');
      await dialog.accept();
    });

    // 3. Submit Pengajuan Batch
    await page.locator('#maker-batch-form button[type="submit"]').click();

    // 4. Verifikasi muncul di tabel status pengajuan berdasarkan varietas yang didaftarkan
    const tbody = page.locator('#maker-submissions-tbody');
    await expect(tbody).toContainText(testVarietas, { timeout: 10000 });
  });

  test('TC-E2E-05: Checker Workflow - Uji Lab & Penerbitan Lembar Taksasi (CoA)', async ({ page }) => {
    // 1. Pindah ke Tab Checker
    await page.locator('.tab-btn[data-tab="tab-checker"]').click();

    // 2. Tunggu tabel antrean pending
    const testButtons = page.locator('.btn-open-test');
    await expect(testButtons.first()).toBeVisible({ timeout: 10000 });

    // 3. Buka Modal Uji Lab pada batch pertama
    await testButtons.first().click();
    const modal = page.locator('#modal-lab-test');
    await expect(modal).toBeVisible();

    // 4. Masukkan parameter uji lab terkalibrasi
    await page.locator('#lab_kadar_air').fill('13.2');
    await page.locator('#lab_butir_patah').fill('11.0');
    await page.locator('#lab_butir_menir').fill('0.3');
    await page.locator('#lab_benda_asing').fill('0.007');

    // Listen dialog alert
    page.once('dialog', async (dialog) => {
      expect(dialog.message()).toContain('Berhasil Diterbitkan');
      await dialog.accept();
    });

    // 5. Submit verifikasi lab
    await page.locator('#lab-test-form button[type="submit"]').click();

    // 6. Verifikasi otomatis beralih ke Tab Arsip Sertifikat
    await expect(page.locator('#tab-certificates')).toHaveClass(/active/, { timeout: 10000 });
    const certTbody = page.locator('#certificates-tbody');
    await expect(certTbody).toBeVisible();
  });

  test('TC-E2E-06: Public Verification & Privacy Protection (UU PDP No. 27/2022)', async ({ page }) => {
    // 1. Buka Halaman Verifikasi Publik
    await page.goto('/verify.html');
    await expect(page).toHaveTitle(/Verifikasi/i);

    // 2. Cek elemen input pencarian sertifikat
    const searchInput = page.locator('#cert_query');
    await expect(searchInput).toBeVisible();

    // 3. Uji sertifikat publik via API list untuk mengambil nomor taksasi pertama
    const res = await page.request.get('/api/certificates');
    const data = await res.json();
    expect(data.certificates).toBeDefined();

    if (data.certificates && data.certificates.length > 0) {
      const firstCert = data.certificates[0];
      const certNo = firstCert.nomor_taksasi || firstCert.nomor_sertifikat;

      // Masukkan nomor taksasi ke input verifikasi
      await searchInput.fill(certNo);
      await page.locator('#verify-form button[type="submit"]').click();

      // Verifikasi Kartu Hasil Verifikasi Muncul
      const resultBox = page.locator('#verify-result');
      await expect(resultBox).toBeVisible({ timeout: 10000 });
      await expect(page.locator('#status-title')).toContainText('LEMBAR TAKSASI SAH');

      // Verifikasi PII NIK telah disensor/dimasking (UU PDP No. 27/2022)
      const nikText = await page.locator('#det-petani-nik').textContent();
      expect(nikText).toMatch(/\*+/); // Harus mengandung asteris masking seperti 331101********01
    }
  });

});
