// WebAudio reminder alarm sounds — parity with PyQt RemindersPage `_play_sound`.
// Generates the four alarm types (beep / bell / magic / fanfare) on the fly
// using OscillatorNode(s), so no audio assets or network access are required.

export type ReminderSound =
  | 'default' | 'beep1' | 'beep2' | 'custom'           // ← PyQt (parity)
  | 'beep' | 'bell' | 'magic' | 'fanfare';             // ← alias web lama (kompat beep1/default)

function ctx(): AudioContext | null {
  try {
    const AC = window.AudioContext || (window as any).webkitAudioContext;
    const c = new AC();
    if (c.state === 'suspended') c.resume();
    return c;
  } catch {
    return null;
  }
}

function tone(c: AudioContext, freq: number, start: number, dur: number, type: OscillatorType = 'sine', vol = 0.12) {
  const o = c.createOscillator();
  const g = c.createGain();
  o.type = type;
  o.frequency.value = freq;
  g.gain.setValueAtTime(0, c.currentTime + start);
  g.gain.linearRampToValueAtTime(vol, c.currentTime + start + 0.01);
  g.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + start + dur);
  o.connect(g);
  g.connect(c.destination);
  o.start(c.currentTime + start);
  o.stop(c.currentTime + start + dur + 0.05);
}

/** Play an alarm sound. Sound types mirror PyQt beep1/beep2/bell/magic/fanfare. */
export function playReminderSound(sound: ReminderSound = 'bell') {
  const c = ctx();
  if (!c) return;
  switch (sound) {
    case 'beep1':
    case 'beep':
      // PyQt _play_sound beep1: 600Hz/200ms → 800Hz/200ms
      tone(c, 600, 0, 0.2, 'square');
      tone(c, 800, 0.22, 0.2, 'square');
      break;
    case 'beep2':
      // PyQt beep2: 400/300 → 600/300 → 800/300
      tone(c, 400, 0, 0.3, 'square');
      tone(c, 600, 0.32, 0.3, 'square');
      tone(c, 800, 0.64, 0.3, 'square');
      break;
    case 'magic':
      tone(c, 523.25, 0, 0.25, 'sine');      // C5
      tone(c, 659.25, 0.22, 0.25, 'sine');    // E5
      tone(c, 783.99, 0.44, 0.3, 'sine');     // G5
      break;
    case 'fanfare':
      tone(c, 523.25, 0, 0.16, 'triangle');
      tone(c, 587.33, 0.14, 0.16, 'triangle');
      tone(c, 659.25, 0.28, 0.16, 'triangle');
      tone(c, 783.99, 0.42, 0.4, 'triangle');
      break;
    case 'bell':
    default:
      tone(c, 1000, 0, 0.4, 'sine', 0.14);
      tone(c, 1300, 0, 0.4, 'sine', 0.06);
      break;
  }
  // Close the context after the sound finishes to free resources.
  const total = 900;
  setTimeout(() => { try { c.close(); } catch { /* ignore */ } }, total);
}

// ── Loop alarm (parity MainWindow._play_reminder_*_loop, interval 2 detik) ──
let _loopStop: (() => void) | null = null;

/** Hentikan loop alarm yang sedang berjalan (parity _stop_reminder_sounds). */
export function stopReminderLoop() {
  try { _loopStop?.(); } catch { /* ignore */ }
  _loopStop = null;
}

/**
 * Mulai loop alarm sampai stopReminderLoop() dipanggil.
 * - custom: HTMLAudio MP3 loop (parity _play_reminder_mp3_loop)
 * - beep1/beep2/default: beep diulang tiap 2 detik (parity beep timer 2000ms)
 * Mengembalikan true jika loop custom (elemen audio) dimulai.
 */
export function startReminderLoop(sound: string, fileUrl?: string): void {
  stopReminderLoop();
  if (sound === 'custom' && fileUrl) {
    try {
      const el = new Audio(fileUrl);
      el.loop = true;
      void el.play().catch(() => { /* autoplay diblok → diabaikan */ });
      _loopStop = () => { try { el.pause(); el.src = ''; } catch { /* ignore */ } };
      return;
    } catch { /* jatuh ke beep */ }
  }
  playReminderSound((sound as ReminderSound) || 'default');
  const id = window.setInterval(() => playReminderSound((sound as ReminderSound) || 'default'), 2000);
  _loopStop = () => window.clearInterval(id);
}
