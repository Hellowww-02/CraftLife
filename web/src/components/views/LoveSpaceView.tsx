import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { NumberInput } from '../NumberInput';
import { useGame } from '../../context/GameContext';
import { t } from '../../i18n';
import { studio } from '../../api/studio';
import { apiUploadFile } from '../../api/client';
import { X } from 'lucide-react';
import {
  Heart,
  MessageSquareHeart,
  Camera,
  Plus,
  Trash2,
  Pencil,
  FolderOpen,
  Images,
  CheckSquare,
  Square,
  Shuffle,
  Star,
  Eye,
  EyeOff,
  Calendar,
  CalendarDays,
  MapPin,
  Bell,
  Repeat,
  Search,
  ChevronDown,
  ChevronRight,
  Sparkles,
  ListChecks,
  StickyNote,
  Image as ImageIcon,
  Clock,
  AlertTriangle,
  CheckCircle2,
  SlidersHorizontal,
} from 'lucide-react';
import LoveEventDialog, { EVENT_CATEGORIES, LoveEventForm } from '../love/LoveEventDialog';
import LoveMemoryDialog, { LoveMemoryForm } from '../love/LoveMemoryDialog';
import LoveBucketDialog, { LoveBucketForm } from '../love/LoveBucketDialog';
// A11: tab connection/cycle/gallery dipindah ke panel tersendiri + helper galeri
// (PhotoThumb/Modal/ZoomableViewer) dibagikan lewat `love/galleryParts`.
import { LoveConnectionPanel } from '../love/LoveConnectionPanel';
import { LoveCyclePanel } from '../love/LoveCyclePanel';
import { LoveGalleryPanel } from '../love/LoveGalleryPanel';
// A12: tab overview = dashboard pasangan (hero hari bersama, hari istimewa,
// cincin skor kedekatan, statistik, aksi cepat) + pemilih pengingat tahunan.
import { LoveOverviewPanel } from '../love/LoveOverviewPanel';
import type { UpcomingItem } from '../love/overviewUtils';
import { Modal, PhotoThumb, ZoomableViewer } from '../love/galleryParts';
import { badgeKind, groupEvents } from '../love/eventUtils';
import {
  bucketCategoryIcon,
  bucketProgressText,
  bucketStats as computeBucketStats,
  filterBucket,
  filterMemories,
  memoryFacets,
  normalizeTags,
  tagsToInput,
  targetBadge,
  type BucketFilter,
  type MemorySort,
} from '../love/memoryUtils';

/* A11: PhotoThumb / ViewerImage / ZoomableViewer / Modal kini di `love/galleryParts.tsx`
   (dipakai bersama tab galeri & sisa dialog di berkas ini). */

const trv = (key: string, vars: Record<string, string | number>, fb: string): string =>
  Object.entries(vars).reduce((acc, [k, v]) => acc.split(`{${k}}`).join(String(v)), t(key, fb));

const MOODS: Array<[number, string]> = [[1, '😞'], [2, '😕'], [3, '😐'], [4, '🙂'], [5, '🥰']];
/* A11: bank PROMPTS kini di `love/connectionUtils.ts` (dipakai panel connection). */

type TabId = 'overview' | 'connection' | 'cycle' | 'memories' | 'gallery' | 'plans';

const LOVE_TABS: TabId[] = ['overview', 'connection', 'cycle', 'memories', 'gallery', 'plans'];

/**
 * Sub-tab awal Love Space. Mendukung tautan langsung (deep-link) `?loveTab=plans`
 * — pola yang sama dengan `?login=1` di App.tsx — sehingga halaman bisa dibuka
 * langsung ke bagian yang dituju (dan memudahkan pengujian render).
 */
function initialLoveTab(): TabId {
  if (typeof window === 'undefined') return 'overview';
  try {
    const params = new URLSearchParams(window.location.search);
    const wanted = String(params.get('loveTab') || params.get('love_tab') || '').toLowerCase();
    if ((LOVE_TABS as string[]).includes(wanted)) return wanted as TabId;
  } catch { /* lingkungan tanpa URLSearchParams — pakai default */ }
  return 'overview';
}

const inputCls = 'ct-input w-full px-2 py-1.5 rounded-lg text-slate-200 text-xs';
/** Label cadangan filter Bucket List (nilai i18n `love_bucket_filter_*` tidak memuat {n}). */
const BUCKET_FILTER_FALLBACK: Record<BucketFilter, string> = {
  all: 'Semua', open: 'Belum', done: 'Selesai', late: 'Terlewat',
};
const btnRose = 'ct-btn ct-btn-rose ct-btn-sm';
const btnGhost = 'ct-btn ct-btn-secondary ct-btn-sm';
const btnDanger = 'ct-btn ct-btn-danger ct-btn-sm';

/**
 * Love Space. `onNavigate` opsional dipakai aksi cepat tab overview (A12) untuk
 * melompat ke halaman lain — mis. "Lihat pengingat" → halaman Reminders.
 */
export const LoveSpaceView: React.FC<{ onNavigate?: (view: string) => void }> = ({ onNavigate }) => {
  const {
    user,
    loveSpace,
    updateLoveSpace,
    loveCheckin,
    loveEvent,
    updateLoveEvent,
    loveWeekly,
    loveCycle,
    addLoveCycle,
    updateLoveCycle,
    loveCycleReminder,
    loveEventReminder,
    loveAlbumCover,
    lovePhotosBulk,
    updateLovePhotoMeta,
    addLoveMemory,
    updateLoveMemory,
    loveMemoryFavorite,
    updateLoveBucket,
    promoteLoveBucket,
    refreshLoveSpace,
    deleteLoveMemory,
    deleteLovePrompt,
    deleteLoveWeekly,
    deleteLoveCycle,
    deleteLoveEvent,
    deleteLoveBucket,
    deleteLovePhoto,
    toggleLoveBucketItem,
    lovePromptFavorite,
    createLoveAlbum,
    renameLoveAlbum,
    deleteLoveAlbum,
    loveAlbumAddPhoto,
    loveAlbumMovePhoto,
    loveAlbumRemovePhoto,
    showToast,
    today,
    nowDate,
  } = useGame();

  const [tab, setTab] = useState<TabId>(initialLoveTab);

  // ── Overview (A12) ──────────────────────────────────────────────────
  // Form check-in + riwayatnya kini tinggal di `LoveOverviewPanel` (state mood
  // dipindah ke sana), jadi yang tersisa di sini adalah data hari istimewa:
  // `GET /api/love/events/upcoming?days=365` (acara `yearly` + ulang tahun &
  // hari jadi dari profil, 29 Feb sudah diamankan server).
  const [upcoming, setUpcoming] = useState<UpcomingItem[]>([]);
  const [upcomingLoading, setUpcomingLoading] = useState(false);

  const loadUpcoming = useCallback(() => {
    setUpcomingLoading(true);
    studio.loveEventsUpcoming(365)
      .then((res: any) => {
        const rows = res?.items || res?.result?.items || res?.events || [];
        setUpcoming(Array.isArray(rows) ? rows : []);
      })
      .catch(() => setUpcoming([]))
      .finally(() => setUpcomingLoading(false));
  }, []);

  useEffect(() => { loadUpcoming(); }, [loadUpcoming]);

  // A11: state & handler prompt/riwayat/review mingguan kini milik
  // `LoveConnectionPanel`, begitu pula pengaturan + riwayat siklus milik
  // `LoveCyclePanel` (dulu keduanya menumpuk di komponen ini).

  // ── Memories ────────────────────────────────────────────────────────
  // A10 — tab memories: dialog Tambah/Edit (emoji, tag, favorit, tautan foto) +
  // toolbar pencarian/filter tahun/filter tag/hanya favorit/urutan. State lama
  // (`showAddMemModal` + 3 field terpisah) digantikan dialog yang sama untuk
  // mode tambah & edit, karena kenangan dulu tidak bisa diedit sama sekali.
  const [memDialog, setMemDialog] = useState<{ mode: 'add' | 'edit'; initial: Partial<LoveMemoryForm> | null; nonce: number } | null>(null);
  const [memSaving, setMemSaving] = useState(false);
  const [memSearch, setMemSearch] = useState('');
  const [memYear, setMemYear] = useState<string>('');
  const [memTag, setMemTag] = useState<string>('');
  const [memOnlyFav, setMemOnlyFav] = useState(false);
  const [memSort, setMemSort] = useState<MemorySort>('newest');

  // ── Plans ───────────────────────────────────────────────────────────
  // A09 — tab plans: dialog Tambah/Edit acara + pencarian/filter + kelompok waktu.
  // (Sebelumnya ada state `evTitle/evDate/evCategory/evNotes`, tetapi `evNotes` tidak
  //  pernah terhubung ke input mana pun → catatan mustahil diisi. Kini semuanya lewat dialog.)
  const [evDialog, setEvDialog] = useState<{ mode: 'add' | 'edit'; initial: Partial<LoveEventForm> | null; nonce: number } | null>(null);
  const [evSaving, setEvSaving] = useState(false);
  const [evSearch, setEvSearch] = useState('');
  const [evCat, setEvCat] = useState<string>('all');
  const [evOnlySpecial, setEvOnlySpecial] = useState(false);
  const [evShowPast, setEvShowPast] = useState(false);
  // A10 — Bucket List: tambah cepat (parity perilaku lama) + dialog lengkap
  // (kategori, target tanggal, catatan, prioritas) + filter & promosi ke kenangan.
  const [bucketQuick, setBucketQuick] = useState('');
  const [bucketDialog, setBucketDialog] = useState<{ mode: 'add' | 'edit'; initial: Partial<LoveBucketForm> | null; nonce: number } | null>(null);
  const [bucketSaving, setBucketSaving] = useState(false);
  const [bucketFilter, setBucketFilter] = useState<BucketFilter>('all');
  const [bucketSearch, setBucketSearch] = useState('');

  // A11: state galeri (filter, album, mode pilih, lightbox, sampul) kini milik
  // `LoveGalleryPanel`; di sini hanya tersisa alur unggah foto (antrean + dialog).
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadQueue, setUploadQueue] = useState<File[]>([]);
  const [uploadIdx, setUploadIdx] = useState(-1);
  const [upCaption, setUpCaption] = useState('');
  const [upDate, setUpDate] = useState(today);
  const [upVis, setUpVis] = useState<'private' | 'shared'>('private');
  const upStats = useRef({ ok: 0, fail: 0 });

  // ── Profile edit (parity _LoveProfileDialog: sisi kamu + pasangan + relasi) ──
  const [showTracking, setShowTracking] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [profPartner, setProfPartner] = useState(loveSpace.partnerName || '');
  const [profMy, setProfMy] = useState((loveSpace as any).myName || '');
  const [profStart, setProfStart] = useState((loveSpace as any).startDate || loveSpace.anniversaryDate || today);
  const [profMyGender, setProfMyGender] = useState((loveSpace as any).myGender || 'male');
  const [profMyAge, setProfMyAge] = useState((loveSpace as any).myAge || 25);
  const [profMyBirth, setProfMyBirth] = useState((loveSpace as any).myBirthdate || '');
  const [profPartnerGender, setProfPartnerGender] = useState((loveSpace as any).partnerGender || 'female');
  const [profPartnerAge, setProfPartnerAge] = useState((loveSpace as any).partnerAge || 25);
  const [profPartnerBirth, setProfPartnerBirth] = useState((loveSpace as any).partnerBirthdate || '');
  const [profRelType, setProfRelType] = useState((loveSpace as any).relationshipType || 'dating');

  const openProfile = () => {
    setProfPartner(loveSpace.partnerName || '');
    setProfMy((loveSpace as any).myName || '');
    setProfStart((loveSpace as any).startDate || loveSpace.anniversaryDate || today);
    setProfMyGender((loveSpace as any).myGender || 'male');
    setProfMyAge((loveSpace as any).myAge || 25);
    setProfMyBirth((loveSpace as any).myBirthdate || '');
    setProfPartnerGender((loveSpace as any).partnerGender || 'female');
    setProfPartnerAge((loveSpace as any).partnerAge || 25);
    setProfPartnerBirth((loveSpace as any).partnerBirthdate || '');
    setProfRelType((loveSpace as any).relationshipType || 'dating');
    setShowProfile(true);
  };

  const saveProfile = () => {
    if (!profPartner.trim()) {
      showToast('info', t('gagal_title', 'Gagal'), t('love_partner_required', 'Partner name is required.'));
      return;
    }
    updateLoveSpace({
      partnerName: profPartner.trim(),
      myName: profMy.trim(),
      startDate: profStart,
      myGender: profMyGender,
      myAge: profMyAge,
      myBirthdate: profMyBirth,
      partnerGender: profPartnerGender,
      partnerAge: profPartnerAge,
      partnerBirthdate: profPartnerBirth,
      relationshipType: profRelType,
    });
    setShowProfile(false);
  };

  // ── Couple account (parity CoupleTrackingDialog: 11 sub-tab per pasangan) ──
  const [tracking, setTracking] = useState<any>(null);
  const [trackingTab, setTrackingTab] = useState(0);
  const openTracking = () => {
    setShowTracking(true);
    setTracking(null);
    setTrackingTab(0);
    studio.loveCoupleTracking().then((r) => setTracking(r)).catch(() => setTracking({ ok: false }));
  };

  const coupleActive = !!loveSpace.coupleActive;
  // P61: akun pasangan couple + jumlah permintaan pending (badge status).
  const couplePartner = (loveSpace as any).couplePartner as
    { displayName: string; username: string; avatarEmoji: string; avatarColor: string; level: number } | null | undefined;
  const couplePending = Number((loveSpace as any).couplePending) || 0;

  const daysTogether = useMemo(() => {
    try {
      const start = new Date((loveSpace as any).startDate || loveSpace.anniversaryDate);
      return Math.max(1, Math.ceil(Math.abs(Date.now() - start.getTime()) / 86400000));
    } catch { return 1; }
  }, [loveSpace]);

  const futureEvents = useMemo(() =>
    (loveSpace.events || [])
      .filter((e) => e.date >= today)
      .sort((a, b) => a.date.localeCompare(b.date)),
  [loveSpace.events, today]);

  const nextEvent = futureEvents[0];

  // ── Hero parity LovePage.load(): format couple + status link + health sync ──
  const linkedUsername = (loveSpace as any).linkedPartnerUsername || '';
  const cloudLoveActive = !!(loveSpace as any).cloudLoveActive;
  const coupleStatusText = useMemo(() => {
    let s = linkedUsername
      ? trv('love_couple_linked', { username: linkedUsername }, `Shared Love Space active with @${linkedUsername}`)
      : t('love_couple_not_linked', 'Private local space');
    if (cloudLoveActive) s += ` · ${t('love_cloud_realtime', 'Online · realtime')}`;
    return s;
  }, [linkedUsername, cloudLoveActive]);
  const hp = (loveSpace as any).healthProfile || { gender: 'male', age: 25 };
  const healthSyncText = useMemo(() => {
    const genderLabel = String(hp.gender || 'male').toLowerCase() === 'female'
      ? t('food_bmi_gender_f', 'Perempuan') : t('food_bmi_gender_m', 'Laki-laki');
    return trv('love_health_sync', { gender: genderLabel, age: hp.age }, '');
  }, [hp.gender, hp.age]);

  // ── Upload flow (parity _upload_gallery_photo + _GalleryPhotoDialog) ──
  const UPLOAD_MAX = 8 * 1024 * 1024;
  const onPickFiles = (files: FileList | null) => {
    if (!files || !files.length) return;
    upStats.current = { ok: 0, fail: 0 };
    setUploadQueue(Array.from(files));
    setUpCaption(''); setUpDate(today); setUpVis('private');
    setUploadIdx(0);
  };

  const processUpload = async (applyMeta: boolean) => {
    const f = uploadQueue[uploadIdx];
    if (!f) return;
    if (f.size > UPLOAD_MAX) {
      upStats.current.fail++;
    } else {
      try {
        const res: any = await apiUploadFile('love_photo', f, applyMeta
          ? { caption: upCaption, photoDate: upDate, visibility: upVis }
          : { visibility: 'private' });
        if (res?.result?.ok || res?.ok) upStats.current.ok++;
        else upStats.current.fail++;
      } catch { upStats.current.fail++; }
    }
    const next = uploadIdx + 1;
    if (next < uploadQueue.length) {
      setUpCaption(''); setUpDate(today); setUpVis('private');
      setUploadIdx(next);
    } else {
      setUploadIdx(-1); setUploadQueue([]);
      const { ok, fail } = upStats.current;
      showToast(fail ? 'info' : 'success',
        fail ? t('gagal_title', 'Gagal') : t('berhasil_title', 'Berhasil'),
        trv('love_gallery_multi_result', { ok, fail }, '{ok} foto berhasil, {fail} gagal.'));
      refreshLoveSpace();
    }
  };

  // A11: aksi massal memakai satu endpoint `/api/love/photos/bulk` (dulu klien
  // memanggil hapus/ubah-visibilitas satu per satu sehingga rawan setengah jalan).
  const galleryBulk = (payload: { action: 'delete' | 'visibility' | 'move'; ids: string[]; albumId?: string; visibility?: string }) => {
    if (!payload.ids.length) {
      showToast('info', t('msg_error', 'Error'), t('love_gallery_none_selected', 'Pilih foto dulu.'));
      return;
    }
    lovePhotosBulk(payload);
    showToast('success', t('berhasil_title', 'Berhasil'), payload.action === 'delete'
      ? t('love_gallery_bulk_deleted', 'Foto terpilih dihapus.')
      : payload.action === 'move'
        ? t('love_gallery_bulk_moved', 'Foto terpilih dipindahkan ke album.')
        : t('love_gallery_bulk_visibility', 'Visibilitas foto terpilih diperbarui.'));
  };

  // ══════════════════ A09: turunan data tab plans ══════════════════
  /** Label hitung mundur yang ramah ("Hari ini!", "Besok!", "12 hari lagi"). */
  const evCountdown = (days: number | null) => {
    if (days === null) return '';
    if (days === 0) return t('love_event_today', 'Hari ini!');
    if (days === 1) return t('love_event_tomorrow', 'Besok!');
    if (days < 0) return trv('love_event_days_ago', { n: Math.abs(days) }, `${Math.abs(days)} hari lalu`);
    return trv('love_event_in_days', { n: days }, `${days} hari lagi`);
  };
  const evBadge = (days: number | null) => {
    if (days === null) return '—';
    const kind = badgeKind(days);
    if (kind === 'today') return t('love_event_today', 'Hari ini!');
    if (kind === 'past') return `+${Math.abs(days)}`;
    return `H-${days}`;
  };
  const evCategoryMeta = (id: string) =>
    EVENT_CATEGORIES.find((c) => c.id === id) || { id: 'date' as const, icon: '💕' };

  // A09: pengelompokan/search/filter dihitung modul murni `love/eventUtils.ts`
  // (dipakai bersama dialog & bisa diuji tanpa DOM).
  const evData = useMemo(
    () => groupEvents(loveSpace.events || [], { query: evSearch, category: evCat, onlySpecial: evOnlySpecial }, today),
    [loveSpace.events, evSearch, evCat, evOnlySpecial, today],
  );

  /** Hari istimewa terdekat — dari server bila ada (sudah termasuk ulang tahun/anniversary
   *  dari profil), dengan cadangan perhitungan lokal agar UI tetap hidup offline. */
  const specialChips: any[] = useMemo(() => {
    const fromServer = (loveSpace as any).specialDays;
    if (Array.isArray(fromServer) && fromServer.length) return fromServer.slice(0, 4);
    return evData.upcoming.filter((e: any) => e.isSpecial).slice(0, 4).map((e: any) => ({
      id: `local-${e.id}`,
      title: e.title,
      icon: e.icon || evCategoryMeta(e.category).icon,
      nextDate: e.nextDate,
      daysUntil: e.daysUntil,
    }));
  }, [loveSpace, evData]);

  const openEventDialog = (ev?: any) => {
    // `nonce` membuat dialog selalu di-mount ulang saat dibuka → nilai awal selalu segar
    // (tidak menyisakan isian dialog sebelumnya).
    const nonce = Date.now();
    if (!ev) {
      setEvDialog({ mode: 'add', initial: { date: today, category: 'date' }, nonce });
      return;
    }
    setEvDialog({
      mode: 'edit',
      nonce,
      initial: {
        id: String(ev.id),
        title: ev.title || '',
        date: ev.date || today,
        category: ev.category || 'date',
        icon: ev.icon || '',
        location: ev.location || '',
        notes: ev.notes || '',
        isSpecial: !!ev.isSpecial,
        recurring: ev.recurring === 'yearly' ? 'yearly' : 'none',
        remindDaysBefore: Number(ev.remindDaysBefore || 0),
      },
    });
  };

  /** Simpan acara (tambah atau edit) — lalu segarkan snapshot supaya kartu langsung berubah. */
  const saveEvent = async (data: LoveEventForm) => {
    const body: Record<string, unknown> = {
      title: data.title,
      date: data.date,
      category: data.category,
      icon: data.icon,
      location: data.location,
      notes: data.notes,
      isSpecial: data.isSpecial,
      recurring: data.recurring,
      remindDaysBefore: data.remindDaysBefore,
    };
    setEvSaving(true);
    try {
      if (data.id) {
        await studio.loveEventUpdate(data.id, body);
        showToast('success', t('love_event_updated', 'Acara diperbarui'), data.title);
      } else {
        await studio.loveEvent(body);
        showToast('success', t('love_event_added', 'Acara ditambahkan'), data.title);
      }
      refreshLoveSpace();
      setEvDialog(null);
    } catch (e) {
      showToast('damage', t('msg_error', 'Error'), String((e as any)?.message || e));
    } finally {
      setEvSaving(false);
    }
  };

  // ══════════════════ A10: turunan data tab memories ══════════════════
  const memView = useMemo(
    () => filterMemories(loveSpace.memories || [], {
      query: memSearch, year: memYear, tag: memTag, onlyFav: memOnlyFav, sort: memSort,
    }),
    [loveSpace.memories, memSearch, memYear, memTag, memOnlyFav, memSort],
  );
  const memFacets = useMemo(() => memoryFacets(loveSpace.memories || []), [loveSpace.memories]);
  const memStats = (loveSpace as any).memoryStats || {
    total: memView.total, favorites: memView.favorites, tagged: 0, withPhoto: memView.withPhoto,
  };
  const memPhotoOf = (photoId: string) =>
    (loveSpace.photos || []).find((p: any) => String(p.id) === String(photoId)) || { id: photoId };

  const openMemoryDialog = (m?: any) => {
    const nonce = Date.now();
    if (!m) {
      setMemDialog({ mode: 'add', nonce, initial: { date: today, emoji: '💖' } });
      return;
    }
    setMemDialog({
      mode: 'edit',
      nonce,
      initial: {
        id: String(m.id),
        title: m.title || '',
        date: (m.date || today).slice(0, 10),
        description: m.description || '',
        emoji: m.emoji || '💖',
        tags: tagsToInput(m.tags || []),
        isFavorite: !!m.isFavorite,
        photoId: m.photoId || '',
      },
    });
  };

  /** Simpan kenangan (tambah/edit) lalu segarkan snapshot. */
  const saveMemory = async (data: LoveMemoryForm) => {
    const body = {
      title: data.title,
      date: data.date,
      description: data.description,
      emoji: data.emoji,
      tags: normalizeTags(data.tags).join(', '),
      isFavorite: data.isFavorite,
      photoId: data.photoId || '',
    };
    setMemSaving(true);
    try {
      if (data.id) {
        await studio.loveMemoryUpdate(data.id, body);
        showToast('success', t('love_memory_updated', 'Kenangan diperbarui'), data.title);
      } else {
        await studio.addMemory(body);
        showToast('success', t('love_memory_added', 'Kenangan ditambahkan'), data.title);
      }
      refreshLoveSpace();
      setMemDialog(null);
    } catch (e) {
      showToast('damage', t('msg_error', 'Error'), String((e as any)?.message || e));
    } finally {
      setMemSaving(false);
    }
  };

  // ══════════════════ A10: turunan data bucket list ══════════════════
  const bucketStat = useMemo(
    () => computeBucketStats(loveSpace.bucketList || [], today),
    [loveSpace.bucketList, today],
  );
  const bucketView = useMemo(
    () => filterBucket(loveSpace.bucketList || [], bucketFilter, bucketSearch, today),
    [loveSpace.bucketList, bucketFilter, bucketSearch, today],
  );
  const bucketFilterCount = (id: BucketFilter) =>
    filterBucket(loveSpace.bucketList || [], id, bucketSearch, today).length;
  const bucketTargetLabel = (b: any) => {
    const kind = targetBadge(b.daysToTarget);
    if (kind === 'none') return '';
    if (kind === 'overdue') return trv('love_bucket_overdue_days', { n: Math.abs(b.daysToTarget) },
      `terlewat ${Math.abs(b.daysToTarget)} hari`);
    if (kind === 'today') return t('love_event_today', 'Hari ini!');
    return trv('love_bucket_h_days', { n: b.daysToTarget }, `H-${b.daysToTarget}`);
  };

  const openBucketDialog = (b?: any) => {
    const nonce = Date.now();
    if (!b) {
      setBucketDialog({ mode: 'add', nonce, initial: { category: 'dream' } });
      return;
    }
    setBucketDialog({
      mode: 'edit',
      nonce,
      initial: {
        id: String(b.id),
        title: b.title || '',
        category: b.category || 'dream',
        targetDate: b.targetDate || '',
        notes: b.notes || '',
        priority: Number(b.priority || 0),
        isCompleted: !!b.isCompleted,
      },
    });
  };

  /** Simpan item bucket (tambah/edit). */
  const saveBucket = async (data: LoveBucketForm) => {
    setBucketSaving(true);
    try {
      if (data.id) {
        await studio.loveBucketUpdate(data.id, {
          title: data.title,
          category: data.category,
          targetDate: data.targetDate,
          notes: data.notes,
          priority: data.priority,
          isDone: data.isCompleted,
        });
        showToast('success', t('love_bucket_updated', 'Item diperbarui'), data.title);
      } else {
        await studio.addBucket({
          title: data.title,
          category: data.category,
          targetDate: data.targetDate,
          notes: data.notes,
          priority: data.priority,
        });
        showToast('success', t('love_bucket_added', 'Item ditambahkan'), data.title);
      }
      refreshLoveSpace();
      setBucketDialog(null);
    } catch (e) {
      showToast('damage', t('msg_error', 'Error'), String((e as any)?.message || e));
    } finally {
      setBucketSaving(false);
    }
  };

  /** Tambah cepat (judul saja) — perilaku lama dipertahankan. */
  const quickAddBucket = () => {
    const title = bucketQuick.trim();
    if (!title) return;
    studio.addBucket({ title })
      .then(() => { refreshLoveSpace(); showToast('success', t('love_bucket_added', 'Item ditambahkan'), title); })
      .catch((e) => showToast('damage', t('msg_error', 'Error'), String(e?.message || e)));
    setBucketQuick('');
  };

  /** Tandai selesai/belum selesai lewat endpoint update (completed_at ikut benar). */
  const toggleBucketDone = (b: any) => {
    updateLoveBucket(String(b.id), { isDone: !b.isCompleted });
  };

  /** Item tercapai → kenangan (satu klik, idempoten). */
  const promoteBucket = (b: any) => {
    promoteLoveBucket(String(b.id));
    showToast('success', t('love_bucket_promoted', 'Ditambahkan ke kenangan'), b.title);
  };

  /* ── A12: handler tab overview ─────────────────────────────────────── */
  /** Aksi cepat panel overview → membuka dialog/tab yang tepat. */
  const quickOverviewAction = (action: 'memory' | 'event' | 'bucket' | 'reminders') => {
    if (action === 'memory') openMemoryDialog();
    else if (action === 'event') openEventDialog();
    else if (action === 'bucket') openBucketDialog();
    else if (onNavigate) onNavigate('reminders');
    else showToast('info', t('love_quick_reminders', 'Lihat pengingat'), t('love_open_reminders', 'Buka Reminder'));
  };

  /**
   * "Buat pengingat" untuk hari istimewa terdekat, idempoten di server
   * (`POST /api/love/events/<id>/create-reminder` → `repeat_type='yearly'`).
   * Pesan dibedakan: baru dibuat vs sudah ada & diperbarui.
   */
  const createSpecialReminder = (item: UpcomingItem) => {
    if (!item?.id) return;
    const days = Number(item.remindDaysBefore) > 0 ? Number(item.remindDaysBefore) : (item.recurring === 'yearly' ? 7 : 1);
    loveEventReminder(String(item.id), { daysBefore: days }).then((res: any) => {
      const r = res?.result || res || {};
      if (r?.ok === false) {
        const msg = r.msg === 'love_reminder_no_date' ? t('love_reminder_no_date', 'Hari istimewa ini belum punya tanggal.')
          : r.msg === 'love_reminder_bad_event' ? t('love_reminder_bad_event', 'Hari istimewa tidak dikenal.')
          : t('msg_error', 'Gagal');
        showToast('info', t('msg_error', 'Gagal'), msg);
        return;
      }
      const repeat = r.repeat_type === 'yearly' ? t('love_reminder_repeat_yearly', 'setiap tahun') : t('love_reminder_repeat_once', 'sekali');
      showToast('success',
        r.already ? t('love_reminder_exists', 'Pengingat sudah ada') : t('love_reminder_created', 'Pengingat dibuat'),
        trv('love_reminder_created_detail', { title: r.title || item.title, date: r.reminder_date || '', repeat },
          `${r.title || item.title} · ${r.reminder_date || ''} (${repeat})`));
      loadUpcoming();
    }).catch((e: any) => showToast('info', t('msg_error', 'Gagal'), String(e?.message || e)));
  };

  const TABS: Array<{ id: TabId; icon: React.ReactNode }> = [
    { id: 'overview', icon: <Heart className="w-4 h-4" /> },
    { id: 'connection', icon: <MessageSquareHeart className="w-4 h-4" /> },
    { id: 'cycle', icon: <Calendar className="w-4 h-4" /> },
    { id: 'memories', icon: <Heart className="w-4 h-4" /> },
    { id: 'gallery', icon: <Camera className="w-4 h-4" /> },
    { id: 'plans', icon: <Plus className="w-4 h-4" /> },
  ];

  return (
    <div id="love-space-view" className="space-y-6">
      {/* Header Hero Banner (parity header LovePage: title + edit profile + end couple) */}
      <div className="p-6 bg-gradient-to-r from-rose-950/60 via-slate-900 to-pink-950/40 border border-rose-500/20 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-6 shadow-xl">
        <div className="flex items-center gap-4 text-center md:text-left">
          <div className="ct-socket w-16 h-16 rounded-2xl bg-rose-500/10 flex items-center justify-center text-3xl shrink-0">
            {loveSpace.partnerAvatar || '🌸'}
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100">{t('page_love_title', 'Love Space')}</h1>
            <div className="text-sm font-bold text-rose-200 mt-1 flex items-center gap-2 justify-center md:justify-start flex-wrap">
              <Heart className="w-3.5 h-3.5 fill-rose-400 text-rose-400" />
              {trv('love_couple_format', { partner: loveSpace.partnerName || t('love_partner_not_set', 'Partner'), days: daysTogether }, '')}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">{coupleStatusText}</p>
            {/* P61: badge status couple (aktif / menunggu / tidak terhubung) + kartu akun pasangan */}
            <div className="flex items-center gap-2 mt-1.5 justify-center md:justify-start flex-wrap">
              {coupleActive ? (
                <span className="px-2 py-0.5 rounded-full text-[9px] font-black tracking-wider bg-emerald-500/15 text-emerald-300 border border-emerald-400/40">⚡ {t('love_couple_status_active', 'Couple aktif')}</span>
              ) : couplePending > 0 ? (
                <span className="px-2 py-0.5 rounded-full text-[9px] font-black tracking-wider bg-amber-500/15 text-amber-300 border border-amber-400/40">⏳ {t('love_couple_status_pending', 'Menunggu konfirmasi couple')}</span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-[9px] font-black tracking-wider bg-slate-700/40 text-slate-400 border border-slate-600/40">🔒 {t('love_couple_status_none', 'Belum terhubung couple')}</span>
              )}
              {coupleActive && couplePartner && (
                <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-950/70 border border-slate-700/60" title={t('love_couple_partner_card', 'Akun pasangan')}>
                  <span className="w-4 h-4 rounded-full flex items-center justify-center text-[10px] shrink-0"
                    style={{ backgroundColor: `${couplePartner.avatarColor || '#5a8a2e'}30`, border: `1px solid ${couplePartner.avatarColor || '#5a8a2e'}` }}>
                    {couplePartner.avatarEmoji || '♥'}</span>
                  <span className="text-slate-200">{couplePartner.displayName}</span>
                  <span className="text-amber-400">Lv.{couplePartner.level}</span>
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5">{healthSyncText}</p>
          </div>
        </div>
        <div className="flex flex-col items-center gap-2">
          <div className="flex items-center gap-4 bg-slate-950/70 p-4 rounded-xl border border-slate-800">
            <div className="text-center">
              <span className="text-2xl font-extrabold text-rose-400 font-mono">{daysTogether}</span>
              <span className="block text-[10px] uppercase tracking-wider text-slate-500 font-bold">{t('love_days_together', 'Hari Bersama')}</span>
            </div>
            <div className="h-8 w-px bg-slate-800" />
            <div className="text-center">
              <span className="text-2xl font-extrabold text-emerald-400 font-mono">{loveSpace.connectionScore}%</span>
              <span className="block text-[10px] uppercase tracking-wider text-slate-500 font-bold">{t('love_connection', 'Harmoni')}</span>
            </div>
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={openProfile} className={btnRose}>
              {t('love_edit_profile', 'Edit Profil')}
            </button>
            {coupleActive && (
              <>
                <button type="button" onClick={openTracking} className={btnGhost}>
                  {t('love_open_tracking', 'Tracking Couple')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (!window.confirm(t('couple_end_confirm', 'Akhiri hubungan couple?'))) return;
                    studio.endCouple().then((r) => showToast(r.ok ? 'success' : 'info', r.result?.msg || r.result?.code || 'couple', ''));
                  }}
                  className={btnDanger}
                >
                  {t('couple_end', 'Akhiri Couple')}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Tab bar (parity QTabWidget LovePage: 6 tab) */}
      <div className="flex flex-wrap gap-1.5 p-1.5 bg-slate-900/70 border border-slate-800 rounded-2xl">
        {TABS.map((tb) => (
          <button
            key={tb.id}
            onClick={() => setTab(tb.id)}
            className={`ct-tab flex items-center gap-1.5 ${
              tab === tb.id ? 'ct-tab-on ct-tab-rose' : ''
            }`}
          >
            {tb.icon}
            {t(`love_tab_${tb.id}`, tb.id)}
          </button>
        ))}
      </div>

      {/* ═══ TAB: OVERVIEW (A12: dashboard pasangan) ═══ */}
      {tab === 'overview' && (
        <LoveOverviewPanel
          t={t}
          trv={trv}
          loveSpace={loveSpace}
          today={today}
          upcoming={upcoming}
          loadingUpcoming={upcomingLoading}
          onRefreshUpcoming={loadUpcoming}
          onCheckin={(p) => loveCheckin(p)}
          onQuickAction={quickOverviewAction}
          onEditProfile={() => setShowProfile(true)}
          onOpenTracking={openTracking}
          onCreateReminder={createSpecialReminder}
          showToast={showToast}
        />
      )}

      {/* ═══ TAB: CONNECTION (A11: statistik, tren mood, riwayat, favorit) ═══ */}
      {tab === 'connection' && (
        <LoveConnectionPanel
          t={t}
          trv={trv}
          loveSpace={loveSpace}
          today={today}
          onSaveResponse={(p) => {
            // Parity _save_prompt_response: simpan jawaban + jawaban pasangan sekaligus.
            studio.lovePrompt(p as any).then((res: any) => {
              if (res?.result?.ok === false) showToast('info', t('msg_error', 'Error'), res.result?.msg || '');
              refreshLoveSpace();
            }).catch((e) => showToast('info', String(e?.message || e), ''));
          }}
          onFavorite={lovePromptFavorite}
          onDeleteResponse={deleteLovePrompt}
          onSaveWeekly={(p) => loveWeekly({ weekStart: p.weekStart, appreciation: p.appreciation, wins: p.wins, support: p.support, intention: p.intention })}
          onDeleteWeekly={deleteLoveWeekly}
          showToast={showToast}
        />
      )}

      {/* ═══ TAB: CYCLE (A11: prediksi + ovulasi/subur + tabel riwayat yang bisa diedit) ═══ */}
      {tab === 'cycle' && (
        <LoveCyclePanel
          t={t}
          trv={trv}
          loveSpace={loveSpace}
          today={today}
          onSaveSettings={(s) => loveCycle({ settings: s })}
          onLogToday={() => addLoveCycle({ startDate: today, notes: '' })}
          onAddCycle={(p) => addLoveCycle(p)}
          onUpdateCycle={(id, p) => updateLoveCycle(id, p)}
          onDeleteCycle={deleteLoveCycle}
          onReminder={(daysBefore) => {
            loveCycleReminder(daysBefore, t('love_cycle_reminder_title', 'Pengingat siklus'));
            showToast('success', t('berhasil_title', 'Berhasil'), trv('love_cycle_reminder_toast', { n: daysBefore }, `Pengingat H-${daysBefore} dibuat.`));
          }}
          showToast={showToast}
        />
      )}

      {/* ═══ TAB: MEMORIES (A10: timeline + toolbar + edit/favorit/foto) ═══ */}
      {tab === 'memories' && (
        <div className="space-y-4" data-testid="love-memories-tab">
          {/* ── Kepala: judul, hitungan, tombol tambah ── */}
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-bold text-sm text-slate-200 flex-1">{t('love_memories_title', 'Kenangan Berdua')}</h3>
            <span className="text-[11px] text-slate-500" data-testid="love-memory-count">
              {trv('love_memory_count', { n: memView.matched, total: memView.total },
                `${memView.matched} dari ${memView.total} kenangan`)}
            </span>
            <button type="button" onClick={() => openMemoryDialog()} className={btnRose} data-testid="love-memory-add">
              <Plus className="w-3.5 h-3.5 inline mr-1" />{t('love_add_memory', 'Tambah Kenangan')}
            </button>
          </div>

          {/* ── Statistik ringkas ── */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {([
              ['love_memory_stat_total', 'Total kenangan', memStats.total, '💖'],
              ['love_memory_stat_fav', 'Favorit', memStats.favorites, '⭐'],
              ['love_memory_stat_tagged', 'Bertag', memStats.tagged, '🏷️'],
              ['love_memory_stat_photo', 'Berfoto', memStats.withPhoto, '🖼️'],
            ] as Array<[string, string, number, string]>).map(([key, fb, value, icon]) => (
              <div key={key} className="p-3 bg-slate-900/70 border border-slate-800 rounded-2xl flex items-center gap-2">
                <span className="text-base">{icon}</span>
                <div>
                  <div className="text-sm font-extrabold text-rose-300 font-mono">{value}</div>
                  <div className="text-[10px] text-slate-500">{t(key, fb)}</div>
                </div>
              </div>
            ))}
          </div>

          {/* ── Toolbar: cari, tahun, tag, urutan, hanya favorit ── */}
          <div className="flex flex-wrap items-center gap-2 p-3 bg-slate-900/60 border border-slate-800 rounded-2xl">
            <div className="relative flex-1 min-w-[170px]">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2 top-1/2 -translate-y-1/2" />
              <input
                value={memSearch}
                onChange={(e) => setMemSearch(e.target.value)}
                className={`${inputCls} pl-7`}
                placeholder={t('love_memory_search_ph', 'Cari kenangan, catatan, atau tag…')}
              />
            </div>
            <select value={memYear} onChange={(e) => setMemYear(e.target.value)} className={`${inputCls} w-auto`}
              title={t('love_memory_filter_year', 'Tahun')} data-testid="love-memory-year">
              <option value="">{t('love_memory_year_all', 'Semua tahun')}</option>
              {memFacets.years.map((y) => <option key={y} value={y}>{y}</option>)}
            </select>
            <select value={memTag} onChange={(e) => setMemTag(e.target.value)} className={`${inputCls} w-auto`}
              title={t('love_memory_tags', 'Tag')} data-testid="love-memory-tag">
              <option value="">{t('love_memory_tag_all', 'Semua tag')}</option>
              {memFacets.tags.map((tg) => (
                <option key={tg.tag} value={tg.tag}>#{tg.tag} ({tg.count})</option>
              ))}
            </select>
            <select value={memSort} onChange={(e) => setMemSort(e.target.value as MemorySort)} className={`${inputCls} w-auto`}
              title={t('love_memory_sort', 'Urutan')} data-testid="love-memory-sort">
              <option value="newest">{t('love_memory_sort_newest', 'Terbaru')}</option>
              <option value="oldest">{t('love_memory_sort_oldest', 'Terlama')}</option>
            </select>
            <button
              type="button"
              onClick={() => setMemOnlyFav((v) => !v)}
              data-testid="love-memory-only-fav"
              className={`ct-btn ct-btn-sm ${memOnlyFav ? 'ct-btn-rose' : 'ct-btn-secondary'}`}
            >
              <Star className={`w-3.5 h-3.5 inline mr-1 ${memOnlyFav ? 'text-amber-200' : ''}`} />
              {t('love_memory_only_fav', 'Hanya favorit')}
            </button>
          </div>

          {/* ── Timeline kenangan ── */}
          <div className="space-y-2">
            {memView.items.map((m) => (
              <div key={m.id} data-testid="love-memory-card" className="flex gap-3">
                <div className="flex flex-col items-center pt-1">
                  <span className="w-10 h-10 rounded-2xl bg-rose-500/10 border border-rose-500/25 flex items-center justify-center text-lg">
                    {m.emoji || '💖'}
                  </span>
                  <span className="flex-1 w-px bg-slate-800 min-h-[12px]" />
                </div>
                <div className="flex-1 min-w-0 p-4 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="font-bold text-sm text-slate-200 flex items-center gap-1.5">
                        {m.isFavorite && <Star className="w-3.5 h-3.5 text-amber-300 fill-amber-300" data-testid="love-memory-star" />}
                        <span className="truncate">{m.title}</span>
                      </div>
                      <div className="text-[11px] text-slate-500 flex flex-wrap items-center gap-2 mt-0.5">
                        <span className="flex items-center gap-1"><CalendarDays className="w-3 h-3" />{m.date || '—'}</span>
                        {m.photoId && (
                          <span className="flex items-center gap-1 text-rose-300/80">
                            <ImageIcon className="w-3 h-3" />{t('love_memory_has_photo', 'Ada foto')}
                          </span>
                        )}
                        {m.updatedAt && m.updatedAt.slice(0, 10) !== m.date && (
                          <span className="text-slate-600">
                            {trv('love_memory_edited_at', { date: m.updatedAt.slice(0, 10) }, `diubah ${m.updatedAt.slice(0, 10)}`)}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        onClick={() => loveMemoryFavorite(String(m.id))}
                        data-testid="love-memory-fav-btn"
                        title={t('love_memory_favorite', 'Tandai favorit')}
                        className={`p-1 ${m.isFavorite ? 'text-amber-300' : 'text-slate-500 hover:text-amber-300'}`}
                      >
                        <Star className={`w-3.5 h-3.5 ${m.isFavorite ? 'fill-amber-300' : ''}`} />
                      </button>
                      <button
                        type="button"
                        onClick={() => openMemoryDialog(m)}
                        data-testid="love-memory-edit"
                        title={t('love_memory_edit_title', 'Edit kenangan')}
                        className="p-1 text-slate-500 hover:text-rose-300"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          if (!window.confirm(t('love_memory_delete_confirm', 'Hapus kenangan ini?'))) return;
                          deleteLoveMemory(String(m.id));
                        }}
                        className="p-1 text-slate-500 hover:text-rose-400"
                        title={t('love_delete_selected', 'Hapus')}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {m.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1" data-testid="love-memory-tags">
                      {m.tags.map((tg) => (
                        <button
                          key={tg}
                          type="button"
                          onClick={() => setMemTag(tg)}
                          className="px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-200 text-[10px] border border-rose-500/25 hover:bg-rose-500/20"
                        >#{tg}</button>
                      ))}
                    </div>
                  )}

                  {m.description && (
                    <p className="text-xs text-slate-400 whitespace-pre-line line-clamp-4">{m.description}</p>
                  )}

                  {m.photoId && (
                    <div className="w-full max-w-[280px]">
                      <PhotoThumb photo={memPhotoOf(m.photoId)} />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {memView.total === 0 && (
            <p className="text-xs text-slate-500" data-testid="love-memory-empty">
              {t('love_memory_empty', 'Belum ada kenangan. Simpan momen pertama kalian di sini.')}
            </p>
          )}
          {memView.total > 0 && memView.matched === 0 && (
            <p className="text-xs text-slate-500" data-testid="love-memory-no-match">
              {t('love_memory_no_match', 'Tidak ada kenangan yang cocok dengan filter ini.')}
            </p>
          )}
        </div>
      )}

      {/* ═══ TAB: GALLERY (A11: sampul album, aksi massal, lightbox keyboard) ═══ */}
      {tab === 'gallery' && (
        <LoveGalleryPanel
          t={t}
          trv={trv}
          photos={loveSpace.photos || []}
          albums={loveSpace.albums || []}
          userId={String((user as any)?.id || '')}
          coupleActive={!!loveSpace.coupleActive}
          today={today}
          onPickFiles={onPickFiles}
          onDeletePhoto={deleteLovePhoto}
          onPhotoMeta={updateLovePhotoMeta}
          onBulk={galleryBulk}
          onCreateAlbum={createLoveAlbum}
          onRenameAlbum={renameLoveAlbum}
          onDeleteAlbum={deleteLoveAlbum}
          onAlbumPhoto={(albumId, photoId, mode) => {
            if (mode === 'remove') loveAlbumRemovePhoto(albumId, photoId);
            else if (mode === 'move') loveAlbumMovePhoto(albumId, photoId, null);
            else loveAlbumAddPhoto(albumId, photoId);
          }}
          onAlbumCover={(albumId, photoId) => {
            loveAlbumCover(albumId, photoId);
            showToast('success', t('berhasil_title', 'Berhasil'), t('love_gallery_cover_saved', 'Sampul album diperbarui.'));
          }}
          showToast={showToast}
        />
      )}

      {/* ═══ TAB: PLANS (events + bucket list) ═══ */}
      {tab === 'plans' && (
        <div className="space-y-4">
          {/* Hari istimewa terdekat — termasuk ulang tahun/anniversary dari profil */}
          {specialChips.length > 0 && (
            <div className="p-4 bg-gradient-to-r from-rose-900/30 via-slate-900/60 to-slate-900/70 border border-rose-500/25 rounded-2xl">
              <div className="flex items-center gap-2 mb-2.5">
                <Star className="w-4 h-4 text-amber-300" />
                <h3 className="text-[11px] font-black uppercase tracking-wider text-rose-200">
                  {t('love_event_special_upcoming', 'Hari istimewa terdekat')}
                </h3>
                <span className="text-[10px] text-slate-500">
                  {trv('love_event_special_count', { n: (loveSpace as any).specialDays?.length || specialChips.length },
                    `${(loveSpace as any).specialDays?.length || specialChips.length} hari istimewa dalam 90 hari`)}
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {specialChips.map((it) => (
                  <div
                    key={String(it.id)}
                    data-testid="love-special-chip"
                    className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-950/60 border border-slate-800"
                  >
                    <span className="text-lg leading-none">{it.icon || '⭐'}</span>
                    <span className="min-w-0">
                      <span className="block text-[11px] font-bold text-slate-200 truncate max-w-[11rem]">{it.title}</span>
                      <span className="block text-[10px] text-slate-400 tabular-nums">
                        {it.nextDate} · {evCountdown(it.daysUntil)}
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* ── Acara berdua ── */}
            <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
              <div className="flex items-center justify-between gap-2">
                <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                  <CalendarDays className="w-4 h-4 text-rose-400" />
                  {t('love_events', 'Acara Berdua')}
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-800 text-slate-400 ct-nlm-num">{evData.total}</span>
                </h3>
                <button type="button" className={btnRose} onClick={() => openEventDialog()}>
                  <Plus className="w-3.5 h-3.5 mr-1" />
                  {t('love_event_add_title', 'Tambah acara')}
                </button>
              </div>

              {/* Toolbar: pencarian + filter kategori + hanya hari istimewa */}
              {(loveSpace.events || []).length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5">
                  <div className="relative flex-1 min-w-[9rem]">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input
                      value={evSearch}
                      onChange={(e) => setEvSearch(e.target.value)}
                      className={`${inputCls} pl-7`}
                      placeholder={t('love_event_search_ph', 'Cari acara, lokasi, atau catatan…')}
                    />
                  </div>
                  <select value={evCat} onChange={(e) => setEvCat(e.target.value)} className={`${inputCls} w-auto`}>
                    <option value="all">{t('love_event_filter_all', 'Semua kategori')}</option>
                    {EVENT_CATEGORIES.map((c) => (
                      <option key={c.id} value={c.id}>{c.icon} {t(`love_category_${c.id}`, c.id)}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => setEvOnlySpecial((v) => !v)}
                    className={`ct-btn ct-btn-sm ${evOnlySpecial ? 'ct-btn-rose' : 'ct-btn-secondary'}`}
                    title={t('love_event_only_special', 'Hanya hari istimewa')}
                  >
                    <Star className="w-3.5 h-3.5 mr-1" />
                    {evData.specialCount}
                  </button>
                </div>
              )}

              {/* Akan datang */}
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  <Sparkles className="w-3 h-3 text-rose-300" />
                  {t('love_event_upcoming', 'Akan datang')}
                  <span className="ct-nlm-num">{evData.upcoming.length}</span>
                </div>
                {evData.upcoming.map((ev: any) => (
                  <div
                    key={ev.id}
                    data-testid="love-event-card"
                    className="rounded-xl border border-slate-800 bg-slate-950/50 p-2.5 space-y-1"
                  >
                    <div className="flex items-start gap-2">
                      <span className="w-8 h-8 rounded-xl bg-rose-500/15 border border-rose-500/25 flex items-center justify-center text-base leading-none shrink-0">
                        {ev.icon || evCategoryMeta(ev.category).icon}
                      </span>
                      <button type="button" onClick={() => openEventDialog(ev)} className="min-w-0 flex-1 text-left">
                        <span className="flex items-center gap-1.5">
                          <span className="text-xs font-bold text-slate-100 truncate">{ev.title}</span>
                          {ev.isSpecial && <Star className="w-3 h-3 text-amber-300 shrink-0" />}
                          {ev.recurring === 'yearly' && <Repeat className="w-3 h-3 text-rose-300 shrink-0" />}
                        </span>
                        <span className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-slate-400">
                          <span className="tabular-nums">
                            {ev.date}
                            {ev.recurring === 'yearly' && ev.nextDate ? ` → ${ev.nextDate}` : ''}
                          </span>
                          <span className="px-1.5 rounded bg-slate-800/80 text-slate-300">
                            {t(`love_category_${ev.category || 'date'}`, ev.category || 'date')}
                          </span>
                          {ev.location && (
                            <span className="flex items-center gap-0.5 truncate max-w-[9rem]">
                              <MapPin className="w-3 h-3" />{ev.location}
                            </span>
                          )}
                          {ev.remindDaysBefore > 0 && (
                            <span className="flex items-center gap-0.5 text-amber-300/90">
                              <Bell className="w-3 h-3" />
                              {trv('love_event_remind_short', { n: ev.remindDaysBefore }, `H-${ev.remindDaysBefore}`)}
                            </span>
                          )}
                        </span>
                      </button>
                      <span className={`shrink-0 text-[10px] font-black px-2 py-1 rounded-lg tabular-nums ${ev.daysUntil <= 1 ? 'bg-rose-500/25 text-rose-200' : 'bg-slate-800 text-slate-300'}`}>
                        {evBadge(ev.daysUntil)}
                      </span>
                      <span className="shrink-0 flex items-center gap-0.5">
                        <button
                          type="button"
                          onClick={() => openEventDialog(ev)}
                          className="p-1 text-slate-500 hover:text-rose-300"
                          title={t('love_event_edit_title', 'Edit acara')}
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            if (window.confirm(t('love_delete_selected', 'Hapus'))) deleteLoveEvent(ev.id);
                          }}
                          className="p-1 text-slate-500 hover:text-rose-400"
                          title={t('love_delete_selected', 'Hapus')}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </span>
                    </div>
                    {ev.notes && (
                      <p className="text-[10px] text-slate-400 leading-relaxed pl-10 whitespace-pre-wrap">{ev.notes}</p>
                    )}
                  </div>
                ))}
                {!evData.upcoming.length && (
                  <p className="text-xs text-slate-500 py-2">
                    {evData.total === 0
                      ? t('love_event_empty', 'Belum ada acara. Tambahkan kencan, hadiah, atau hari istimewa.')
                      : t('love_event_no_match', 'Tidak ada acara yang cocok dengan filter ini.')}
                  </p>
                )}
              </div>

              {/* Sudah lewat (kolaps) */}
              {evData.past.length > 0 && (
                <div className="space-y-1.5 pt-1 border-t border-slate-800/60">
                  <button
                    type="button"
                    onClick={() => setEvShowPast((v) => !v)}
                    className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 hover:text-slate-200 w-full"
                  >
                    {evShowPast ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                    {t('love_event_past', 'Sudah lewat')}
                    <span className="ct-nlm-num">{evData.past.length}</span>
                  </button>
                  {evShowPast && evData.past.map((ev: any) => (
                    <div
                      key={ev.id}
                      data-testid="love-event-card-past"
                      className="rounded-xl border border-slate-800/60 bg-slate-950/30 p-2 text-[11px] text-slate-400 flex items-start gap-2"
                    >
                      <span className="text-sm leading-none shrink-0">{ev.icon || evCategoryMeta(ev.category).icon}</span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-1.5">
                          <span className="font-bold text-slate-300 truncate">{ev.title}</span>
                          {ev.isSpecial && <Star className="w-3 h-3 text-amber-300/80" />}
                        </span>
                        <span className="text-[10px] text-slate-500 tabular-nums">
                          {ev.date} · {evCountdown(ev.daysUntil)}
                          {ev.location ? ` · ${ev.location}` : ''}
                        </span>
                        {ev.notes && <span className="block text-[10px] text-slate-500 truncate">{ev.notes}</span>}
                      </span>
                      <span className="shrink-0 flex items-center gap-0.5">
                        <button type="button" onClick={() => openEventDialog(ev)} className="p-1 hover:text-rose-300" title={t('love_event_edit_title', 'Edit acara')}>
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => { if (window.confirm(t('love_delete_selected', 'Hapus'))) deleteLoveEvent(ev.id); }}
                          className="p-1 hover:text-rose-400"
                          title={t('love_delete_selected', 'Hapus')}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* ── Bucket List (A10: progres, kategori, target, catatan, prioritas, promosi) ── */}
            <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3" data-testid="love-bucket-panel">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-bold text-sm text-slate-200 flex items-center gap-1.5">
                  <ListChecks className="w-4 h-4 text-rose-400" />{t('love_bucket_list', 'Bucket List')}
                </h3>
                <span className="text-[11px] text-slate-500 flex-1" data-testid="love-bucket-progress-text">
                  {bucketProgressText(bucketStat, (key, vars, fb) => trv(key, vars || {}, fb || key))}
                </span>
                <button type="button" onClick={() => openBucketDialog()} className={btnGhost} data-testid="love-bucket-add-detail">
                  <Plus className="w-3.5 h-3.5 inline mr-1" />{t('love_bucket_add', 'Tambah lengkap')}
                </button>
              </div>

              {/* Progres */}
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden" data-testid="love-bucket-progress">
                <div className="h-full bg-gradient-to-r from-rose-500 to-amber-400 transition-all" style={{ width: `${bucketStat.percent}%` }} />
              </div>
              <div className="flex flex-wrap items-center gap-2 text-[11px]">
                <span className="px-2 py-0.5 rounded-full bg-slate-800/70 text-slate-300">
                  {trv('love_bucket_stat_total', { n: bucketStat.total }, `${bucketStat.total} total`)}
                </span>
                <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-200 border border-emerald-500/20">
                  {trv('love_bucket_stat_done', { n: bucketStat.done }, `${bucketStat.done} selesai`)}
                </span>
                <span className="px-2 py-0.5 rounded-full bg-slate-800/70 text-slate-300">
                  {trv('love_bucket_stat_open', { n: bucketStat.open }, `${bucketStat.open} belum`)}
                </span>
                {bucketStat.overdue > 0 && (
                  <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-200 border border-amber-500/25 flex items-center gap-1" data-testid="love-bucket-overdue-stat">
                    <AlertTriangle className="w-3 h-3" />
                    {trv('love_bucket_stat_overdue', { n: bucketStat.overdue }, `${bucketStat.overdue} lewat target`)}
                  </span>
                )}
                <span className="text-slate-600 font-mono">{bucketStat.percent}%</span>
              </div>

              {/* Tambah cepat + pencarian */}
              <div className="flex flex-wrap items-center gap-2">
                <input
                  value={bucketQuick}
                  onChange={(e) => setBucketQuick(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') quickAddBucket(); }}
                  className={`${inputCls} flex-1 min-w-[150px]`}
                  placeholder={t('love_bucket_quick_ph', 'Tambah cepat: tulis impian, tekan Enter')}
                />
                <button type="button" className={btnRose} onClick={quickAddBucket} data-testid="love-bucket-quick-add">
                  {t('love_add', 'Tambah')}
                </button>
                <div className="relative w-full md:w-48">
                  <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2 top-1/2 -translate-y-1/2" />
                  <input
                    value={bucketSearch}
                    onChange={(e) => setBucketSearch(e.target.value)}
                    className={`${inputCls} pl-7`}
                    placeholder={t('love_bucket_search_ph', 'Cari item…')}
                  />
                </div>
              </div>

              {/* Filter */}
              <div className="flex flex-wrap gap-1.5">
                {(['all', 'open', 'done', 'late'] as BucketFilter[]).map((f) => (
                  <button
                    key={f}
                    type="button"
                    onClick={() => setBucketFilter(f)}
                    data-testid={`love-bucket-filter-${f}`}
                    className={`ct-btn ct-btn-sm ${bucketFilter === f ? 'ct-btn-rose' : 'ct-btn-secondary'}`}
                  >
                    {t(`love_bucket_filter_${f}`, BUCKET_FILTER_FALLBACK[f])}
                    <span className="ml-1 font-mono opacity-70">{bucketFilterCount(f)}</span>
                  </button>
                ))}
              </div>

              {/* Daftar item */}
              <div className="max-h-[430px] overflow-y-auto space-y-2 pr-0.5">
                {bucketView.map((b) => (
                  <div
                    key={b.id}
                    data-testid="love-bucket-card"
                    className={`p-3 rounded-xl border space-y-2 ${
                      b.isCompleted ? 'border-emerald-500/25 bg-emerald-500/5'
                        : b.isOverdue ? 'border-amber-500/30 bg-amber-500/5'
                          : 'border-slate-800 bg-slate-950/40'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <button
                        type="button"
                        onClick={() => toggleBucketDone(b)}
                        data-testid="love-bucket-check"
                        title={b.isCompleted
                          ? t('love_bucket_mark_open', 'Tandai belum tercapai')
                          : t('love_bucket_mark_done', 'Tandai sudah tercapai')}
                        className={`mt-0.5 ${b.isCompleted ? 'text-emerald-300' : 'text-slate-500 hover:text-rose-300'}`}
                      >
                        {b.isCompleted ? <CheckCircle2 className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                      </button>
                      <div className="flex-1 min-w-0">
                        <div className={`text-xs font-bold ${b.isCompleted ? 'line-through text-slate-500' : 'text-slate-200'}`}>
                          <span className="mr-1">{bucketCategoryIcon(b.category)}</span>{b.title}
                          {b.priority > 0 && (
                            <span className="ml-1 text-amber-300" data-testid="love-bucket-priority-stars"
                              title={trv('love_bucket_priority_n', { n: b.priority }, `Prioritas ${b.priority}`)}>
                              {'⭐'.repeat(b.priority)}
                            </span>
                          )}
                        </div>
                        <div className="flex flex-wrap items-center gap-2 mt-0.5 text-[10px]">
                          <span className="text-slate-500">{t(`love_bucket_category_${b.category}`, b.category)}</span>
                          {b.targetDate && (
                            <span
                              data-testid="love-bucket-target"
                              className={`flex items-center gap-1 ${b.isOverdue ? 'text-amber-300' : 'text-slate-400'}`}
                            >
                              <Clock className="w-3 h-3" />{b.targetDate}
                              {bucketTargetLabel(b) ? ` · ${bucketTargetLabel(b)}` : ''}
                            </span>
                          )}
                          {b.completedDate && (
                            <span className="text-emerald-300/80">
                              ✅ {String(b.completedDate).split(' ')[0]}
                            </span>
                          )}
                          {b.promotedMemoryId && (
                            <span className="text-rose-300/80 flex items-center gap-1" data-testid="love-bucket-promoted">
                              <StickyNote className="w-3 h-3" />{t('love_bucket_is_memory', 'Sudah jadi kenangan')}
                            </span>
                          )}
                        </div>
                        {b.notes && <p className="text-[11px] text-slate-400 mt-1 whitespace-pre-line">{b.notes}</p>}
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        {b.isCompleted && !b.promotedMemoryId && (
                          <button
                            type="button"
                            onClick={() => promoteBucket(b)}
                            data-testid="love-bucket-promote"
                            title={t('love_bucket_promote', 'Simpan jadi kenangan')}
                            className="ct-btn ct-btn-sm ct-btn-rose"
                          >
                            <StickyNote className="w-3 h-3 inline mr-1" />
                            {t('love_bucket_promote_short', 'Jadi kenangan')}
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => openBucketDialog(b)}
                          data-testid="love-bucket-edit"
                          title={t('love_bucket_edit_title', 'Edit item bucket list')}
                          className="p-1 text-slate-500 hover:text-rose-300"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            if (!window.confirm(t('love_bucket_delete_confirm', 'Hapus item ini?'))) return;
                            deleteLoveBucket(String(b.id));
                          }}
                          className="p-1 text-slate-500 hover:text-rose-400"
                          title={t('love_delete_selected', 'Hapus')}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
                {!(loveSpace.bucketList || []).length && (
                  <p className="text-xs text-slate-500" data-testid="love-bucket-empty">
                    {t('love_bucket_empty', 'Belum ada rencana. Tulis impian pertama kalian di atas.')}
                  </p>
                )}
                {(loveSpace.bucketList || []).length > 0 && bucketView.length === 0 && (
                  <p className="text-xs text-slate-500" data-testid="love-bucket-no-match">
                    {t('love_bucket_no_match', 'Tidak ada item yang cocok dengan filter ini.')}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Dialog Tambah/Edit Acara (A09) ── */}
      <LoveEventDialog
        key={evDialog ? `${evDialog.mode}-${evDialog.initial?.id || 'new'}-${evDialog.nonce}` : 'closed'}
        open={!!evDialog}
        mode={evDialog?.mode || 'add'}
        initial={evDialog?.initial || null}
        saving={evSaving}
        today={today}
        onClose={() => setEvDialog(null)}
        onSave={saveEvent}
        tr={(key, vars, fb) => {
          // i18n `t()` butuh fallback berupa string; dialog boleh memanggil tanpa fallback.
          const base = t(key, fb || key);
          if (!vars) return base;
          return Object.entries(vars).reduce((acc, [k, v]) => acc.split(`{${k}}`).join(String(v)), base);
        }}
      />

      {/* ── Dialog Tambah/Edit Kenangan (A10: emoji, tag, favorit, tautan foto) ── */}
      <LoveMemoryDialog
        key={memDialog ? `${memDialog.mode}-${memDialog.initial?.id || 'new'}-${memDialog.nonce}` : 'closed'}
        open={!!memDialog}
        mode={memDialog?.mode || 'add'}
        initial={memDialog?.initial || null}
        photos={(loveSpace.photos || []).map((ph: any) => ({
          id: String(ph.id), caption: ph.caption || '', photoDate: ph.photoDate || '',
        }))}
        saving={memSaving}
        today={today}
        onClose={() => setMemDialog(null)}
        onSave={saveMemory}
        tr={(key, vars, fb) => {
          const base = t(key, fb || key);
          if (!vars) return base;
          return Object.entries(vars).reduce((acc, [k, v]) => acc.split(`{${k}}`).join(String(v)), base);
        }}
      />

      {/* ── Dialog Tambah/Edit Item Bucket List (A10: kategori, target, prioritas) ── */}
      <LoveBucketDialog
        key={bucketDialog ? `${bucketDialog.mode}-${bucketDialog.initial?.id || 'new'}-${bucketDialog.nonce}` : 'closed'}
        open={!!bucketDialog}
        mode={bucketDialog?.mode || 'add'}
        initial={bucketDialog?.initial || null}
        saving={bucketSaving}
        today={today}
        onClose={() => setBucketDialog(null)}
        onSave={saveBucket}
        tr={(key, vars, fb) => {
          const base = t(key, fb || key);
          if (!vars) return base;
          return Object.entries(vars).reduce((acc, [k, v]) => acc.split(`{${k}}`).join(String(v)), base);
        }}
      />

      {/* A11: lightbox + dialog "pilih album" kini dirender `LoveGalleryPanel`
          (navigasi ← → / Esc, tombol Simpan keterangan, simpan ke album). */}

      {/* ── Upload metadata dialog per file (parity _GalleryPhotoDialog) ── */}
      {uploadIdx >= 0 && uploadQueue[uploadIdx] && (
        <Modal title={`${t('love_gallery_upload', 'Unggah Foto')} (${uploadIdx + 1}/${uploadQueue.length})`} onClose={() => { setUploadIdx(-1); setUploadQueue([]); }}>
          <p className="text-xs text-slate-400 truncate">{uploadQueue[uploadIdx].name} · {(uploadQueue[uploadIdx].size / 1024).toFixed(0)} KB</p>
          {uploadQueue[uploadIdx].size > UPLOAD_MAX && (
            <p className="text-xs text-rose-400">{t('web_upload_too_large', 'File terlalu besar (maks 8MB).')}</p>
          )}
          <input value={upCaption} onChange={(e) => setUpCaption(e.target.value)} className={inputCls} placeholder={t('love_gallery_meta', 'Keterangan foto (opsional)')} />
          <label className="block text-[11px] text-slate-400">{t('love_date_label', 'Tanggal')}</label>
          <input type="date" value={upDate} onChange={(e) => setUpDate(e.target.value)} className={inputCls} />
          <label className="block text-[11px] text-slate-400">{t('love_album_scope', 'Visibilitas')}</label>
          <select value={upVis} onChange={(e) => setUpVis(e.target.value as 'private' | 'shared')} className={inputCls}>
            <option value="private">🔒 {t('love_gallery_private_hint', 'Private — hanya kamu')}</option>
            <option value="shared" disabled={!coupleActive}>
              💞 {coupleActive ? t('love_gallery_shared_hint', 'Shared — terlihat pasangan') : t('love_album_shared_need_couple', 'Shared (butuh couple aktif)')}
            </option>
          </select>
          <div className="flex justify-end gap-2">
            <button type="button" className={btnGhost} onClick={() => processUpload(false)}>{t('msg_cancel', 'Lewati')}</button>
            <button type="button" className={btnRose} onClick={() => processUpload(true)}>{t('love_gallery_upload', 'Unggah')}</button>
          </div>
        </Modal>
      )}

      {/* ── Edit profile modal (parity _edit_profile) ── */}
      {showProfile && (
        <Modal title={t('love_profile_title', 'Profil Hubungan')} onClose={() => setShowProfile(false)} wide>
          <p className="text-[11px] text-slate-400">{t('love_profile_both_hint', '')}</p>
          {/* Sisi Kamu (parity _LoveProfileDialog me_card) */}
          <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3 space-y-2">
            <div className="text-xs font-bold text-slate-200">{t('love_profile_you_title', 'Profil Kamu')}</div>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <label className="block text-slate-400 col-span-2">
                {t('love_my_name', 'Namamu')}
                <input value={profMy} onChange={(e) => setProfMy(e.target.value)} placeholder={t('love_my_name_ph', 'Nama lengkapmu')} className={inputCls} />
              </label>
              <label className="block text-slate-400">
                {t('love_my_gender', 'Gender kamu')}
                <select value={profMyGender} onChange={(e) => setProfMyGender(e.target.value)} className={inputCls}>
                  <option value="male">{t('food_bmi_gender_m', 'Laki-laki')}</option>
                  <option value="female">{t('food_bmi_gender_f', 'Perempuan')}</option>
                </select>
              </label>
              <label className="block text-slate-400">
                {t('love_my_age', 'Umurmu')}
                <NumberInput value={profMyAge} onValueChange={setProfMyAge} min={15} max={100} integer emptyValue={25} inputClassName={inputCls} />
              </label>
              <label className="block text-slate-400 col-span-2">
                {t('love_my_birthdate', 'Tanggal lahirmu')}
                <input type="date" value={profMyBirth} onChange={(e) => setProfMyBirth(e.target.value)} className={inputCls} />
              </label>
            </div>
          </div>
          {/* Sisi Pasangan (parity _LoveProfileDialog partner_card) */}
          <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3 space-y-2">
            <div className="text-xs font-bold text-slate-200">{t('love_profile_partner_title', 'Profil Pasangan')}</div>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <label className="block text-slate-400 col-span-2">
                {t('love_partner_name', 'Nama pasangan')} *
                <input value={profPartner} onChange={(e) => setProfPartner(e.target.value)} placeholder={t('love_partner_name_ph', 'Nama panggilan pasangan')} className={inputCls} />
              </label>
              <label className="block text-slate-400">
                {t('love_partner_gender', 'Gender pasangan')}
                <select value={profPartnerGender} onChange={(e) => setProfPartnerGender(e.target.value)} className={inputCls}>
                  <option value="male">{t('food_bmi_gender_m', 'Laki-laki')}</option>
                  <option value="female">{t('food_bmi_gender_f', 'Perempuan')}</option>
                </select>
              </label>
              <label className="block text-slate-400">
                {t('love_partner_age', 'Umur pasangan')}
                <NumberInput value={profPartnerAge} onValueChange={setProfPartnerAge} min={15} max={100} integer emptyValue={25} inputClassName={inputCls} />
              </label>
              <label className="block text-slate-400 col-span-2">
                {t('love_partner_birthdate', 'Tanggal lahir pasangan')}
                <input type="date" value={profPartnerBirth} onChange={(e) => setProfPartnerBirth(e.target.value)} className={inputCls} />
              </label>
            </div>
          </div>
          {/* Relasi (parity _LoveProfileDialog rel_card) */}
          <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3 space-y-2">
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <label className="block text-slate-400">
                {t('love_relationship_type', 'Status hubungan')}
                <select value={profRelType} onChange={(e) => setProfRelType(e.target.value)} className={inputCls}>
                  <option value="dating">{t('love_type_dating', 'Pacaran')}</option>
                  <option value="engaged">{t('love_type_engaged', 'Tunangan')}</option>
                  <option value="married">{t('love_type_married', 'Menikah')}</option>
                  <option value="long_distance">{t('love_type_long_distance', 'Hubungan jarak jauh')}</option>
                </select>
              </label>
              <label className="block text-slate-400">
                {t('love_start_date', 'Mulai bersama')}
                <input type="date" value={profStart} onChange={(e) => setProfStart(e.target.value)} className={inputCls} />
              </label>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" className={btnGhost} onClick={() => setShowProfile(false)}>{t('msg_cancel', 'Batal')}</button>
            <button type="button" className={btnRose} onClick={saveProfile}>{t('btn_save', 'Simpan')}</button>
          </div>
        </Modal>
      )}

      {/* ── Couple account modal (parity CoupleTrackingDialog: 11 sub-tab per pasangan) ── */}
      {showTracking && (
        <Modal title={t('ct_title', 'Tracking Couple')} onClose={() => setShowTracking(false)} wide>
          {!tracking ? (
            <p className="text-xs text-slate-500 text-center py-6">{t('loading', 'Memproses...')}</p>
          ) : tracking.ok === false || !(tracking.pair || []).length ? (
            <p className="text-xs text-slate-500 text-center py-6">{t('ct_no_couple', 'Fitur ini tersedia setelah kamu punya couple.')}</p>
          ) : (
            <div className="space-y-3">
              {/* Sub-tab bar (parity QTabWidget CoupleTrackingDialog) */}
              <div className="flex flex-wrap gap-1">
                {(tracking.pair[0]?.sections || []).map((s: any, i: number) => (
                  <button
                    key={s.key}
                    type="button"
                    onClick={() => setTrackingTab(i)}
                    className={`ct-tab text-[11px] ${
                      trackingTab === i ? 'ct-tab-on ct-tab-rose' : ''
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
              {/* Dua kartu: saya & pasangan (parity _tab_page) */}
              {tracking.pair.map((p: any) => {
                const section = p.sections?.[trackingTab];
                return (
                  <div key={p.id} className="rounded-xl bg-slate-950/60 border border-slate-800 p-3 space-y-1.5">
                    <div className="text-xs font-bold text-slate-200">👤 {p.name}</div>
                    <div className="text-[11px] text-slate-300 space-y-0.5">
                      {(section?.lines || []).map((line: string, i: number) => (
                        <div key={i}>{line}</div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          <div className="flex justify-end mt-4">
            <button type="button" className={btnGhost} onClick={() => setShowTracking(false)}>{t('btn_close', 'Tutup')}</button>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default LoveSpaceView;
