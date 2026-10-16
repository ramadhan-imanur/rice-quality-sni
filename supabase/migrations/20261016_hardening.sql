-- ==============================================================================
-- 20261016_hardening.sql — Hardening Skema Supabase, Optimasi RLS & Indeks Komposit
-- Sistem Taksasi Mutu Beras SNI 6128:2020 & Anti-Fraud Engine
-- Pedoman: Supabase Best Practices (JWT Claims, Composite Index, Immutability)
-- ==============================================================================

-- 1. Helper Function: Ekstraksi Role berbasis JWT App Metadata (Zero-DB Lookups)
-- Menghindari overhead subquery ke tabel profiles pada setiap evaluasi RLS row
CREATE OR REPLACE FUNCTION public.current_user_role()
RETURNS TEXT
LANGUAGE sql
STABLE
AS $$
    SELECT coalesce(
        auth.jwt() -> 'app_metadata' ->> 'role',
        auth.jwt() ->> 'role',
        (SELECT role::text FROM public.profiles WHERE id = (select auth.uid()))
    );
$$;

-- Perbarui is_analis_or_admin untuk memanfaatkan JWT metadata cache
CREATE OR REPLACE FUNCTION public.is_analis_or_admin()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
    SELECT public.current_user_role() IN ('analis_lab', 'admin');
$$;

-- 2. Indeks Komposit Skalabilitas Tinggi (High-Throughput Pagination & Filtering)
CREATE INDEX IF NOT EXISTS idx_submissions_status_created 
    ON public.submissions (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_submissions_petani_created 
    ON public.submissions (petani_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_certificates_created_at 
    ON public.certificates (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_certificates_signature 
    ON public.certificates (signature_hmac);

CREATE INDEX IF NOT EXISTS idx_audit_logs_composite 
    ON public.audit_logs (entity_type, entity_id, timestamp DESC);

-- 3. Batasan Integritas Data (Data Constraints & Defensive Checks)
DO $$ BEGIN
    ALTER TABLE public.certificates 
        ADD CONSTRAINT chk_kadar_air_range CHECK (kadar_air >= 0 AND kadar_air <= 40.0),
        ADD CONSTRAINT chk_butir_patah_range CHECK (butir_patah >= 0 AND butir_patah <= 100.0),
        ADD CONSTRAINT chk_butir_menir_range CHECK (butir_menir >= 0 AND butir_menir <= 100.0),
        ADD CONSTRAINT chk_benda_asing_range CHECK (benda_asing >= 0 AND benda_asing <= 100.0),
        ADD CONSTRAINT chk_harga_dasar_non_negative CHECK (harga_dasar >= 0),
        ADD CONSTRAINT chk_harga_bersih_non_negative CHECK (harga_bersih >= 0);
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 4. Audit Log Otomatis via Database Trigger (Defense-in-Depth Anti-Tamper)
CREATE OR REPLACE FUNCTION public.audit_certificate_insertion()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    INSERT INTO public.audit_logs (
        timestamp,
        user_id,
        action,
        entity_type,
        entity_id,
        details_json
    ) VALUES (
        now(),
        NEW.analis_id,
        'VERIFY_AND_ISSUE_CERT',
        'CERTIFICATE',
        NEW.nomor_sertifikat,
        jsonb_build_object(
            'submission_id', NEW.submission_id,
            'kelas_mutu', NEW.kelas_mutu,
            'harga_bersih', NEW.harga_bersih,
            'signature_hmac', NEW.signature_hmac,
            'petani_nik_hash', encode(digest(NEW.petani_nik, 'sha256'), 'hex')
        )
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_cert_insert ON public.certificates;
CREATE TRIGGER trg_audit_cert_insert
    AFTER INSERT ON public.certificates
    FOR EACH ROW
    EXECUTE FUNCTION public.audit_certificate_insertion();

-- 5. Pemberian Hak Akses Terkendali (Least Privilege Enforcement)
REVOKE ALL ON public.audit_logs FROM public, anon;
GRANT SELECT ON public.audit_logs TO authenticated;
