// Parity PomodoroPage._build_alarm_wav — alarm WAV dihasilkan sekali per fase
// lalu diputar berulang (QMediaPlayer setLoops(-1) + loop manual saat EndOfMedia)
// sampai pengguna mengakui alert fase. Alarm pomodoro selalu berbunyi dan TIDAK
// mengikuti setting sound effects (catatan parity dari PyQt).

type PomoPhase = 'focus' | 'break';

const RATE = 44100;
// Pola identik MainPyQt6.py: (freq Hz, durasi detik), 0 = senyap.
const PATTERNS: Record<PomoPhase, Array<[number, number]>> = {
  focus: [[880, 0.18], [0, 0.08], [1175, 0.22], [0, 0.08], [1320, 0.28], [0, 0.22]],
  break: [[660, 0.2], [0, 0.1], [880, 0.24], [0, 0.1], [660, 0.2], [0, 0.25]],
};

function buildBuffer(ctx: AudioContext, phase: PomoPhase): AudioBuffer {
  let total = 0;
  for (const [, d] of PATTERNS[phase]) total += Math.floor(RATE * d);
  const buf = ctx.createBuffer(1, total, RATE);
  const ch = buf.getChannelData(0);
  let off = 0;
  for (const [freq, dur] of PATTERNS[phase]) {
    const count = Math.floor(RATE * dur);
    for (let i = 0; i < count; i++) {
      let sample = 0;
      if (freq !== 0) {
        const fade = Math.min(1, i / (RATE * 0.015), Math.max(0, (count - i) / (RATE * 0.02)));
        sample = 0.32 * fade * Math.sin((2 * Math.PI * freq * i) / RATE);
      }
      ch[off + i] = sample;
    }
    off += count;
  }
  return buf;
}

let audioCtx: AudioContext | null = null;
let source: AudioBufferSourceNode | null = null;
let gainNode: GainNode | null = null;
const bufferCache = new Map<PomoPhase, AudioBuffer>();

export function startPomoAlarm(phase: PomoPhase): void {
  stopPomoAlarm();
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) return;
    audioCtx = audioCtx || new Ctx();
    let buf = bufferCache.get(phase);
    if (!buf || buf.numberOfChannels === 0) {
      buf = buildBuffer(audioCtx, phase);
      bufferCache.set(phase, buf);
    }
    gainNode = audioCtx.createGain();
    gainNode.gain.value = 0.9; // parity _alarm_output.setVolume(0.9)
    gainNode.connect(audioCtx.destination);
    source = audioCtx.createBufferSource();
    source.buffer = buf;
    source.loop = true; // parity setLoops(-1)
    source.connect(gainNode);
    source.start();
    // Resume eksplisit untuk memenuhi kebijakan autoplay browser.
    if (audioCtx.state === 'suspended') audioCtx.resume().catch(() => { /* tetap diam */ });
  } catch {
    /* alarm gagal → abaikan (mirror try/except _start_alarm) */
  }
}

export function stopPomoAlarm(): void {
  try { source?.stop(); } catch { /* sudah berhenti */ }
  source = null;
  try { gainNode?.disconnect(); } catch { /* ignore */ }
  gainNode = null;
}
