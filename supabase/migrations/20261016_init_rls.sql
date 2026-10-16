-- ==============================================================================
-- 20261016_init_rls.sql — Skema Supabase PostgreSQL & Kebijakan Row Level Security (RLS)
-- Sistem Taksasi Mutu Beras SNI 6128:2020 & Perlindungan Data Pribadi (UU PDP No. 27/2022)
-- Sesuai Pedoman Resmi: Supabase RLS & PostgreSQL Security Best Practices
-- ==============================================================================

-- 1. Ekstensi & Enum Types
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('petani', 'analis_lab', 'admin');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE submission_status AS ENUM ('PENDING', 'VERIFIED', 'REJECTED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE kelas_mutu_type AS ENUM ('PREMIUM', 'MEDIUM_I', 'MEDIUM_II', 'SUBSTANDAR');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Tabel Profiles (Terintegrasi dengan auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT UNIQUE NOT NULL,
    nama_lengkap TEXT NOT NULL,
    role user_role NOT NULL DEFAULT 'petani',
    nik_nip TEXT,
    instansi TEXT,
    kontak TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Index performa
CREATE INDEX IF NOT EXISTS idx_profiles_role ON public.profiles(role);

-- 3. Tabel Submissions (Pengajuan Batch Sampel oleh Petani)
CREATE TABLE IF NOT EXISTS public.submissions (
    id TEXT PRIMARY KEY,
    petani_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    petani_nama TEXT NOT NULL,
    petani_nik TEXT NOT NULL,
    kontak TEXT,
    varietas_padi TEXT NOT NULL,
    asal_lahan TEXT NOT NULL,
    tonase_kg NUMERIC(10, 2) NOT NULL CHECK (tonase_kg > 0),
    tanggal_panen DATE NOT NULL,
    catatan TEXT,
    status submission_status NOT NULL DEFAULT 'PENDING',
    barcode_id TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    verified_at TIMESTAMPTZ,
    verified_by UUID REFERENCES public.profiles(id),
    nomor_sertifikat TEXT
);

CREATE INDEX IF NOT EXISTS idx_submissions_petani_id ON public.submissions(petani_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON public.submissions(status);
CREATE INDEX IF NOT EXISTS idx_submissions_barcode ON public.submissions(barcode_id);

-- 4. Tabel Certificates (Lembar Hasil Taksasi Mutu Resmi)
CREATE TABLE IF NOT EXISTS public.certificates (
    nomor_sertifikat TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL UNIQUE REFERENCES public.submissions(id) ON DELETE RESTRICT,
    petani_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    analis_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    analis_nama TEXT NOT NULL,
    analis_nip TEXT NOT NULL,
    analis_instansi TEXT NOT NULL,
    petani_nama TEXT NOT NULL,
    petani_nik TEXT NOT NULL,
    varietas_padi TEXT NOT NULL,
    asal_lahan TEXT NOT NULL,
    tonase_kg NUMERIC(10, 2) NOT NULL,
    tanggal_uji DATE NOT NULL,
    kadar_air NUMERIC(5, 2) NOT NULL,
    butir_patah NUMERIC(5, 2) NOT NULL,
    butir_menir NUMERIC(5, 2) NOT NULL,
    benda_asing NUMERIC(6, 4) NOT NULL,
    kelas_mutu kelas_mutu_type NOT NULL,
    label_mutu TEXT NOT NULL,
    harga_dasar NUMERIC(12, 2) NOT NULL,
    penalti_pengeringan NUMERIC(12, 2) NOT NULL DEFAULT 0,
    potongan_penyusutan NUMERIC(12, 2) NOT NULL DEFAULT 0,
    harga_bersih NUMERIC(12, 2) NOT NULL,
    signature_hmac TEXT NOT NULL,
    qr_url TEXT NOT NULL,
    pdf_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_certificates_submission_id ON public.certificates(submission_id);
CREATE INDEX IF NOT EXISTS idx_certificates_petani_id ON public.certificates(petani_id);
CREATE INDEX IF NOT EXISTS idx_certificates_kelas_mutu ON public.certificates(kelas_mutu);

-- 5. Tabel Audit Logs (Append-Only)
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    user_id UUID REFERENCES public.profiles(id),
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    details_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON public.audit_logs(timestamp DESC);

-- ==============================================================================
-- 6. PENEGAKAN KEBIJAKAN ROW LEVEL SECURITY (RLS)
-- ==============================================================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- Helper Function: Mengecek apakah pengguna saat ini adalah analis_lab atau admin
CREATE OR REPLACE FUNCTION public.is_analis_or_admin()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = (select auth.uid())
          AND role IN ('analis_lab', 'admin')
    );
$$;

-- ------------------------------------------------------------------------------
-- A. KEBIJAKAN RLS: public.profiles
-- ------------------------------------------------------------------------------
-- Pengguna hanya dapat membaca profil miliknya sendiri, analis/admin dapat membaca semua
CREATE POLICY "profiles_select_own_or_analyst"
ON public.profiles
FOR SELECT
TO authenticated
USING (
    (select auth.uid()) = id OR public.is_analis_or_admin()
);

-- Pengguna hanya dapat mengubah profilnya sendiri
CREATE POLICY "profiles_update_own"
ON public.profiles
FOR UPDATE
TO authenticated
USING ((select auth.uid()) = id)
WITH CHECK ((select auth.uid()) = id);

-- ------------------------------------------------------------------------------
-- B. KEBIJAKAN RLS: public.submissions
-- ------------------------------------------------------------------------------
-- Petani dapat membuat pengajuan untuk dirinya sendiri
CREATE POLICY "submissions_insert_petani"
ON public.submissions
FOR INSERT
TO authenticated
WITH CHECK (
    (select auth.uid()) = petani_id
);

-- Petani hanya dapat melihat pengajuan miliknya; Analis/Admin dapat melihat semua antrean
CREATE POLICY "submissions_select_policy"
ON public.submissions
FOR SELECT
TO authenticated
USING (
    (select auth.uid()) = petani_id OR public.is_analis_or_admin()
);

-- Hanya Analis/Admin yang berhak memverifikasi dan mengubah status pengajuan
CREATE POLICY "submissions_update_analyst"
ON public.submissions
FOR UPDATE
TO authenticated
USING (public.is_analis_or_admin())
WITH CHECK (public.is_analis_or_admin());

-- ------------------------------------------------------------------------------
-- C. KEBIJAKAN RLS: public.certificates
-- ------------------------------------------------------------------------------
-- Petani pemilik dapat melihat sertifikat miliknya; Analis/Admin dapat melihat semua
CREATE POLICY "certificates_select_policy"
ON public.certificates
FOR SELECT
TO authenticated
USING (
    (select auth.uid()) = petani_id OR public.is_analis_or_admin()
);

-- Hanya Analis Lab dan Admin yang berwenang menerbitkan sertifikat
CREATE POLICY "certificates_insert_analyst"
ON public.certificates
FOR INSERT
TO authenticated
WITH CHECK (
    public.is_analis_or_admin() AND (select auth.uid()) = analis_id
);

-- ------------------------------------------------------------------------------
-- D. KEBIJAKAN RLS: public.audit_logs
-- ------------------------------------------------------------------------------
-- Hanya Admin yang dapat membaca seluruh audit log
CREATE POLICY "audit_logs_select_admin"
ON public.audit_logs
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = (select auth.uid()) AND role = 'admin'
    )
);

-- Tidak ada pengguna yang dapat mengubah atau menghapus audit log (Immutable)
REVOKE UPDATE, DELETE ON public.audit_logs FROM public, anon, authenticated;

-- ==============================================================================
-- 7. FUNGSI VERIFIKASI PUBLIK AMAN (MASKING NIK & ANTI DATA HARVESTING)
-- ==============================================================================
CREATE OR REPLACE FUNCTION public.verify_taksasi_public(p_cert_id TEXT, p_sig TEXT)
RETURNS TABLE (
    valid BOOLEAN,
    status TEXT,
    nomor_sertifikat TEXT,
    petani_nama TEXT,
    petani_nik_masked TEXT,
    varietas_padi TEXT,
    asal_lahan TEXT,
    tonase_kg NUMERIC,
    tanggal_uji DATE,
    kadar_air NUMERIC,
    butir_patah NUMERIC,
    butir_menir NUMERIC,
    benda_asing NUMERIC,
    kelas_mutu TEXT,
    harga_bersih NUMERIC,
    signature_hmac TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    r RECORD;
BEGIN
    SELECT * INTO r FROM public.certificates WHERE certificates.nomor_sertifikat = p_cert_id;
    IF NOT FOUND THEN
        RETURN QUERY SELECT
            FALSE, 'NOT_FOUND'::TEXT, NULL::TEXT, NULL::TEXT, NULL::TEXT, NULL::TEXT,
            NULL::TEXT, NULL::NUMERIC, NULL::DATE, NULL::NUMERIC, NULL::NUMERIC,
            NULL::NUMERIC, NULL::NUMERIC, NULL::TEXT, NULL::NUMERIC, NULL::TEXT;
        RETURN;
    END IF;

    -- Validasi tanda tangan jika disediakan
    IF p_sig IS NOT NULL AND p_sig <> '' AND p_sig <> r.signature_hmac THEN
        RETURN QUERY SELECT
            FALSE, 'TAMPERED'::TEXT, r.nomor_sertifikat, r.petani_nama,
            SUBSTRING(r.petani_nik, 1, 6) || '******' || SUBSTRING(r.petani_nik, 13, 4),
            r.varietas_padi, r.asal_lahan, r.tonase_kg, r.tanggal_uji,
            r.kadar_air, r.butir_patah, r.butir_menir, r.benda_asing,
            r.kelas_mutu::TEXT, r.harga_bersih, r.signature_hmac;
        RETURN;
    END IF;

    -- Kembalikan data sah dengan NIK ter-masking
    RETURN QUERY SELECT
        TRUE, 'VERIFIED_OFFICIAL'::TEXT, r.nomor_sertifikat, r.petani_nama,
        SUBSTRING(r.petani_nik, 1, 6) || '******' || SUBSTRING(r.petani_nik, 13, 4),
        r.varietas_padi, r.asal_lahan, r.tonase_kg, r.tanggal_uji,
        r.kadar_air, r.butir_patah, r.butir_menir, r.benda_asing,
        r.kelas_mutu::TEXT, r.harga_bersih, r.signature_hmac;
END;
$$;

GRANT EXECUTE ON FUNCTION public.verify_taksasi_public(TEXT, TEXT) TO anon, authenticated;
