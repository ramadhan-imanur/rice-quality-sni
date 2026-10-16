/**
 * app.js — Logika Antarmuka Penilai Mutu Beras SNI 6128:2020 & Maker-Checker
 * =========================================================================
 * Mengimplementasikan:
 * 1. Navigasi Tab Terpadu (Simulasi, Maker Petani, Checker Lab, Bank Sertifikat)
 * 2. Visualisasi Indikator Ambang Batas SNI (Traffic Light System)
 * 3. Alur Kerja Maker-Checker Anti-Fraud (Pengajuan Batch & Sertifikasi Lab)
 * 4. Integrasi Penuh dengan Peladen REST API & Dukungan Offline
 * 
 * Penulis: Ramadhaan Imanur Rochima (NIM M0124015) — S1 Matematika FMIPA UNS
 */

(function () {
  "use strict";

  // =========================================================================
  // KONSTANTA & PRESETS LOKAL
  // =========================================================================

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

  // =========================================================================
  // INISIALISASI HALAMAN
  // =========================================================================

  document.addEventListener("DOMContentLoaded", function () {
    initTabs();
    initCV();
    initSimulation();
    initMaker();
    initChecker();
    initCertificates();

    // Default: jalankan simulasi pertama
    loadPreset("premium_ideal");
  });

  // =========================================================================
  // 1. PENGALIHAN TAB (TAB SWITCHER)
  // =========================================================================

  function initTabs() {
    const tabBtns = document.querySelectorAll(".tab-btn");
    tabBtns.forEach((btn) => {
      btn.addEventListener("click", function () {
        const targetId = this.dataset.tab;
        switchTab(targetId);
      });
    });

    const btnGoMaker = document.getElementById("btn-go-to-maker");
    if (btnGoMaker) {
      btnGoMaker.addEventListener("click", () => switchTab("tab-maker"));
    }
  }

  function switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.tab === tabId);
    });
    document.querySelectorAll(".tab-content").forEach((c) => {
      c.classList.toggle("active", c.id === tabId);
    });

    // Refresh data saat tab dibuka
    if (tabId === "tab-maker") loadMakerSubmissions();
    if (tabId === "tab-checker") loadPendingSubmissions();
    if (tabId === "tab-certificates") loadCertificates();
  }

  // =========================================================================
  // 1b. DETEKSI CITRA COMPUTER VISION (CV) UNTUK BUTIR BERAS
  // =========================================================================

  let lastCvResult = null;

  function initCV() {
    const fileInput = document.getElementById("cv-file-input");
    const btnTrigger = document.getElementById("btn-trigger-camera");
    const btnDemo = document.getElementById("btn-cv-demo");
    const btnApply = document.getElementById("btn-apply-cv");
    const resultBox = document.getElementById("cv-result-box");
    const previewImg = document.getElementById("cv-preview-img");

    if (!fileInput || !btnTrigger) return;

    btnTrigger.addEventListener("click", () => {
      fileInput.click();
    });

    fileInput.addEventListener("change", function () {
      const file = this.files && this.files[0];
      if (!file) return;

      const reader = new FileReader();
      setButtonLoading(btnTrigger, true, "⏳ Memproses Citra...");
      reader.onload = function (e) {
        const base64Data = e.target.result;
        sendCvAnalysis(base64Data, file.name);
      };
      reader.onerror = function () {
        setButtonLoading(btnTrigger, false, "📸 Ambil Foto / Unggah Citra");
        alert("Gagal membaca file gambar.");
      };
      reader.readAsDataURL(file);
    });

    if (btnDemo) {
      btnDemo.addEventListener("click", function () {
        setButtonLoading(btnDemo, true, "⏳ Menyiapkan Sampel Demo...");
        sendCvAnalysis(null, "Sampel Demo Butir Beras");
      });
    }

    if (btnApply) {
      btnApply.addEventListener("click", function () {
        if (!lastCvResult) {
          alert("Belum ada data citra beras untuk diterapkan.");
          return;
        }
        applyCvToForm(lastCvResult);
      });
    }

    function setButtonLoading(btn, isLoading, text) {
      if (!btn) return;
      btn.disabled = isLoading;
      if (btnDemo) btnDemo.disabled = isLoading;
      if (btnTrigger) btnTrigger.disabled = isLoading;
      btn.textContent = text;
    }

    function sendCvAnalysis(base64Data, sampleName) {
      const payload = {
        sample_id: sampleName || "Analisis Citra Beras",
      };
      if (base64Data) {
        payload.image_base64 = base64Data;
      }

      fetch("/api/cv/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then(async (res) => {
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || "Gagal menganalisis citra beras.");
          return data;
        })
        .then((data) => {
          lastCvResult = data.measurements;
          displayCvResults(data);
        })
        .catch((err) => {
          alert("Galat Computer Vision: " + err.message);
        })
        .finally(() => {
          setButtonLoading(btnTrigger, false, "📸 Ambil Foto / Unggah Citra");
          if (btnDemo) setButtonLoading(btnDemo, false, "✨ Coba Sampel Demo");
        });
    }

    function displayCvResults(data) {
      if (!resultBox || !previewImg) return;
      const m = data.measurements;

      const b64 = data.annotated_image_base64 || "";
      previewImg.src = b64.startsWith("data:") ? b64 : "data:image/jpeg;base64," + b64;
      document.getElementById("cv-stat-total").textContent = m.grain_count;
      document.getElementById("cv-stat-head").textContent = m.persentase_butir_kepala.toFixed(1) + "%";
      document.getElementById("cv-stat-broken").textContent = m.persentase_butir_patah.toFixed(1) + "%";
      document.getElementById("cv-stat-menir").textContent = m.persentase_butir_menir.toFixed(1) + "%";
      document.getElementById("cv-stat-foreign").textContent = (m.persentase_benda_asing || 0).toFixed(4) + "%";

      resultBox.style.display = "block";
      resultBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function applyCvToForm(m) {
      document.getElementById("sim_butir_patah").value = m.persentase_butir_patah.toFixed(1);
      document.getElementById("sim_butir_menir").value = m.persentase_butir_menir.toFixed(1);
      document.getElementById("sim_benda_asing").value = (m.persentase_benda_asing || 0.005).toFixed(4);

      const sampleInput = document.getElementById("sim_sample_id");
      if (!sampleInput.value.trim() || sampleInput.value === "Simulasi Beras") {
        sampleInput.value = "Sampel CV (" + m.grain_count + " butir)";
      }

      clearErrors();

      const ka = parseFloat(document.getElementById("sim_kadar_air").value) || 13.5;
      runSimulation(ka, m.persentase_butir_patah, m.persentase_butir_menir, m.persentase_benda_asing || 0.005, sampleInput.value);

      const simForm = document.getElementById("simulation-form");
      if (simForm) {
        simForm.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
  }

  // =========================================================================
  // 2. MODUL SIMULASI MANDIRI & INDIKATOR TRAFFIC LIGHT (TAB 1)
  // =========================================================================

  function initSimulation() {
    const simForm = document.getElementById("simulation-form");
    const btnSimReset = document.getElementById("btn-sim-reset");

    // Presets
    document.querySelectorAll(".btn-chip").forEach((chip) => {
      chip.addEventListener("click", function () {
        loadPreset(this.dataset.preset);
      });
    });

    // Submit
    simForm.addEventListener("submit", function (e) {
      e.preventDefault();
      clearErrors();

      const ka = parseFloat(document.getElementById("sim_kadar_air").value);
      const bp = parseFloat(document.getElementById("sim_butir_patah").value);
      const mn = parseFloat(document.getElementById("sim_butir_menir").value);
      const ba = parseFloat(document.getElementById("sim_benda_asing").value);
      const sampleId = document.getElementById("sim_sample_id").value.trim() || "Simulasi Beras";

      let valid = true;
      if (isNaN(ka) || ka < 0 || ka > 40) {
        document.getElementById("err-sim_kadar_air").textContent = "Kadar air harus 0.0 - 40.0%";
        valid = false;
      }
      if (isNaN(bp) || bp < 0 || bp > 100) {
        document.getElementById("err-sim_butir_patah").textContent = "Butir patah harus 0.0 - 100.0%";
        valid = false;
      }
      if (isNaN(mn) || mn < 0 || mn > 100) {
        document.getElementById("err-sim_butir_menir").textContent = "Butir menir harus 0.0 - 100.0%";
        valid = false;
      }
      if (isNaN(ba) || ba < 0 || ba > 10) {
        document.getElementById("err-sim_benda_asing").textContent = "Benda asing harus 0.000 - 10.000%";
        valid = false;
      }

      if (!valid) return;

      runSimulation(ka, bp, mn, ba, sampleId);
    });

    btnSimReset.addEventListener("click", function () {
      simForm.reset();
      clearErrors();
      document.getElementById("sim-result-placeholder").style.display = "block";
      document.getElementById("sim-result-content").style.display = "none";
    });
  }

  function clearErrors() {
    document.querySelectorAll(".error-message").forEach((el) => (el.textContent = ""));
  }

  function loadPreset(key) {
    const p = PRESETS[key];
    if (!p) return;
    document.getElementById("sim_sample_id").value = p.id;
    document.getElementById("sim_kadar_air").value = p.ka;
    document.getElementById("sim_butir_patah").value = p.bp;
    document.getElementById("sim_butir_menir").value = p.mn;
    document.getElementById("sim_benda_asing").value = p.ba;
    clearErrors();
    runSimulation(p.ka, p.bp, p.mn, p.ba, p.id);
  }

  function runSimulation(ka, bp, mn, ba, sampleId) {
    // Panggil API peladen
    fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        kadar_air: ka,
        butir_patah: bp,
        butir_menir: mn,
        benda_asing: ba,
        sample_id: sampleId,
      }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.error || "Gagal menghitung simulasi");
        }
        return res.json();
      })
      .then((data) => {
        renderSimulationResult(data.result);
      })
      .catch((err) => {
        // Fallback komputasi lokal jika server offline
        console.warn("API Offline, menghitung secara deterministik lokal:", err);
        const localResult = computeLocalDeterministic(ka, bp, mn, ba, sampleId);
        renderSimulationResult(localResult);
      });
  }

  function renderSimulationResult(res) {
    document.getElementById("sim-result-placeholder").style.display = "none";
    document.getElementById("sim-result-content").style.display = "block";

    const kelas = res.klasifikasi.kelas_mutu;
    const label = res.klasifikasi.label_mutu;
    const banner = document.getElementById("sim-grade-banner");
    const titleEl = document.getElementById("sim-grade-title");
    const descEl = document.getElementById("sim-grade-desc");
    const iconEl = document.getElementById("sim-grade-icon");

    banner.className = "grade-banner " + kelas.toLowerCase();
    titleEl.textContent = "MUTU " + label.toUpperCase();

    if (kelas === "PREMIUM") {
      iconEl.textContent = "✓";
      descEl.textContent = "Beras Anda memenuhi seluruh ambang batas mutu tertinggi SNI 6128:2020.";
    } else if (kelas === "MEDIUM_I") {
      iconEl.textContent = "i";
      descEl.textContent = "Beras Anda memenuhi standar baku kelas Mutu Medium I.";
    } else if (kelas === "MEDIUM_II") {
      iconEl.textContent = "!";
      descEl.textContent = "Beras Anda memenuhi standar baku kelas Mutu Medium II.";
    } else {
      iconEl.textContent = "✕";
      descEl.textContent = "Beras melampaui batas toleransi mutu fisik Medium II atau berkadar air basah (> 14%).";
    }

    // 1. Diagnosa Penurunan Kelas Mutu
    renderDiagnosisVerdict(res);

    // 2. Indikator Traffic Light & Visual Gauges
    renderGauges(res.parameter_uji);

    // 3. Rekomendasi Finansial
    const h = res.rekomendasi_harga;
    document.getElementById("sim-price-base").textContent = `Rp ${h.harga_dasar.toLocaleString("id-ID")} / kg`;
    document.getElementById("sim-price-drying").textContent = `- Rp ${h.penalti_pengeringan.toLocaleString("id-ID")} / kg`;
    document.getElementById("sim-price-shrinkage").textContent = `- Rp ${h.potongan_penyusutan.toLocaleString("id-ID")} / kg`;
    document.getElementById("sim-price-net").textContent = `Rp ${h.harga_bersih.toLocaleString("id-ID")} / kg`;
  }

  function renderDiagnosisVerdict(res) {
    const box = document.getElementById("sim-verdict-box");
    const p = res.parameter_uji;
    const kelas = res.klasifikasi.kelas_mutu;

    let reasons = [];
    if (p.kadar_air > 14.0) {
      reasons.push(`Kadar air (${p.kadar_air}%) melebihi batas 14.0% (kena penalti pengeringan)`);
    }
    if (p.butir_patah > 25.0) {
      reasons.push(`Butir patah (${p.butir_patah}%) melebihi batas Medium II (25.0%)`);
    } else if (p.butir_patah > 20.0) {
      reasons.push(`Butir patah (${p.butir_patah}%) melebihi batas Medium I (20.0%)`);
    } else if (p.butir_patah > 15.0) {
      reasons.push(`Butir patah (${p.butir_patah}%) melebihi batas Premium (15.0%)`);
    }

    if (p.butir_menir > 5.0) {
      reasons.push(`Butir menir (${p.butir_menir}%) melebihi batas Medium II (5.0%)`);
    } else if (p.butir_menir > 2.0) {
      reasons.push(`Butir menir (${p.butir_menir}%) melebihi batas Medium I (2.0%)`);
    } else if (p.butir_menir > 0.5) {
      reasons.push(`Butir menir (${p.butir_menir}%) melebihi batas Premium (0.5%)`);
    }

    if (p.benda_asing > 0.05) {
      reasons.push(`Benda asing (${p.benda_asing}%) melebihi batas Medium II (0.05%)`);
    } else if (p.benda_asing > 0.02) {
      reasons.push(`Benda asing (${p.benda_asing}%) melebihi batas Medium I (0.02%)`);
    } else if (p.benda_asing > 0.01) {
      reasons.push(`Benda asing (${p.benda_asing}%) melebihi batas Premium (0.01%)`);
    }

    if (kelas === "PREMIUM") {
      box.innerHTML = `<strong>Status Mutu Unggul:</strong> Seluruh 4 parameter berada di dalam batas toleransi tertinggi. Tidak ada penalti harga acuan.`;
      box.style.borderLeftColor = "#10b981";
    } else if (reasons.length > 0) {
      box.innerHTML = `<strong>Penyebab Penurunan Kelas Mutu:</strong><br>&bull; ` + reasons.join("<br>&bull; ");
      box.style.borderLeftColor = (kelas === "SUBSTANDAR") ? "#ef4444" : "#f59e0b";
    } else {
      box.innerHTML = `<strong>Keterangan:</strong> Hasil sesuai toleransi kelas ${res.klasifikasi.label_mutu}.`;
      box.style.borderLeftColor = "#3b82f6";
    }
  }

  function renderGauges(p) {
    const grid = document.getElementById("sim-gauge-grid");

    const gauges = [
      {
        label: "Kadar Air",
        val: p.kadar_air,
        unit: "%",
        max: 25,
        color: p.kadar_air <= 14.0 ? "green" : "red",
        status: p.kadar_air <= 14.0 ? "Lulus SNI (<= 14%)" : "Penalti (> 14%)",
        fillPct: Math.min(100, (p.kadar_air / 25) * 100),
      },
      {
        label: "Butir Patah",
        val: p.butir_patah,
        unit: "%",
        max: 40,
        color: p.butir_patah <= 15 ? "green" : (p.butir_patah <= 20 ? "blue" : (p.butir_patah <= 25 ? "amber" : "red")),
        status: p.butir_patah <= 15 ? "Premium (<= 15%)" : (p.butir_patah <= 20 ? "Med I (<= 20%)" : (p.butir_patah <= 25 ? "Med II (<= 25%)" : "Substandar")),
        fillPct: Math.min(100, (p.butir_patah / 40) * 100),
      },
      {
        label: "Butir Menir",
        val: p.butir_menir,
        unit: "%",
        max: 8,
        color: p.butir_menir <= 0.5 ? "green" : (p.butir_menir <= 2.0 ? "blue" : (p.butir_menir <= 5.0 ? "amber" : "red")),
        status: p.butir_menir <= 0.5 ? "Premium (<= 0.5%)" : (p.butir_menir <= 2.0 ? "Med I (<= 2%)" : (p.butir_menir <= 5.0 ? "Med II (<= 5%)" : "Substandar")),
        fillPct: Math.min(100, (p.butir_menir / 8) * 100),
      },
      {
        label: "Benda Asing",
        val: p.benda_asing,
        unit: "%",
        max: 0.1,
        color: p.benda_asing <= 0.01 ? "green" : (p.benda_asing <= 0.02 ? "blue" : (p.benda_asing <= 0.05 ? "amber" : "red")),
        status: p.benda_asing <= 0.01 ? "Premium (<= 0.01%)" : (p.benda_asing <= 0.02 ? "Med I (<= 0.02%)" : (p.benda_asing <= 0.05 ? "Med II (<= 0.05%)" : "Substandar")),
        fillPct: Math.min(100, (p.benda_asing / 0.1) * 100),
      },
    ];

    grid.innerHTML = gauges
      .map(
        (g) => `
      <div class="gauge-item">
        <div class="gauge-header">
          <span>${g.label}</span>
          <span class="gauge-val">${g.val.toFixed(g.label === "Benda Asing" ? 4 : 2)} ${g.unit}</span>
        </div>
        <div class="gauge-track">
          <div class="gauge-fill ${g.color}" style="width: ${g.fillPct}%;"></div>
        </div>
        <div class="gauge-status ${g.color}">${g.status}</div>
      </div>
    `
      )
      .join("");
  }

  // =========================================================================
  // 3. PORTAL PETANI: PENGAJUAN BATCH (TAB 2 - MAKER WORKFLOW)
  // =========================================================================

  function initMaker() {
    const form = document.getElementById("maker-batch-form");
    const tglPanenInput = document.getElementById("m_tanggal_panen");
    if (tglPanenInput && !tglPanenInput.value) {
      tglPanenInput.value = new Date().toISOString().substring(0, 10);
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();

      const payload = {
        petani_id: 1,
        petani_nama: document.getElementById("m_petani_nama").value.trim(),
        petani_nik: document.getElementById("m_petani_nik").value.trim(),
        kontak: document.getElementById("m_kontak").value.trim(),
        varietas_padi: document.getElementById("m_varietas").value.trim(),
        asal_lahan: document.getElementById("m_asal_lahan").value.trim(),
        tonase_kg: parseFloat(document.getElementById("m_tonase").value),
        tanggal_panen: document.getElementById("m_tanggal_panen").value,
        catatan: document.getElementById("m_catatan").value.trim(),
      };

      fetch("/api/submissions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then(async (res) => {
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || "Gagal mengirim pengajuan batch");
          return data;
        })
        .then((data) => {
          alert("Pengajuan sampel berhasil terdaftar!\nID Batch: " + data.submission.id + "\n\nUnduh label pengantar untuk ditempel di karung sampel.");
          form.reset();
          tglPanenInput.value = new Date().toISOString().substring(0, 10);
          loadMakerSubmissions();
          if (data.label_url) {
            window.open(data.label_url, "_blank");
          }
        })
        .catch((err) => {
          alert("Galat: " + err.message);
        });
    });

    document.getElementById("btn-refresh-submissions").addEventListener("click", loadMakerSubmissions);
  }

  function loadMakerSubmissions() {
    const tbody = document.getElementById("maker-submissions-tbody");
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:1.5rem;">Memuat daftar pengajuan...</td></tr>`;

    fetch("/api/submissions")
      .then((res) => res.json())
      .then((data) => {
        if (!data.submissions || data.submissions.length === 0) {
          tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:1.5rem; color:#64748b;">Belum ada pengajuan batch sampel.</td></tr>`;
          return;
        }

        tbody.innerHTML = data.submissions
          .map(
            (s) => `
          <tr>
            <td>
              <strong>${s.id}</strong><br>
              <small style="color:#64748b;">Barcode: ${s.barcode_id}</small>
            </td>
            <td>${escapeHtml(s.varietas_padi)}</td>
            <td>${Number(s.tonase_kg).toLocaleString("id-ID")} kg</td>
            <td>
              <span class="badge-status ${s.status.toLowerCase()}">${s.status}</span>
            </td>
            <td>
              <div class="btn-action-group">
                <a href="/api/submissions/${encodeURIComponent(s.id)}/label" target="_blank" class="btn btn-xs btn-outline">
                  🏷 Cetak Label
                </a>
                ${
                  s.status === "VERIFIED" && s.nomor_sertifikat
                    ? `<a href="/api/certificates/${encodeURIComponent(s.nomor_sertifikat)}/download" target="_blank" class="btn btn-xs btn-success">
                        📜 Lembar Taksasi
                      </a>`
                    : ""
                }
              </div>
            </td>
          </tr>
        `
          )
          .join("");
      })
      .catch((err) => {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:red; padding:1.5rem;">Gagal memuat: ${err.message}</td></tr>`;
      });
  }

  // =========================================================================
  // 4. PORTAL ANALIS LAB: VERIFIKASI & TAKSASI (TAB 3 - CHECKER)
  // =========================================================================

  function initChecker() {
    document.getElementById("btn-refresh-pending").addEventListener("click", loadPendingSubmissions);
    document.getElementById("btn-close-modal").addEventListener("click", closeModal);

    const labForm = document.getElementById("lab-test-form");
    labForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const subId = document.getElementById("lab_sub_id").value;
      const payload = {
        analis_id: 2,
        kadar_air: parseFloat(document.getElementById("lab_kadar_air").value),
        butir_patah: parseFloat(document.getElementById("lab_butir_patah").value),
        butir_menir: parseFloat(document.getElementById("lab_butir_menir").value),
        benda_asing: parseFloat(document.getElementById("lab_benda_asing").value),
      };

      fetch(`/api/submissions/${encodeURIComponent(subId)}/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then(async (res) => {
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || "Gagal menerbitkan lembar taksasi");
          return data;
        })
        .then((data) => {
          alert(`Lembar Hasil Taksasi Mutu Berhasil Diterbitkan!\n\nNo. Taksasi: ${data.nomor_taksasi || data.nomor_sertifikat}\nKelas Mutu: ${data.kelas_mutu}\nHarga Bersih: Rp ${Number(data.harga_bersih).toLocaleString("id-ID")}/kg\nTanda Tangan HMAC: ${data.signature_hmac}`);
          closeModal();
          loadPendingSubmissions();
          switchTab("tab-certificates");
          if (data.download_url) {
            window.open(data.download_url, "_blank");
          }
        })
        .catch((err) => {
          alert("Galat verifikasi lab: " + err.message);
        });
    });
  }

  function loadPendingSubmissions() {
    const tbody = document.getElementById("checker-pending-tbody");
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:1.5rem;">Memuat antrean sampel lab...</td></tr>`;

    fetch("/api/submissions?status=PENDING")
      .then((res) => res.json())
      .then((data) => {
        if (!data.submissions || data.submissions.length === 0) {
          tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:1.5rem; color:#64748b;">Tidak ada sampel tertunda dalam antrean uji laboratorium.</td></tr>`;
          return;
        }

        tbody.innerHTML = data.submissions
          .map(
            (s) => `
          <tr>
            <td>${s.created_at}</td>
            <td>
              <strong>${s.id}</strong><br>
              <small style="color:#64748b;">${s.barcode_id}</small>
            </td>
            <td>${escapeHtml(s.petani_nama)}<br><small style="color:#64748b;">NIK: ${s.petani_nik}</small></td>
            <td>${escapeHtml(s.varietas_padi)}<br><small style="color:#64748b;">${escapeHtml(s.asal_lahan)}</small></td>
            <td>${Number(s.tonase_kg).toLocaleString("id-ID")} kg</td>
            <td><span class="badge-status pending">PENDING</span></td>
            <td>
              <button type="button" class="btn btn-xs btn-primary btn-open-test" data-id="${s.id}" data-nama="${escapeHtml(s.petani_nama)}" data-varietas="${escapeHtml(s.varietas_padi)}" data-tonase="${s.tonase_kg}">
                🔬 Uji Sampel Lab
              </button>
            </td>
          </tr>
        `
          )
          .join("");

        // Pasang event listener modal
        document.querySelectorAll(".btn-open-test").forEach((btn) => {
          btn.addEventListener("click", function () {
            openLabTestModal(this.dataset.id, this.dataset.nama, this.dataset.varietas, this.dataset.tonase);
          });
        });
      })
      .catch((err) => {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:red; padding:1.5rem;">Gagal memuat antrean: ${err.message}</td></tr>`;
      });
  }

  function openLabTestModal(subId, nama, varietas, tonase) {
    document.getElementById("lab_sub_id").value = subId;
    document.getElementById("modal-lab-title").textContent = `Input Uji Laboratorium: ${subId}`;
    document.getElementById("modal-batch-info").innerHTML = `
      <strong>Pemilik:</strong> ${escapeHtml(nama)} | <strong>Varietas:</strong> ${escapeHtml(varietas)} | <strong>Tonase:</strong> ${Number(tonase).toLocaleString("id-ID")} kg<br>
      <small style="color:#64748b;">Gunakan alat ukur terkalibrasi untuk mengisi 4 parameter berikut:</small>
    `;

    // Default nilai uji wajar
    document.getElementById("lab_kadar_air").value = "13.4";
    document.getElementById("lab_butir_patah").value = "12.5";
    document.getElementById("lab_butir_menir").value = "0.35";
    document.getElementById("lab_benda_asing").value = "0.0080";

    document.getElementById("modal-lab-test").style.display = "flex";
  }

  function closeModal() {
    document.getElementById("modal-lab-test").style.display = "none";
  }

  // =========================================================================
  // 5. BANK SERTIFIKAT & AUDIT TRAIL (TAB 4)
  // =========================================================================

  let allCertificates = [];

  function initCertificates() {
    document.getElementById("btn-refresh-certs").addEventListener("click", loadCertificates);
    const searchInput = document.getElementById("cert-search-input");
    searchInput.addEventListener("input", function () {
      const q = this.value.toLowerCase().trim();
      filterCertificates(q);
    });
  }

  function loadCertificates() {
    const tbody = document.getElementById("certificates-tbody");
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:1.5rem;">Memuat daftar sertifikat...</td></tr>`;

    fetch("/api/certificates")
      .then((res) => res.json())
      .then((data) => {
        allCertificates = data.certificates || [];
        renderCertificatesTable(allCertificates);
      })
      .catch((err) => {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:red; padding:1.5rem;">Gagal memuat sertifikat: ${err.message}</td></tr>`;
      });
  }

  function filterCertificates(query) {
    if (!query) {
      renderCertificatesTable(allCertificates);
      return;
    }
    const filtered = allCertificates.filter((c) => {
      return (
        c.nomor_sertifikat.toLowerCase().includes(query) ||
        (c.petani_nama && c.petani_nama.toLowerCase().includes(query)) ||
        (c.varietas_padi && c.varietas_padi.toLowerCase().includes(query)) ||
        (c.kelas_mutu && c.kelas_mutu.toLowerCase().includes(query))
      );
    });
    renderCertificatesTable(filtered);
  }

  function renderCertificatesTable(certs) {
    const tbody = document.getElementById("certificates-tbody");
    if (!certs || certs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:1.5rem; color:#64748b;">Belum ada lembar taksasi mutu yang diterbitkan.</td></tr>`;
      return;
    }

    tbody.innerHTML = certs
      .map(
        (c) => `
      <tr>
        <td>
          <strong style="color:#064e3b;">${c.nomor_sertifikat}</strong><br>
          <small style="color:#64748b;">Batch: ${c.submission_id}</small>
        </td>
        <td>${c.tanggal_uji}</td>
        <td>
          <strong>${escapeHtml(c.petani_nama)}</strong><br>
          <small style="color:#64748b;">NIK: ${c.petani_nik}</small>
        </td>
        <td>${escapeHtml(c.varietas_padi)}</td>
        <td>
          <span class="badge-status verified">${c.label_mutu || c.kelas_mutu}</span>
        </td>
        <td><strong>Rp ${Number(c.harga_bersih).toLocaleString("id-ID")} / kg</strong></td>
        <td>
          <code style="font-size:0.75rem; background:#f1f5f9; padding:2px 4px; border-radius:3px;">
            ${c.signature_hmac ? c.signature_hmac.substring(0, 12) + "..." : "-"}
          </code>
        </td>
        <td>
          <div class="btn-action-group">
            <a href="${c.qr_url || `/verify.html?id=${encodeURIComponent(c.nomor_sertifikat)}&sig=${encodeURIComponent(c.signature_hmac)}`}" target="_blank" class="btn btn-xs btn-outline">
              🔍 Cek Keaslian
            </a>
            <a href="/api/certificates/${encodeURIComponent(c.nomor_sertifikat)}/download" target="_blank" class="btn btn-xs btn-success">
              📥 Unduh PDF
            </a>
          </div>
        </td>
      </tr>
    `
      )
      .join("");
  }

  // =========================================================================
  // UTILITIES & FALLBACK OFFLINE COMPUTATION
  // =========================================================================

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function computeLocalDeterministic(ka, bp, mn, ba, sampleId) {
    // Klasifikasi deterministik SNI 6128:2020
    let kelas = "SUBSTANDAR";
    let label = "Substandar";
    let hargaDasar = 11500;

    if (ka <= 14.0 && bp <= 15.0 && mn <= 0.5 && ba <= 0.01) {
      kelas = "PREMIUM";
      label = "Premium";
      hargaDasar = 15800;
    } else if (ka <= 14.0 && bp <= 20.0 && mn <= 2.0 && ba <= 0.02) {
      kelas = "MEDIUM_I";
      label = "Medium I";
      hargaDasar = 13500;
    } else if (ka <= 14.0 && bp <= 25.0 && mn <= 5.0 && ba <= 0.05) {
      kelas = "MEDIUM_II";
      label = "Medium II";
      hargaDasar = 13500;
    }

    const kelebihanAir = Math.max(0.0, ka - 14.0);
    const penaltiPengeringan = Math.round(kelebihanAir * 150);
    const potonganPenyusutan = Math.round(kelebihanAir * 0.015 * hargaDasar);
    const hargaBersih = Math.max(0, hargaDasar - penaltiPengeringan - potonganPenyusutan);

    return {
      sample_id: sampleId,
      nomor_sertifikat: "SIMULASI-LOKAL",
      parameter_uji: { kadar_air: ka, butir_patah: bp, butir_menir: mn, benda_asing: ba },
      klasifikasi: { kelas_mutu: kelas, label_mutu: label },
      rekomendasi_harga: {
        harga_dasar: hargaDasar,
        kelebihan_kadar_air: kelebihanAir,
        penalti_pengeringan: penaltiPengeringan,
        potongan_penyusutan: potonganPenyusutan,
        harga_bersih: hargaBersih,
      },
    };
  }
})();
