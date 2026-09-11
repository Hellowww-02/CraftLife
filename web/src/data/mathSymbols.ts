/**
 * mathSymbols.ts — katalog palette simbol & template matematika (P55).
 *
 * Dipakai menu Σ di NotesView: kategori tab, klik = sisip `insert` di kursor.
 * Item simbol menyisipkan karakter Unicode langsung; item template menyisipkan
 * snippet LaTeX (lalu dikonversi via tombol "Konversi" / pratinjau server).
 */
export interface MathPaletteItem {
  /** Tampilan pada tombol. */
  label: string;
  /** Teks yang disisipkan di kursor editor. */
  insert: string;
  /** Tooltip opsional. */
  title?: string;
}

export interface MathPaletteCategory {
  id: string;
  i18nKey: string;
  fallbackId: string;
  fallbackEn: string;
  items: MathPaletteItem[];
}

const ch = (chars: string[]): MathPaletteItem[] => chars.map((c) => ({ label: c, insert: c }));

export const MATH_PALETTE: MathPaletteCategory[] = [
  {
    id: 'greek',
    i18nKey: 'notes_math_palette_greek',
    fallbackId: 'Yunani',
    fallbackEn: 'Greek',
    items: ch(['α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'π', 'ρ', 'σ', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω', 'ς', 'ϑ', 'ϕ', 'ϖ', 'ϱ', 'Γ', 'Δ', 'Θ', 'Λ', 'Ξ', 'Π', 'Σ', 'Φ', 'Ψ', 'Ω', 'Υ']),
  },
  {
    id: 'operators',
    i18nKey: 'notes_math_palette_operators',
    fallbackId: 'Operator',
    fallbackEn: 'Operators',
    items: ch(['⋅', '×', '÷', '±', '∓', '∗', '⋆', '∘', '•', '⊕', '⊖', '⊗', '⊘', '⊙', '⊛', '⊚', '⊡', '∨', '∧', '∩', '∪', '⊓', '⊔', '⊎', '∐', '≀', '†', '‡', '⊲', '⊳', '⊴', '⊵', '△', '▽', '⋄', '○', '□', '⊺']),
  },
  {
    id: 'arrows',
    i18nKey: 'notes_math_palette_arrows',
    fallbackId: 'Panah',
    fallbackEn: 'Arrows',
    items: ch(['→', '←', '↔', '⇒', '⇐', '⇔', '⟶', '⟵', '⟷', '⟹', '⟸', '⟺', '↦', '⟼', '⇀', '↼', '↪', '↩', '↑', '↓', '↕', '⇑', '⇓', '⇕', '↗', '↘', '↙', '↖', '⇌', '⇉', '⇇', '⇢', '⇠', '↻', '↺', '↷', '↶', '↛', '↚', '⇏', '⇎']),
  },
  {
    id: 'relations',
    i18nKey: 'notes_math_palette_relations',
    fallbackId: 'Relasi',
    fallbackEn: 'Relations',
    items: ch(['≤', '≥', '≠', '≈', '≃', '≅', '≍', '≡', '∝', '∼', '≪', '≫', '≺', '≻', '≼', '≽', '⪯', '⪰', '⊂', '⊃', '⊆', '⊇', '⊊', '⊋', '⊈', '⊉', '∈', '∉', '∋', '∣', '∤', '∥', '∦', '⊥', '⊨', '⊢', '⊣', '⋈', '≰', '≱', '≶', '≷', '≲', '≳', '≜', '≔', '≕', '⋪', '⋫']),
  },
  {
    id: 'calculus',
    i18nKey: 'notes_math_palette_calculus',
    fallbackId: 'Kalkulus',
    fallbackEn: 'Calculus',
    items: [
      ...ch(['∑', '∏', '∐', '∫', '∬', '∭', '∮', '∯', '∰', '∂', '∇', '∞', '√', '∟', '∠', '∡', '∢', '…', '⋯', '⋮', '⋱']),
      { label: 'lim', insert: 'lim', title: '\\lim' },
      { label: 'log', insert: 'log', title: '\\log' },
      { label: 'ln', insert: 'ln', title: '\\ln' },
      { label: 'sin', insert: 'sin', title: '\\sin' },
      { label: 'cos', insert: 'cos', title: '\\cos' },
      { label: 'tan', insert: 'tan', title: '\\tan' },
    ],
  },
  {
    id: 'letters',
    i18nKey: 'notes_math_palette_letters',
    fallbackId: 'Huruf Khusus',
    fallbackEn: 'Special Letters',
    items: ch(['ℵ', 'ℶ', 'ℷ', 'ℸ', 'ℏ', 'ℓ', '℘', 'ℜ', 'ℑ', 'ı', 'ȷ', '𝕜', '∅', '∀', '∃', '∄', '¬', '⊤', '∁', '𝜶', '𝜷', '𝜸', '𝜹', '𝜽', '𝝀', '𝝁', '𝝈', '𝝅', '𝝍', '𝝎', '𝚪', '𝚫', '𝚯', '𝚲', '𝚷', '𝚺', '𝚽', '𝛀']),
  },
  {
    id: 'templates',
    i18nKey: 'notes_math_palette_templates',
    fallbackId: 'Template',
    fallbackEn: 'Templates',
    items: [
      { label: 'a/b', insert: '\\frac{a}{b}', title: '\\frac{}{}' },
      { label: '(a+b)/(c+d)', insert: '\\frac{a+b}{c+d}', title: '\\frac pecahan majemuk' },
      { label: 'ⁿ√(x)', insert: '\\sqrt[3]{x}', title: '\\sqrt[n]{}' },
      { label: '√(x)', insert: '\\sqrt{x}', title: '\\sqrt{}' },
      { label: 'C(n,k)', insert: '\\binom{n}{k}', title: '\\binom{}{}' },
      { label: 'x̅', insert: '\\overline{x}', title: '\\overline{}' },
      { label: 'x̲', insert: '\\underline{x}', title: '\\underline{}' },
      { label: 'v⃗', insert: '\\vec{v}', title: '\\vec{}' },
      { label: 'â', insert: '\\hat{a}', title: '\\hat{}' },
      { label: 'ã', insert: '\\tilde{a}', title: '\\tilde{}' },
      { label: 'x̄', insert: '\\bar{x}', title: '\\bar{}' },
      { label: 'ẋ', insert: '\\dot{x}', title: '\\dot{}' },
      { label: 'ẍ', insert: '\\ddot{x}', title: '\\ddot{}' },
      { label: '=ᵈᵉᶠ', insert: '\\overset{\\mathrm{def}}{=}', title: '\\overset{}{}' },
      { label: '∑ᵢ₌₁', insert: '\\underset{i=1}{\\sum}', title: '\\underset{}{}' },
      { label: '𝜶', insert: '\\boldsymbol{\\alpha}', title: '\\boldsymbol{}' },
      { label: 'ⁱ⁼¹ⁿ', insert: '\\substack{i=1 \\\\ n}', title: '\\substack{}' },
      { label: '⟶ᵗᵉˣᵗ', insert: '\\xrightarrow{\\text{teks}}', title: '\\xrightarrow{}' },
      { label: '{x│y', insert: '\\begin{cases} x=1 \\\\ y=2 \\end{cases}', title: 'cases' },
      { label: '(a b; c d)', insert: '\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}', title: 'pmatrix' },
    ],
  },
];
