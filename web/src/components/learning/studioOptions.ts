/**
 * studioOptions.ts — Skema konfigurasi per tipe generator Studio (A05).
 *
 * Satu sumber kebenaran untuk: (1) kontrol apa yang muncul di dialog tiap tipe,
 * (2) nilai default, (3) penyimpanan pengaturan terakhir per notebook (localStorage),
 * (4) serialisasi ke payload API (`buildStudioPayload`).
 *
 * Backend (`learning_helper.generate_studio_content` + `studio_api._studio_generate`)
 * memvalidasi ulang SEMUA nilai di sini → menolak/memotong nilai di luar rentang.
 * Tanpa pengaturan apa pun, perilaku lama tidak berubah (zero-regression).
 */

export type StudioKind =
  | 'summary'
  | 'study-guide'
  | 'flashcards'
  | 'faq'
  | 'mindmap'
  | 'timeline'
  | 'quiz'
  | 'podcast';

export type OptionKind = 'number' | 'choice' | 'toggle' | 'multi' | 'text';

export interface StudioChoice {
  value: string;
  labelKey: string;
  labelFallback: string;
}

export interface StudioOption {
  /** Kunci di objek konfigurasi (localStorage) — juga dikirim apa adanya ke API. */
  id: string;
  kind: OptionKind;
  labelKey: string;
  labelFallback: string;
  /** Keterangan kecil di bawah kontrol. */
  hintKey?: string;
  hintFallback?: string;
  min?: number;
  max?: number;
  choices?: StudioChoice[];
  /** Pilihan untuk kind 'multi' (checkbox). */
  multi?: StudioChoice[];
  placeholderFallback?: string;
  rows?: number;
  /** Ditaruh di bagian "Pengaturan lanjutan" (dibuka manual). */
  advanced?: boolean;
}

export interface StudioMeta {
  icon: string;
  labelKey: string;
  labelFallback: string;
  /** Key i18n satu baris penjelasan tipe (dipakai di header dialog). */
  blurbKey: string;
  blurbFallback: string;
  /** Nilai `kind` yang dikirim ke `POST /api/ai/<kind>`. */
  apiKind: string;
}

/** Parity LearningPage._STUDIO_TYPES — 8 generator, urutan sama dengan grid UI. */
export const STUDIO_META: Record<StudioKind, StudioMeta> = {
  summary: {
    icon: '📄', labelKey: 'learning_studio_summary', labelFallback: 'Summary',
    blurbKey: 'learning_dialog_blurb_summary',
    blurbFallback: 'Ringkasan eksekutif materi.', apiKind: 'summary',
  },
  'study-guide': {
    icon: '📘', labelKey: 'learning_studio_guide', labelFallback: 'Study Guide',
    blurbKey: 'learning_dialog_blurb_study_guide',
    blurbFallback: 'Panduan belajar lengkap + latihan.', apiKind: 'study-guide',
  },
  flashcards: {
    icon: '🃏', labelKey: 'learning_studio_flashcards', labelFallback: 'Flashcards',
    blurbKey: 'learning_dialog_blurb_flashcards',
    blurbFallback: 'Kartu tanya-jawab untuk hafalan.', apiKind: 'flashcards',
  },
  faq: {
    icon: '❓', labelKey: 'learning_studio_faq', labelFallback: 'FAQ',
    blurbKey: 'learning_dialog_blurb_faq',
    blurbFallback: 'Tanya-jawab yang sering ditanyakan.', apiKind: 'faq',
  },
  mindmap: {
    icon: '🗺️', labelKey: 'learning_studio_mindmap', labelFallback: 'Mind Map',
    blurbKey: 'learning_dialog_blurb_mindmap',
    blurbFallback: 'Peta konsep bercabang.', apiKind: 'mindmap',
  },
  timeline: {
    icon: '🕒', labelKey: 'learning_studio_timeline', labelFallback: 'Timeline',
    blurbKey: 'learning_dialog_blurb_timeline',
    blurbFallback: 'Urutan kronologis peristiwa.', apiKind: 'timeline',
  },
  quiz: {
    icon: '📝', labelKey: 'learning_studio_quiz', labelFallback: 'Quiz',
    blurbKey: 'learning_dialog_blurb_quiz',
    blurbFallback: 'Latihan pilihan ganda + esai.', apiKind: 'quiz',
  },
  podcast: {
    icon: '🎙️', labelKey: 'learning_studio_podcast_script', labelFallback: 'Audio Overview',
    blurbKey: 'learning_dialog_blurb_podcast',
    blurbFallback: 'Dialog dua host membahas materi.', apiKind: 'podcast',
  },
};

// ── Pilihan bersama (dipakai beberapa tipe) ─────────────────────────────────
const DIFFICULTY: StudioOption = {
  id: 'difficulty', kind: 'choice',
  labelKey: 'learning_opt_difficulty', labelFallback: 'Tingkat kesulitan',
  choices: [
    { value: 'easy', labelKey: 'learning_opt_difficulty_easy', labelFallback: 'Mudah' },
    { value: 'mixed', labelKey: 'learning_opt_difficulty_mixed', labelFallback: 'Campuran' },
    { value: 'hard', labelKey: 'learning_opt_difficulty_hard', labelFallback: 'Sulit' },
  ],
};

const LANGUAGE: StudioOption = {
  id: 'language', kind: 'choice',
  labelKey: 'learning_opt_language', labelFallback: 'Bahasa hasil',
  hintKey: 'learning_opt_language_hint', hintFallback: 'Bahasa yang dipakai untuk seluruh hasil.',
  choices: [
    { value: 'auto', labelKey: 'learning_opt_language_auto', labelFallback: 'Ikuti sumbernya' },
    { value: 'id', labelKey: 'learning_opt_lang_id', labelFallback: 'Bahasa Indonesia' },
    { value: 'en', labelKey: 'learning_opt_lang_en', labelFallback: 'English' },
  ],
};

const FOCUS: StudioOption = {
  id: 'focus', kind: 'text', advanced: true,
  labelKey: 'learning_opt_focus', labelFallback: 'Fokus topik (opsional)',
  hintKey: 'learning_opt_focus_hint', hintFallback: 'Batasi materi ke bagian tertentu, mis. “bab 3 saja”.',
  placeholderFallback: 'mis. Bab 3 — Termodinamika',
};

/** Definisi kontrol per tipe Studio. */
export const STUDIO_OPTIONS: Record<StudioKind, StudioOption[]> = {
  // A04: dua counter terpisah (PG & Esai, total ≤ 30) — kontrolnya komponen khusus
  // QuizCountFields, jadi TIDAK didaftarkan di sini agar tidak muncul dua kali.
  quiz: [
    DIFFICULTY,
    LANGUAGE,
    FOCUS,
    {
      id: 'instructions', kind: 'text', advanced: true, rows: 3,
      labelKey: 'learning_opt_custom_instructions', labelFallback: 'Instruksi tambahan',
      hintKey: 'learning_opt_custom_instructions_hint', hintFallback: 'Permintaan bebas yang wajib dipatuhi AI.',
      placeholderFallback: 'mis. Sertakan rumus dan contoh soal hitungan',
    },
  ],
  flashcards: [
    {
      id: 'count', kind: 'number', min: 5, max: 30,
      labelKey: 'learning_flashcard_count_label', labelFallback: 'Jumlah kartu Flashcard',
    },
    {
      id: 'style', kind: 'choice',
      labelKey: 'learning_opt_card_style', labelFallback: 'Gaya kartu',
      choices: [
        { value: 'term', labelKey: 'learning_opt_card_style_term', labelFallback: 'Istilah → Definisi' },
        { value: 'qa', labelKey: 'learning_opt_card_style_qa', labelFallback: 'Pertanyaan → Jawaban' },
        { value: 'formula', labelKey: 'learning_opt_card_style_formula', labelFallback: 'Rumus → Arti' },
      ],
    },
    DIFFICULTY,
    LANGUAGE,
    FOCUS,
  ],
  podcast: [
    {
      id: 'style', kind: 'choice',
      labelKey: 'learning_opt_host_style', labelFallback: 'Gaya pembawa acara',
      choices: [
        { value: 'casual', labelKey: 'learning_opt_host_casual', labelFallback: 'Santai & akrab' },
        { value: 'formal', labelKey: 'learning_opt_host_formal', labelFallback: 'Formal & edukatif' },
        { value: 'debate', labelKey: 'learning_opt_host_debate', labelFallback: 'Diskusi kritis' },
      ],
    },
    {
      id: 'length', kind: 'choice',
      labelKey: 'learning_opt_length', labelFallback: 'Panjang',
      choices: [
        { value: 'short', labelKey: 'learning_opt_length_short', labelFallback: 'Singkat' },
        { value: 'standard', labelKey: 'learning_opt_length_standard', labelFallback: 'Standar' },
        { value: 'deep', labelKey: 'learning_opt_length_deep', labelFallback: 'Mendalam' },
      ],
    },
    LANGUAGE,
    {
      id: 'instructions', kind: 'text', advanced: true, rows: 3,
      labelKey: 'learning_opt_custom_instructions', labelFallback: 'Instruksi tambahan',
      hintKey: 'learning_opt_custom_instructions_hint', hintFallback: 'Permintaan bebas yang wajib dipatuhi AI.',
      placeholderFallback: 'mis. Mulai dengan pertanyaan pemancing, sebut contoh lokal',
    },
    FOCUS,
  ],
  mindmap: [
    {
      id: 'depth', kind: 'number', min: 1, max: 3,
      labelKey: 'learning_opt_depth', labelFallback: 'Kedalaman cabang',
      hintKey: 'learning_opt_depth_hint', hintFallback: '1 = hanya sub, 2–3 = sub bercabang lagi.',
    },
    {
      id: 'branches', kind: 'number', min: 3, max: 8,
      labelKey: 'learning_opt_branches', labelFallback: 'Jumlah cabang utama',
    },
    {
      id: 'subs', kind: 'number', min: 2, max: 6,
      labelKey: 'learning_opt_subs', labelFallback: 'Maks sub per cabang',
    },
    LANGUAGE,
    FOCUS,
  ],
  'study-guide': [
    {
      id: 'sections', kind: 'multi',
      labelKey: 'learning_opt_sections', labelFallback: 'Bagian yang disertakan',
      hintKey: 'learning_opt_sections_hint', hintFallback: 'Minimal satu bagian harus dipilih.',
      multi: [
        { value: 'summary', labelKey: 'learning_opt_section_summary', labelFallback: 'Ringkasan utama' },
        { value: 'concepts', labelKey: 'learning_opt_section_concepts', labelFallback: 'Konsep kunci' },
        { value: 'examples', labelKey: 'learning_opt_section_examples', labelFallback: 'Contoh penting' },
        { value: 'practice', labelKey: 'learning_opt_section_practice', labelFallback: 'Latihan soal' },
        { value: 'conclusion', labelKey: 'learning_opt_section_conclusion', labelFallback: 'Kesimpulan' },
      ],
    },
    {
      id: 'exercises', kind: 'number', min: 3, max: 10,
      labelKey: 'learning_opt_exercises', labelFallback: 'Jumlah soal latihan',
    },
    LANGUAGE,
    FOCUS,
  ],
  faq: [
    {
      id: 'faqCount', kind: 'number', min: 5, max: 15,
      labelKey: 'learning_opt_faq_count', labelFallback: 'Jumlah Q&A',
    },
    {
      id: 'style', kind: 'choice',
      labelKey: 'learning_opt_answer_style', labelFallback: 'Gaya jawaban',
      choices: [
        { value: 'brief', labelKey: 'learning_opt_answer_brief', labelFallback: 'Singkat' },
        { value: 'detail', labelKey: 'learning_opt_answer_detail', labelFallback: 'Detail' },
      ],
    },
    LANGUAGE,
    FOCUS,
  ],
  timeline: [
    {
      id: 'granularity', kind: 'choice',
      labelKey: 'learning_opt_granularity', labelFallback: 'Granularitas waktu',
      choices: [
        { value: 'day', labelKey: 'learning_opt_granularity_day', labelFallback: 'Harian' },
        { value: 'week', labelKey: 'learning_opt_granularity_week', labelFallback: 'Mingguan' },
        { value: 'month', labelKey: 'learning_opt_granularity_month', labelFallback: 'Bulanan' },
        { value: 'year', labelKey: 'learning_opt_granularity_year', labelFallback: 'Tahunan' },
      ],
    },
    {
      id: 'absoluteDates', kind: 'toggle',
      labelKey: 'learning_opt_absolute_dates', labelFallback: 'Sertakan tanggal absolut',
      hintKey: 'learning_opt_absolute_dates_hint', hintFallback: 'Bila sumber tidak punya tanggal pasti, tulis “Tahap n”.',
    },
    LANGUAGE,
    FOCUS,
  ],
  summary: [
    {
      id: 'length', kind: 'choice',
      labelKey: 'learning_opt_length', labelFallback: 'Panjang',
      choices: [
        { value: 'short', labelKey: 'learning_opt_length_short', labelFallback: 'Singkat' },
        { value: 'standard', labelKey: 'learning_opt_length_standard', labelFallback: 'Standar' },
        { value: 'deep', labelKey: 'learning_opt_length_deep', labelFallback: 'Mendalam' },
      ],
    },
    {
      id: 'style', kind: 'choice',
      labelKey: 'learning_opt_summary_style', labelFallback: 'Gaya ringkasan',
      choices: [
        { value: 'bullets', labelKey: 'learning_opt_summary_bullets', labelFallback: 'Poin-poin' },
        { value: 'narrative', labelKey: 'learning_opt_summary_narrative', labelFallback: 'Naratif' },
      ],
    },
    LANGUAGE,
    FOCUS,
  ],
};

/** Nilai default per tipe (sama dengan default dialog). */
export function studioDefaults(kind: StudioKind): Record<string, any> {
  const out: Record<string, any> = {};
  if (kind === 'quiz') {
    out.mc = 10;        // A04: default 10 PG
    out.essay = 5;      // A04: default 5 esai  → total 15
  }
  for (const opt of STUDIO_OPTIONS[kind] || []) {
    if (opt.kind === 'number') out[opt.id] = opt.min ?? 0;
    else if (opt.kind === 'choice') out[opt.id] = opt.choices?.[0]?.value;
    else if (opt.kind === 'toggle') out[opt.id] = true;
    else if (opt.kind === 'multi') out[opt.id] = (opt.multi || []).map((m) => m.value);
    else out[opt.id] = '';
  }
  // Default yang diminta user (bukan nilai terendah slider).
  if (kind === 'quiz') { out.difficulty = 'mixed'; out.language = 'auto'; out.focus = ''; out.instructions = ''; }
  if (kind === 'flashcards') { out.count = 15; out.style = 'qa'; out.difficulty = 'mixed'; out.language = 'auto'; }
  if (kind === 'podcast') { out.style = 'casual'; out.length = 'standard'; out.language = 'auto'; }
  if (kind === 'mindmap') { out.depth = 2; out.branches = 5; out.subs = 3; out.language = 'auto'; }
  if (kind === 'study-guide') { out.exercises = 3; out.language = 'auto'; }
  if (kind === 'faq') { out.faqCount = 8; out.style = 'detail'; out.language = 'auto'; }
  if (kind === 'timeline') { out.granularity = 'month'; out.absoluteDates = true; out.language = 'auto'; }
  if (kind === 'summary') { out.length = 'standard'; out.style = 'bullets'; out.language = 'auto'; }
  return out;
}

export const STUDIO_CFG_PREFIX = 'cl_learning_studio_cfg_';

export function studioConfigKey(notebookId: string | number, kind: StudioKind): string {
  return `${STUDIO_CFG_PREFIX}${notebookId}_${kind}`;
}

/** Pengaturan terakhir untuk notebook+tipe (default bila belum ada / rusak). */
export function loadStudioConfig(notebookId: string | number, kind: StudioKind): Record<string, any> {
  const base = studioDefaults(kind);
  try {
    const raw = localStorage.getItem(studioConfigKey(notebookId, kind));
    if (!raw) return base;
    const saved = JSON.parse(raw);
    if (!saved || typeof saved !== 'object') return base;
    // Hanya kunci yang dikenal yang dipakai — aman terhadap skema lama.
    const known = new Set([...Object.keys(base), 'instructions', 'absoluteDates']);
    for (const [k, v] of Object.entries(saved)) if (known.has(k)) base[k] = v;
    return base;
  } catch {
    return base;
  }
}

export function saveStudioConfig(notebookId: string | number, kind: StudioKind, cfg: Record<string, any>): void {
  try {
    localStorage.setItem(studioConfigKey(notebookId, kind), JSON.stringify({ ...cfg, _at: Date.now() }));
  } catch { /* localStorage penuh/diblokir — abaikan */ }
}

export function resetStudioConfig(notebookId: string | number, kind: StudioKind): Record<string, any> {
  try { localStorage.removeItem(studioConfigKey(notebookId, kind)); } catch { /* ignore */ }
  return studioDefaults(kind);
}

/**
 * Serialisasi konfigurasi → payload API. Nama kunci mengikuti yang divalidasi
 * `studio_api._studio_generate` (camelCase diterima: `faqCount`, `absoluteDates`).
 */
export function buildStudioPayload(kind: StudioKind, cfg: Record<string, any>): Record<string, unknown> {
  const s = (v: any) => String(v ?? '').trim();
  const body: Record<string, unknown> = {};
  const common = () => {
    if (s(cfg.language) && cfg.language !== 'auto') body.language = cfg.language;
    if (s(cfg.focus)) body.focus = s(cfg.focus).slice(0, 200);
    if (s(cfg.instructions)) body.instructions = s(cfg.instructions).slice(0, 600);
  };
  switch (kind) {
    case 'quiz': {
      const mc = Math.max(0, Math.min(30, Number(cfg.mc) || 0));
      const essay = Math.max(0, Math.min(30, Number(cfg.essay) || 0));
      body.count = mc + essay;
      body.mcCount = mc;
      body.essayCount = essay;
      if (cfg.difficulty) body.difficulty = cfg.difficulty;
      common();
      break;
    }
    case 'flashcards':
      body.count = Math.max(5, Math.min(30, Number(cfg.count) || 15));
      if (cfg.style) body.style = cfg.style;
      if (cfg.difficulty) body.difficulty = cfg.difficulty;
      common();
      break;
    case 'podcast':
      if (cfg.style) body.style = cfg.style;
      if (cfg.length) body.length = cfg.length;
      common();
      break;
    case 'mindmap':
      body.depth = Math.max(1, Math.min(3, Number(cfg.depth) || 2));
      body.branches = Math.max(3, Math.min(8, Number(cfg.branches) || 5));
      body.subs = Math.max(2, Math.min(6, Number(cfg.subs) || 3));
      common();
      break;
    case 'study-guide': {
      const secs = Array.isArray(cfg.sections) && cfg.sections.length
        ? cfg.sections
        : (STUDIO_OPTIONS['study-guide'][0].multi || []).map((m) => m.value);
      body.sections = secs;
      body.exercises = Math.max(3, Math.min(10, Number(cfg.exercises) || 3));
      common();
      break;
    }
    case 'faq':
      body.faqCount = Math.max(5, Math.min(15, Number(cfg.faqCount) || 8));
      if (cfg.style) body.style = cfg.style;
      common();
      break;
    case 'timeline':
      if (cfg.granularity) body.granularity = cfg.granularity;
      body.absoluteDates = cfg.absoluteDates !== false;
      common();
      break;
    case 'summary':
      if (cfg.length) body.length = cfg.length;
      if (cfg.style) body.style = cfg.style;
      common();
      break;
  }
  return body;
}

/** Ringkasan pendek untuk baris "Pengaturan terakhir" di panel Studio. */
export function summarizeStudioConfig(
  kind: StudioKind,
  cfg: Record<string, any>,
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string,
): string {
  const label = (opt: StudioOption, value: any) => {
    if (opt.kind === 'choice') {
      const c = (opt.choices || []).find((x) => x.value === value);
      return c ? tr(c.labelKey, {}, c.labelFallback) : String(value ?? '-');
    }
    if (opt.kind === 'toggle') return value === false ? tr('learning_dialog_toggle_off', {}, 'Tidak') : tr('learning_dialog_toggle_on', {}, 'Ya');
    if (opt.kind === 'multi') {
      const arr = Array.isArray(value) ? value : [];
      return `${arr.length}/${(opt.multi || []).length}`;
    }
    return String(value ?? '-');
  };
  const parts: string[] = [];
  if (kind === 'quiz') parts.push(`${tr('learning_quiz_mc_count', {}, 'Jumlah soal pilihan ganda')} ${cfg.mc}`, `${tr('learning_quiz_essay_count', {}, 'Jumlah soal essay')} ${cfg.essay}`);
  for (const opt of STUDIO_OPTIONS[kind] || []) {
    if (opt.advanced || opt.kind === 'text') continue;
    const v = cfg[opt.id];
    if (v === '' || v === undefined || v === null) continue;
    parts.push(`${tr(opt.labelKey, {}, opt.labelFallback)}: ${label(opt, v)}`);
  }
  return parts.join(' · ');
}
