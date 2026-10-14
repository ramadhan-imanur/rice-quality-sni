/**
 * app.js — Logika Penilai Mutu Beras Deterministik SNI 6128:2020
 * =============================================================
 * Berjalan 100% luring di peramban lokal (offline-first, zero compute cost).
 * 
 * Penulis: Ramadhaan Imanur Rochima (NIM M0124015) — S1 Matematika FMIPA UNS
 */

(function () {
  "use strict";

  // =========================================================================
  // KONSTANTA STANDAR SNI 6128:2020 & BAPANAS NO. 67/2024
  // =========================================================================

  const KELAS_MUTU_SNI = [
    {
      nama_kelas: "PREMIUM",
      label: "Premium",
      kadar_air_maks: 14.0,
      butir_patah_maks: 15.0,
      butir_menir_maks: 0.5,
      benda_asing_maks: 0.01,
      harga_dasar: 15800,
      deskripsi: "Memenuhi seluruh standar baku tertinggi kelas Mutu Premium SNI 6128:2020.",
    },
    {
      nama_kelas: "MEDIUM_I",
      label: "Medium I",
      kadar_air_maks: 14.0,
      butir_patah_maks: 20.0,
      butir_menir_maks: 2.0,
      benda_asing_maks: 0.02,
      harga_dasar: 13500,
      deskripsi: "Memenuhi standar baku kelas Mutu Medium I SNI 6128:2020.",
    },
    {
      nama_kelas: "MEDIUM_II",
      label: "Medium II",
      kadar_air_maks: 14.0,
      butir_patah_maks: 25.0,
      butir_menir_maks: 5.0,
      benda_asing_maks: 0.05,
      harga_dasar: 13500,
      deskripsi: "Memenuhi standar baku kelas Mutu Medium II SNI 6128:2020.",
    },
  ];

  const KELAS_SUBSTANDAR = {
    nama_kelas: "SUBSTANDAR",
    label: "Substandar",
    kadar_air_maks: 99.0,
    butir_patah_maks: 100.0,
    butir_menir_maks: 100.0,
    benda_asing_maks: 100.0,
    harga_dasar: 11500,
    deskripsi: "Melampaui batas toleransi mutu fisik Medium II atau berkadar air tinggi (> 14%). Dikenai penalti pengeringan.",
  };

  const BIAYA_PENGERINGAN_PER_PERSEN = 150; // Rp/kg per 1% kadar air > 14%
  const FAKTOR_PENYUSUTAN_PER_PERSEN = 0.015; // 1.5% dari harga dasar per 1% kelebihan air

  const RENTANG_VALIDASI = {
    kadar_air: { min: 0.0, max: 40.0, label: "Kadar Air" },
    butir_patah: { min: 0.0, max: 100.0, label: "Butir Patah" },
    butir_menir: { min: 0.0, max: 100.0, label: "Butir Menir" },
    benda_asing: { min: 0.0, max: 10.0, label: "Benda Asing" },
  };

  const PRESETS = {
    premium_ideal: {
      id: "Sampel Premium Super (Ideal)",
      ka: 12.5,
      bp: 8.0,
      mn: 0.2,
      ba: 0.005,
    },
    premium_boundary: {
      id: "Sampel Ambang Batas Premium",
      ka: 14.0,
      bp: 15.0,
      mn: 0.5,
      ba: 0.01,
    },
    medium_1: {
      id: "Sampel Medium I Standar",
      ka: 13.8,
      bp: 18.0,
      mn: 1.5,
      ba: 0.015,
    },
    medium_2: {
      id: "Sampel Medium II Pasar",
      ka: 14.0,
      bp: 23.5,
      mn: 3.8,
      ba: 0.035,
    },
    substandar_air: {
      id: "Sampel Beras Basah Sawah",
      ka: 16.5,
      bp: 18.0,
      mn: 1.2,
      ba: 0.015,
    },
  };

  // State aplikasi
  let currentResult = null;
  const STORAGE_KEY = "sni_rice_quality_history_v1";

  // =========================================================================
  // LOGIKA DETERMINISTIK EVALUASI MUTU & HARGA
  // =========================================================================

  function evaluate(ka, bp, mn, ba, sampleId, storeName) {
    // 1. Klasifikasi Mutu O(1)
    let selectedClass = KELAS_SUBSTANDAR;
    for (const k of KELAS_MUTU_SNI) {
      if (
        ka <= k.kadar_air_maks &&
        bp <= k.butir_patah_maks &&
        mn <= k.butir_menir_maks &&
        ba <= k.benda_asing_maks
      ) {
        selectedClass = k;
        break;
      }
    }

    // 2. Kalkulasi Penalti Harga Bapanas No. 67/2024
    const hargaDasar = selectedClass.harga_dasar;
    const kelebihanAir = Math.max(0, ka - 14.0);
    const penaltiPengeringan = Math.round(kelebihanAir * BIAYA_PENGERINGAN_PER_PERSEN);
    const potonganPenyusutan = Math.round(kelebihanAir * FAKTOR_PENYUSUTAN_PER_PERSEN * hargaDasar);
    const totalPotongan = penaltiPengeringan + potonganPenyusutan;
    const hargaBersih = Math.max(0, hargaDasar - totalPotongan);

    // 3. Nomor Sertifikat Unik
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const dateStr = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`;
    const randCode = Math.random().toString(36).substring(2, 8).toUpperCase();
    const certNumber = `SNI-${dateStr}-${randCode}`;

    const dateFormatted = now.toLocaleDateString("id-ID", {
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

    return {
      nomor_sertifikat: certNumber,
      sample_id: sampleId || `Sampel-${randCode}`,
      store_name: storeName ? storeName.trim() : "",
      tanggal_uji: `${dateFormatted} WIB`,
      tanggal_iso: now.toISOString(),
      parameter_uji: {
        kadar_air: ka,
        butir_patah: bp,
        butir_menir: mn,
        benda_asing: ba,
      },
      klasifikasi: {
        nama_kelas: selectedClass.nama_kelas,
        label_mutu: selectedClass.label,
        deskripsi: selectedClass.deskripsi,
      },
      rekomendasi_harga: {
        harga_dasar: hargaDasar,
        kelebihan_kadar_air: Number(kelebihanAir.toFixed(2)),
        penalti_pengeringan: penaltiPengeringan,
        potongan_penyusutan: potonganPenyusutan,
        total_potongan: totalPotongan,
        harga_bersih: hargaBersih,
      },
    };
  }

  // =========================================================================
  // FORMATTING HELPERS
  // =========================================================================

  function formatRupiah(num) {
    return "Rp " + Number(num).toLocaleString("id-ID");
  }

  // =========================================================================
  // DOM UPDATES & RENDERING
  // =========================================================================

  function renderResult(result) {
    currentResult = result;

    const placeholder = document.getElementById("result-placeholder");
    const content = document.getElementById("result-content");
    const certSerial = document.getElementById("res-cert-number");

    placeholder.style.display = "none";
    content.style.display = "block";
    certSerial.textContent = result.nomor_sertifikat;

    // Grade Banner
    const banner = document.getElementById("grade-banner");
    const gradeTitle = document.getElementById("res-grade-title");
    const gradeDesc = document.getElementById("res-grade-desc");
    const gradeIcon = document.getElementById("grade-icon");

    banner.className = "grade-banner";
    const k = result.klasifikasi.nama_kelas;
    if (k === "PREMIUM") {
      banner.classList.add("grade-premium");
      gradeIcon.textContent = "★";
    } else if (k === "MEDIUM_I") {
      banner.classList.add("grade-medium-1");
      gradeIcon.textContent = "I";
    } else if (k === "MEDIUM_II") {
      banner.classList.add("grade-medium-2");
      gradeIcon.textContent = "II";
    } else {
      banner.classList.add("grade-substandar");
      gradeIcon.textContent = "!";
    }

    gradeTitle.textContent = result.klasifikasi.label_mutu.toUpperCase();
    gradeDesc.textContent = result.klasifikasi.deskripsi;

    // Parameter Summary Grid
    const paramGrid = document.getElementById("res-param-grid");
    const p = result.parameter_uji;
    paramGrid.innerHTML = `
      <div class="param-chip ${p.kadar_air > 14.0 ? "is-deviant" : ""}">
        <span class="chip-label">Kadar Air:</span>
        <span class="chip-val ${p.kadar_air > 14.0 ? "text-red" : ""}">${p.kadar_air.toFixed(2)}%</span>
      </div>
      <div class="param-chip ${p.butir_patah > 25.0 ? "is-deviant" : ""}">
        <span class="chip-label">Butir Patah:</span>
        <span class="chip-val ${p.butir_patah > 25.0 ? "text-red" : ""}">${p.butir_patah.toFixed(2)}%</span>
      </div>
      <div class="param-chip ${p.butir_menir > 5.0 ? "is-deviant" : ""}">
        <span class="chip-label">Butir Menir:</span>
        <span class="chip-val ${p.butir_menir > 5.0 ? "text-red" : ""}">${p.butir_menir.toFixed(2)}%</span>
      </div>
      <div class="param-chip ${p.benda_asing > 0.05 ? "is-deviant" : ""}">
        <span class="chip-label">Benda Asing:</span>
        <span class="chip-val ${p.benda_asing > 0.05 ? "text-red" : ""}">${p.benda_asing.toFixed(4)}%</span>
      </div>
    `;

    // Pricing Box
    const h = result.rekomendasi_harga;
    document.getElementById("res-price-base").textContent = `${formatRupiah(h.harga_dasar)} / kg`;
    document.getElementById("res-drying-sub").textContent = `(Kelebihan air ${h.kelebihan_kadar_air}%)`;
    document.getElementById("res-price-drying").textContent = `- ${formatRupiah(h.penalti_pengeringan)} / kg`;
    document.getElementById("res-price-shrinkage").textContent = `- ${formatRupiah(h.potongan_penyusutan)} / kg`;
    document.getElementById("res-price-net").innerHTML = `<strong>${formatRupiah(h.harga_bersih)} / kg</strong>`;

    // Simulasi 5 Ton (5.000 kg)
    const total5Ton = h.harga_bersih * 5000;
    const simText = document.getElementById("res-sim-text");
    simText.textContent = `Total nilai transaksi wajar: ${formatRupiah(total5Ton)} untuk muatan 5.000 kg (Menghindari taksiran borongan sepihak tengkulak).`;

    // Sinkronisasi ke Tampilan Cetak A4
    syncPrintCertificate(result);
  }

  function syncPrintCertificate(result) {
    document.getElementById("cert-print-serial").textContent = `NO: ${result.nomor_sertifikat}`;
    document.getElementById("cert-print-id").textContent = result.sample_id;
    document.getElementById("cert-print-date").textContent = result.tanggal_uji;

    const storeKopEl = document.getElementById("cert-print-store-name");
    if (storeKopEl) {
      storeKopEl.textContent = result.store_name ? result.store_name.toUpperCase() : "UNIT VERIFIKASI MUTU BERAS RAKYAT";
    }

    const p = result.parameter_uji;
    const tbody = document.getElementById("cert-print-params-tbody");
    tbody.innerHTML = `
      <tr>
        <td style="text-align: center;">1</td>
        <td>Kadar Air</td>
        <td style="text-align: center; font-weight: bold;">${p.kadar_air.toFixed(2)}%</td>
        <td style="text-align: center;">&le; 14.00%</td>
        <td style="text-align: center;">&le; 14.00%</td>
        <td style="text-align: center;">&le; 14.00%</td>
        <td style="text-align: center;">${p.kadar_air <= 14.0 ? "Memenuhi Standar" : "Kelebihan Air (Penalti)"}</td>
      </tr>
      <tr>
        <td style="text-align: center;">2</td>
        <td>Butir Patah</td>
        <td style="text-align: center; font-weight: bold;">${p.butir_patah.toFixed(2)}%</td>
        <td style="text-align: center;">&le; 15.00%</td>
        <td style="text-align: center;">&le; 20.00%</td>
        <td style="text-align: center;">&le; 25.00%</td>
        <td style="text-align: center;">${p.butir_patah <= 25.0 ? "Sesuai Toleransi" : "Melampaui Ambang"}</td>
      </tr>
      <tr>
        <td style="text-align: center;">3</td>
        <td>Butir Menir</td>
        <td style="text-align: center; font-weight: bold;">${p.butir_menir.toFixed(2)}%</td>
        <td style="text-align: center;">&le; 0.50%</td>
        <td style="text-align: center;">&le; 2.00%</td>
        <td style="text-align: center;">&le; 5.00%</td>
        <td style="text-align: center;">${p.butir_menir <= 5.0 ? "Sesuai Toleransi" : "Melampaui Ambang"}</td>
      </tr>
      <tr>
        <td style="text-align: center;">4</td>
        <td>Benda Asing / Kotoran</td>
        <td style="text-align: center; font-weight: bold;">${p.benda_asing.toFixed(4)}%</td>
        <td style="text-align: center;">&le; 0.0100%</td>
        <td style="text-align: center;">&le; 0.0200%</td>
        <td style="text-align: center;">&le; 0.0500%</td>
        <td style="text-align: center;">${p.benda_asing <= 0.05 ? "Sesuai Toleransi" : "Melampaui Ambang"}</td>
      </tr>
    `;

    document.getElementById("cert-print-grade").textContent = `MUTU ${result.klasifikasi.label_mutu.toUpperCase()}`;
    document.getElementById("cert-print-statement").textContent = result.klasifikasi.deskripsi;

    const h = result.rekomendasi_harga;
    document.getElementById("cert-print-base-price").textContent = `${formatRupiah(h.harga_dasar)} / kg`;
    document.getElementById("cert-print-drying-pen").textContent = `- ${formatRupiah(h.penalti_pengeringan)} / kg`;
    document.getElementById("cert-print-shrink-pen").textContent = `- ${formatRupiah(h.potongan_penyusutan)} / kg`;
    document.getElementById("cert-print-net-price").innerHTML = `<strong>${formatRupiah(h.harga_bersih)} / kg</strong>`;

    const now = new Date();
    document.getElementById("cert-print-sign-loc").textContent = `Surakarta, ${now.toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" })}`;
  }

  // =========================================================================
  // MANAJEMEN RIWAYAT PENGUJIAN LOKAL (FR-07)
  // =========================================================================

  function getHistory() {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      return [];
    }
  }

  function saveToHistory(result) {
    const history = getHistory();
    // Hindari duplikat nomor sertifikat
    const exists = history.some((item) => item.nomor_sertifikat === result.nomor_sertifikat);
    if (!exists) {
      history.unshift(result);
      if (history.length > 50) history.pop(); // simpan maksimal 50 riwayat
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    }
    renderHistoryTable();
  }

  function renderHistoryTable() {
    const history = getHistory();
    const tbody = document.getElementById("history-tbody");
    if (!tbody) return;

    if (history.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align: center; color: #94a3b8; padding: 1.5rem;">
            Belum ada riwayat pengujian tersimpan di peramban ini.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = history
      .map((item, idx) => {
        const p = item.parameter_uji;
        const k = item.klasifikasi.nama_kelas;
        const h = item.rekomendasi_harga.harga_bersih;
        const tgl = item.tanggal_iso ? item.tanggal_iso.substring(0, 16).replace("T", " ") : "-";
        return `
          <tr>
            <td>${tgl}</td>
            <td><code>${item.nomor_sertifikat}</code></td>
            <td><strong>${escapeHtml(item.sample_id)}</strong></td>
            <td>${p.kadar_air.toFixed(1)}%</td>
            <td>${p.butir_patah.toFixed(1)}%</td>
            <td><span class="badge-pill ${k}">${item.klasifikasi.label_mutu}</span></td>
            <td><strong>${formatRupiah(h)}</strong></td>
            <td>
              <button type="button" class="btn btn-sm btn-outline btn-inspect" data-idx="${idx}">Muat</button>
            </td>
          </tr>
        `;
      })
      .join("");

    // Tambahkan event listener untuk tombol muat
    document.querySelectorAll(".btn-inspect").forEach((btn) => {
      btn.addEventListener("click", function () {
        const idx = Number(this.dataset.idx);
        const item = history[idx];
        if (item) {
          // Isi formulir
          document.getElementById("sample_id").value = item.sample_id;
          document.getElementById("kadar_air").value = item.parameter_uji.kadar_air;
          document.getElementById("butir_patah").value = item.parameter_uji.butir_patah;
          document.getElementById("butir_menir").value = item.parameter_uji.butir_menir;
          document.getElementById("benda_asing").value = item.parameter_uji.benda_asing;
          renderResult(item);
          window.scrollTo({ top: 0, behavior: "smooth" });
        }
      });
    });
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function exportHistoryJSON() {
    const history = getHistory();
    if (history.length === 0) {
      alert("Belum ada data riwayat untuk diekspor.");
      return;
    }
    const blob = new Blob([JSON.stringify(history, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `lab_samples_export_${new Date().toISOString().substring(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // =========================================================================
  // INISIALISASI & EVENT LISTENERS
  // =========================================================================

  document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("quality-form");
    const btnReset = document.getElementById("btn-reset");
    const btnPrint = document.getElementById("btn-print-cert");
    const btnSaveLog = document.getElementById("btn-save-log");
    const btnExport = document.getElementById("btn-export-json");
    const btnClear = document.getElementById("btn-clear-history");

    // Tangani Preset Buttons
    document.querySelectorAll(".btn-chip").forEach((chip) => {
      chip.addEventListener("click", function () {
        const presetKey = this.dataset.preset;
        const p = PRESETS[presetKey];
        if (p) {
          document.getElementById("sample_id").value = p.id;
          document.getElementById("kadar_air").value = p.ka;
          document.getElementById("butir_patah").value = p.bp;
          document.getElementById("butir_menir").value = p.mn;
          document.getElementById("benda_asing").value = p.ba;
          // Bersihkan galat
          clearErrors();
          // Evaluasi instan
          const storeName = document.getElementById("store_name") ? document.getElementById("store_name").value.trim() : "";
          const res = evaluate(p.ka, p.bp, p.mn, p.ba, p.id, storeName);
          renderResult(res);
        }
      });
    });

    // Validasi & Submit
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      clearErrors();

      const storeName = document.getElementById("store_name") ? document.getElementById("store_name").value.trim() : "";
      const sampleId = document.getElementById("sample_id").value.trim();
      const kaVal = document.getElementById("kadar_air").value;
      const bpVal = document.getElementById("butir_patah").value;
      const mnVal = document.getElementById("butir_menir").value;
      const baVal = document.getElementById("benda_asing").value;

      let valid = true;

      function checkField(id, val, config) {
        const errEl = document.getElementById(`err-${id}`);
        if (val === "" || isNaN(val)) {
          errEl.textContent = `Nilai ${config.label} wajib diisi angka.`;
          valid = false;
          return null;
        }
        const num = parseFloat(val);
        if (num < config.min) {
          errEl.textContent = `${config.label} tidak boleh lebih kecil dari ${config.min}%.`;
          valid = false;
          return null;
        }
        if (num > config.max) {
          errEl.textContent = `${config.label} tidak boleh melebihi ${config.max}%.`;
          valid = false;
          return null;
        }
        return num;
      }

      const ka = checkField("kadar_air", kaVal, RENTANG_VALIDASI.kadar_air);
      const bp = checkField("butir_patah", bpVal, RENTANG_VALIDASI.butir_patah);
      const mn = checkField("butir_menir", mnVal, RENTANG_VALIDASI.butir_menir);
      const ba = checkField("benda_asing", baVal, RENTANG_VALIDASI.benda_asing);

      if (!valid) return;

      const res = evaluate(ka, bp, mn, ba, sampleId, storeName);
      renderResult(res);
    });

    function clearErrors() {
      document.querySelectorAll(".error-message").forEach((el) => (el.textContent = ""));
    }

    // Reset Form
    btnReset.addEventListener("click", function () {
      form.reset();
      clearErrors();
      document.getElementById("result-placeholder").style.display = "block";
      document.getElementById("result-content").style.display = "none";
      document.getElementById("res-cert-number").textContent = "SNI-BELUM-DIUJI";
      currentResult = null;
    });

    // Cetak Sertifikat
    btnPrint.addEventListener("click", function () {
      if (!currentResult) {
        alert("Silakan lakukan evaluasi sampel terlebih dahulu.");
        return;
      }
      window.print();
    });

    // Simpan ke Riwayat
    btnSaveLog.addEventListener("click", function () {
      if (!currentResult) {
        alert("Silakan lakukan evaluasi sampel terlebih dahulu.");
        return;
      }
      saveToHistory(currentResult);
      alert("Hasil evaluasi sampel berhasil disimpan ke riwayat lokal!");
    });

    // Ekspor JSON
    btnExport.addEventListener("click", exportHistoryJSON);

    // Hapus Riwayat
    btnClear.addEventListener("click", function () {
      if (confirm("Apakah Anda yakin ingin menghapus seluruh riwayat pengujian lokal?")) {
        localStorage.removeItem(STORAGE_KEY);
        renderHistoryTable();
      }
    });

    // Muat riwayat awal
    renderHistoryTable();

    // Jika riwayat kosong, muat preset pertama sebagai demo awal
    if (getHistory().length === 0) {
      const initP = PRESETS.premium_ideal;
      document.getElementById("sample_id").value = initP.id;
      document.getElementById("kadar_air").value = initP.ka;
      document.getElementById("butir_patah").value = initP.bp;
      document.getElementById("butir_menir").value = initP.mn;
      document.getElementById("benda_asing").value = initP.ba;
      const initialRes = evaluate(initP.ka, initP.bp, initP.mn, initP.ba, initP.id);
      saveToHistory(initialRes);
      renderResult(initialRes);
    }
  });
})();
