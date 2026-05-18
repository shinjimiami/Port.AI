"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Loader2, Trash2, Upload, X } from "lucide-react";
import { fundamentalApi } from "@/lib/api";

const PIPELINE_STEPS = [
  "Mengekstrak data dari file...",
  "Menghitung rasio keuangan...",
  "Menganalisis tren pertumbuhan...",
  "Mendeteksi red flag...",
  "Menghitung valuasi...",
  "Menyusun entry signal...",
  "Membuat laporan naratif...",
];

interface FileEntry {
  file: File;
  year: string;
}

export default function FundamentalAnalyzePage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [ticker,       setTicker]       = useState("");
  const [currentPrice, setCurrentPrice] = useState("");
  const [files,        setFiles]        = useState<FileEntry[]>([]);
  const [loading,      setLoading]      = useState(false);
  const [stepIdx,      setStepIdx]      = useState(0);
  const [error,        setError]        = useState<string | null>(null);

  function handleFileDrop(e: React.DragEvent) {
    e.preventDefault();
    addFiles(Array.from(e.dataTransfer.files));
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    addFiles(Array.from(e.target.files ?? []));
  }

  function addFiles(incoming: File[]) {
    const valid = incoming.filter(
      (f) => f.name.endsWith(".pdf") || f.name.endsWith(".xlsx")
    );
    setFiles((prev) => {
      const combined = [...prev, ...valid.map((f) => ({ file: f, year: "" }))];
      return combined.slice(0, 3);
    });
  }

  function removeFile(idx: number) {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  }

  function setYear(idx: number, year: string) {
    setFiles((prev) => prev.map((f, i) => (i === idx ? { ...f, year } : f)));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ticker || !files.length) return;

    setError(null);
    setLoading(true);
    setStepIdx(0);

    // Animate steps while waiting
    const interval = setInterval(() => {
      setStepIdx((prev) => (prev < PIPELINE_STEPS.length - 1 ? prev + 1 : prev));
    }, 4000);

    try {
      const formData = new FormData();
      formData.append("ticker", ticker.toUpperCase());
      if (currentPrice) formData.append("current_price", currentPrice);

      const years = files.map((f) => f.year || "").join(",");
      if (years.replace(/,/g, "").trim()) formData.append("years", years);

      files.forEach((entry) => formData.append("files", entry.file));

      const result = await fundamentalApi.analyze(formData);
      clearInterval(interval);
      router.push(`/analyze/fundamental/${result.analysis_id}`);
    } catch (err: unknown) {
      clearInterval(interval);
      const axiosErr = err as { response?: { status?: number; data?: { detail?: unknown } }; message?: string };
      const raw    = axiosErr?.response?.data?.detail;
      const status = axiosErr?.response?.status;
      const detail = Array.isArray(raw)
        ? (raw as { msg?: string }[]).map((e) => e.msg ?? JSON.stringify(e)).join("; ")
        : typeof raw === "string" ? raw : undefined;
      const msg = detail
        ?? (status ? `Server error ${status}` : axiosErr?.message)
        ?? "Terjadi kesalahan. Pastikan file valid dan coba lagi.";
      setError(msg);
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Analisis Fundamental</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Upload laporan keuangan tahunan IDX (PDF atau Excel) — sistem akan mengekstrak
          data, menghitung rasio, dan menghasilkan entry signal berbasis AI.
        </p>
      </div>

      {loading ? (
        <PipelineLoading steps={PIPELINE_STEPS} activeIdx={stepIdx} />
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm flex items-start gap-2">
              <X size={16} className="shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          {/* Ticker + Price */}
          <div className="card space-y-4">
            <div>
              <label className="label">Kode Saham IDX *</label>
              <input
                className="input-field uppercase"
                placeholder="BBCA, TLKM, GOTO…"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                required
                maxLength={10}
              />
            </div>
            <div>
              <label className="label">Harga Saham Saat Ini <span className="text-gray-400 font-normal">(opsional — untuk valuasi)</span></label>
              <input
                className="input-field"
                type="number"
                placeholder="contoh: 9875"
                value={currentPrice}
                onChange={(e) => setCurrentPrice(e.target.value)}
                min={0}
              />
            </div>
          </div>

          {/* File upload */}
          <div className="card space-y-4">
            <h3 className="font-semibold text-gray-800">Upload Laporan Keuangan</h3>
            <p className="text-xs text-gray-400">Maksimal 3 file · PDF atau Excel · Maks 50MB per file</p>

            {/* Drop zone */}
            <div
              className="border-2 border-dashed border-gray-200 rounded-lg p-8 text-center cursor-pointer hover:border-brand-400 hover:bg-brand-50 transition-colors"
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
              onClick={() => inputRef.current?.click()}
            >
              <Upload className="mx-auto mb-2 text-gray-400" size={28} />
              <p className="text-sm text-gray-500">
                <span className="text-brand-600 font-medium">Klik untuk pilih file</span> atau drag & drop di sini
              </p>
              <input
                ref={inputRef}
                type="file"
                multiple
                accept=".pdf,.xlsx"
                className="hidden"
                onChange={handleFileInput}
              />
            </div>

            {/* File list */}
            {files.length > 0 && (
              <div className="space-y-2">
                {files.map((entry, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <FileText size={18} className="text-brand-500 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{entry.file.name}</p>
                      <p className="text-xs text-gray-400">{(entry.file.size / 1024 / 1024).toFixed(1)} MB</p>
                    </div>
                    <input
                      className="input-field w-28 text-sm py-1"
                      type="number"
                      placeholder="Tahun"
                      value={entry.year}
                      onChange={(e) => setYear(idx, e.target.value)}
                      min={2000}
                      max={2099}
                    />
                    <button type="button" onClick={() => removeFile(idx)} className="text-gray-400 hover:text-red-500">
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={!ticker || files.length === 0}
            className="btn-primary w-full py-3 text-base"
          >
            Mulai Analisis
          </button>
        </form>
      )}
    </div>
  );
}

function PipelineLoading({ steps, activeIdx }: { steps: string[]; activeIdx: number }) {
  return (
    <div className="card space-y-6">
      <div className="text-center">
        <Loader2 className="animate-spin mx-auto mb-3 text-brand-600" size={36} />
        <h3 className="font-semibold text-gray-800 text-lg">Sedang Menganalisis…</h3>
        <p className="text-gray-400 text-sm mt-1">Proses ini membutuhkan 30–90 detik</p>
      </div>
      <div className="space-y-3">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-3">
            <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 text-xs font-bold
              ${i < activeIdx  ? "bg-emerald-500 text-white"
              : i === activeIdx ? "bg-brand-600 text-white animate-pulse"
              : "bg-gray-100 text-gray-400"}`}>
              {i < activeIdx ? "✓" : i + 1}
            </div>
            <span className={`text-sm ${i <= activeIdx ? "text-gray-800 font-medium" : "text-gray-400"}`}>
              {step}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
