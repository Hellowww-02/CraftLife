import { apiGet, apiPost, authToken, apiBase, apiUploadFile } from './client';

export const studio = {
  // C07: auto-updater — check / download (poll status) / apply.
  updateCheck: () => apiGet<any>('/api/update/check'),
  updateDownload: () => apiPost<any>('/api/update/download', {}),
  updateStatus: () => apiGet<any>('/api/update/status'),
  updateApply: () => apiPost<any>('/api/update/apply', {}),
  addNotebook: (title: string, description?: string, icon?: string) =>
    apiPost<any>('/api/learning/notebooks', { title, description, icon }),
  deleteNotebook: (id: string) => apiPost<any>(`/api/learning/notebooks/${id}/delete`, {}),
  listNotebooks: () => apiGet<any>('/api/learning/notebooks'),
  // A15: `icon` opsional — ikut dikirim supaya emoji notebook benar-benar tersimpan.
  renameNotebook: (id: string, title: string, icon?: string) =>
    apiPost<any>(`/api/learning/notebooks/${id}/rename`, icon ? { title, icon } : { title }),
  generateNotebook: (notebookId: string, type: string, topic = '') =>
    apiPost<any>('/api/learning/generate', { notebookId, type, topic }),
  deleteGeneration: (notebookId: string, generationId: string) =>
    apiPost<any>('/api/learning/generations/delete', { notebookId, generationId }),
  // A06: daftar artefak Studio — ganti nama & duplikat (rename/duplicate) dan ekspor.
  // Ekspor dilakukan dua langkah: server menyiapkan berkas (staged) → UI mengunduhnya
  // lewat `/api/system/download-file?id=…` (jalur unduhan terverifikasi A03.5).
  renameGeneration: (notebookId: string, generationId: string, title: string) =>
    apiPost<any>('/api/learning/generations/rename', { notebookId, generationId, title }),
  duplicateGeneration: (notebookId: string, generationId: string) =>
    apiPost<any>('/api/learning/generations/duplicate', { notebookId, generationId }),
  exportGeneration: (notebookId: string, generationId: string, format: 'md' | 'txt' | 'csv' | 'html' = 'md') =>
    apiGet<any>(
      `/api/learning/generations/export?notebookId=${encodeURIComponent(notebookId)}` +
      `&generationId=${encodeURIComponent(generationId)}&format=${format}`,
    ),
  uploadLearningSource: async (notebookId: string, file: File) => {
    // C02: upload mentah (nama+mime asli ikut) lalu server ekstrak + simpan berkas.
    const up = await apiUploadFile<any>('learning_source', file);
    const inner = up && typeof up.result === 'object' && up.result ? up.result : up;
    if (!inner || inner.ok === false || !inner.path) return inner;
    return apiPost<any>(`/api/learning/notebooks/${notebookId}/upload-source`, {
      path: inner.path,
      orig_name: file.name,
      mime: file.type || '',
    });
  },
  // C02: ekstrak ulang dari berkas asli + URL unduh berkas asli (owner-only).
  reextractSource: (notebookId: string, sourceId: string) =>
    apiPost<any>(`/api/learning/notebooks/${notebookId}/sources/${sourceId}/re-extract`, {}),
  learningSourceFileUrl: (sourceId: string) => `/api/learning/sources/${sourceId}/file`,
  learningSourceContent: (notebookId: string, sourceId: string) =>
    apiPost<any>('/api/learning/source-content', { notebookId, sourceId }),
  addSource: (notebookId: string, title: string, content: string, type?: string) =>
    apiPost<any>(`/api/learning/notebooks/${notebookId}/sources`, { title, content, type }),
  // C03: sumber URL — server yang fetch (website/YouTube terdeteksi otomatis).
  addSourceFromUrl: (notebookId: string, opts: { url: string; type: string; title?: string }) =>
    apiPost<any>(`/api/learning/notebooks/${notebookId}/sources`, opts),
  deleteSource: (notebookId: string, sourceId: string) =>
    apiPost<any>(`/api/learning/notebooks/${notebookId}/sources/${sourceId}/delete`, {}),
  // C04: catatan tersimpan dari jawaban AI.
  addNote: (notebookId: string, title: string, content: string) =>
    apiPost<any>(`/api/learning/notebooks/${notebookId}/notes`, { title, content }),
  deleteNote: (notebookId: string, noteId: string) =>
    apiPost<any>(`/api/learning/notebooks/${notebookId}/notes/${noteId}/delete`, {}),
  // A08: `sourceIds` = sumber terpilih (grounding) — kosong berarti pakai semua sumber.
  chat: (notebookId: string, text: string, sourceIds?: string[]) =>
    apiPost<any>(`/api/learning/notebooks/${notebookId}/chat`, { text, sourceIds: sourceIds || [] }),
  // A08: bangun audio podcast dua host (MP3) + offset tiap giliran untuk pemutar interaktif.
  podcastAudio: (notebookId: string, generationId: string, force = false) =>
    apiPost<any>('/api/learning/podcast/audio', { notebookId, generationId, force }),
  // URL <audio> — menyajikan MP3 dengan HTTP Range supaya bisa di-seek.
  podcastAudioUrl: (notebookId: string, generationId: string) =>
    `/api/learning/podcast/audio?notebook=${encodeURIComponent(notebookId)}&id=${encodeURIComponent(generationId)}`,
  // P48: bersihkan history chat notebook di server (db.clear_learning_chats).
  clearChat: (notebookId: string) =>
    apiPost<any>(`/api/learning/notebooks/${notebookId}/chat/clear`, {}),
  logMusic: (path: string, title?: string, artist?: string) =>
    apiPost<any>('/api/music/play', { path, title, artist }),
  createPlaylist: (name: string) => apiPost<any>('/api/music/playlists', { name }),
  updateLove: (updates: Record<string, unknown>) => apiPost<any>('/api/love/profile', updates),
  loveCoupleTracking: () => apiGet<any>('/api/love/couple-tracking'),
  // A10: kenangan membawa emoji pilihan, tag, favorit & tautan foto galeri.
  addMemory: (payload: { title: string; date: string; description?: string; emoji?: string;
    tags?: string; isFavorite?: boolean; photoId?: string }) =>
    apiPost<any>('/api/love/memories', payload),
  toggleBucket: (id: string) => apiPost<any>(`/api/love/bucket/${id}/toggle`, {}),
  // A10: bucket list membawa kategori, target tanggal, catatan & prioritas.
  addBucket: (payload: { title: string; category?: string; targetDate?: string;
    notes?: string; priority?: number }) => apiPost<any>('/api/love/bucket', payload),
  sendChat: (text: string, otherId?: string) =>
    apiPost<any>('/api/social/messages', { text, otherId }),
  sendGuild: (text: string) => apiPost<any>('/api/guild/messages', { text }),
  // Parity GuildChatDialog._load_messages (guild lokal): daftar pesan + isLeader.
  guildChat: (limit = 100) =>
    apiGet<any>(`/api/guild/messages` + (limit ? `?limit=${limit}` : '')),
  attackGuildBoss: (action: 'light' | 'heavy' | 'block' | 'ultimate' = 'light') =>
    apiPost<any>('/api/guild/boss/attack', { action }),
  startGuildBoss: (bossId: string, teamIds?: string[]) =>
    apiPost<any>('/api/guild/boss/start', { bossId, teamIds }),
  guildSkill: () => apiPost<any>('/api/guild/skill', {}),
  guildQuickHeal: () => apiPost<any>('/api/guild/quick-heal', {}),
  guildRewards: () => apiGet<any>('/api/guild/rewards'),
  claimGuildReward: (id: string) => apiPost<any>(`/api/guild/rewards/${id}/claim`, {}),
  createGuild: (name: string, description?: string) =>
    apiPost<any>('/api/guild/create', { name, description }),
  joinGuild: (guildId: string) => apiPost<any>('/api/guild/join', { guildId }),
  leaveGuild: () => apiPost<any>('/api/guild/leave', {}),
  kickGuild: (userId: string) => apiPost<any>('/api/guild/kick', { userId }),
  inviteGuild: (username: string) => apiPost<any>('/api/guild/invite', { username }),
  inviteGuildFriend: (friendId: string) => apiPost<any>('/api/guild/invite', { friendId }),
  acceptGuildInvite: (id: string) => apiPost<any>(`/api/guild/invites/${id}/accept`, {}),
  rejectGuildInvite: (id: string) => apiPost<any>(`/api/guild/invites/${id}/reject`, {}),
  removeFriend: (friendId: string) => apiPost<any>('/api/friends/remove', { friendId }),
  transferGuild: (userId: string) => apiPost<any>('/api/guild/transfer', { userId }),
  acceptGuildTransfer: (transferId: string) => apiPost<any>('/api/guild/accept-transfer', { transferId }),
  guildDescription: (description: string) => apiPost<any>('/api/guild/description', { description }),
  clearGuildChat: () => apiPost<any>('/api/guild/clear-chat', {}),
  // ── Friends chat (parity ChatDialog hybrid: cloud Supabase / local) ─────
  friendChat: (friendId: number | string, limit = 50) =>
    apiGet<any>(`/api/friends/${friendId}/chat` + (limit ? `?limit=${limit}` : '')),
  sendFriendChat: (
    friendId: number | string,
    text: string,
    replyToId?: string | number | null,
    attachmentIds: (string | number)[] = [],
  ) => apiPost<any>(`/api/friends/${friendId}/chat`, { text, replyToId: replyToId || null, attachmentIds }),
  clearFriendChat: (friendId: number | string) =>
    apiPost<any>(`/api/friends/${friendId}/clear`, {}),
  friendChatAttachment: async (file: File) => {
    const dataBase64 = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error('read_failed'));
      reader.onload = () => {
        const result = String(reader.result || '');
        const comma = result.indexOf(',');
        resolve(comma >= 0 ? result.slice(comma + 1) : result);
      };
      reader.readAsDataURL(file);
    });
    return apiPost<any>('/api/friends/chat/attachment', { name: file.name, dataBase64 });
  },
  discardFriendAttachments: (ids: (string | number)[]) =>
    apiPost<any>('/api/friends/chat/attachments/discard', { ids }),
  friendTyping: (friendId: number | string, isTyping: boolean) =>
    apiPost<any>(`/api/friends/${friendId}/typing`, { isTyping }),
  editFriendMessage: (mid: string | number, text: string, cloud = false) =>
    apiPost<any>(`/api/friends/messages/${mid}/edit`, { text, cloud }),
  deleteFriendMessage: (mid: string | number, cloud = false) =>
    apiPost<any>(`/api/friends/messages/${mid}/delete`, { cloud }),
  reactFriendMessage: (mid: string | number, reaction: string | null, cloud = false) =>
    apiPost<any>(`/api/friends/messages/${mid}/reaction`, { reaction, cloud }),
  customBoss: (body: Record<string, unknown>) => apiPost<any>('/api/guild/custom-boss', body),
  endCouple: () => apiPost<any>('/api/couple/end', {}),
  coupleRequest: (friendId: string) => apiPost<any>('/api/couple/request', { friendId }),
  coupleRespond: (id: string, accept: boolean) => apiPost<any>(`/api/couple/${id}/respond`, { accept }),
  coupleCancel: (id: string) => apiPost<any>(`/api/couple/${id}/cancel`, {}),
  claimPvp: (id: string) => apiPost<any>(`/api/pvp/${id}/claim`, {}),
  sendPvp: (friendId: string) => apiPost<any>('/api/pvp', { friendId }),
  friendRequest: (username: string) => apiPost<any>('/api/friends/request', { username }),
  acceptFriend: (id: string) => apiPost<any>(`/api/friends/${id}/accept`, {}),
  rejectFriend: (id: string) => apiPost<any>(`/api/friends/${id}/reject`, {}),
  respondPvp: (id: string, accept: boolean) => apiPost<any>(`/api/pvp/${id}/respond`, { accept }),
  approveGuildRequest: (id: string) => apiPost<any>(`/api/guild/requests/${id}/approve`, {}),
  rejectGuildRequest: (id: string) => apiPost<any>(`/api/guild/requests/${id}/reject`, {}),
  lovePhotoMeta: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/love/photos/${id}/meta`, body),
  // --- LovePage parity: delete handlers, favorit prompt, album galeri ---
  deleteLovePhoto: (id: string) => apiPost<any>(`/api/love/photos/${id}/delete`, {}),
  deleteLoveMemory: (id: string) => apiPost<any>(`/api/love/memories/${id}/delete`, {}),
  deleteLovePrompt: (id: string) => apiPost<any>(`/api/love/prompts/${id}/delete`, {}),
  deleteLoveWeekly: (id: string) => apiPost<any>(`/api/love/weekly/${id}/delete`, {}),
  deleteLoveCycle: (id: string) => apiPost<any>(`/api/love/cycles/${id}/delete`, {}),
  deleteLoveEvent: (id: string) => apiPost<any>(`/api/love/events/${id}/delete`, {}),
  deleteLoveBucket: (id: string) => apiPost<any>(`/api/love/bucket/${id}/delete`, {}),
  // A10: kenangan bisa diedit & difavoritkan; bucket list bisa diedit dan
  // item yang tercapai dipromosikan menjadi kenangan (satu klik).
  loveMemoryUpdate: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/love/memories/${id}/update`, body),
  loveMemoryFavorite: (id: string) => apiPost<any>(`/api/love/memories/${id}/favorite`, {}),
  loveBucketUpdate: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/love/bucket/${id}/update`, body),
  loveBucketPromote: (id: string) => apiPost<any>(`/api/love/bucket/${id}/promote-to-memory`, {}),
  lovePromptFavorite: (promptKey: string) => apiPost<any>('/api/love/prompt-favorite', { promptKey }),
  createLoveAlbum: (body: { name: string; scope?: string }) => apiPost<any>('/api/love/albums', body),
  renameLoveAlbum: (id: string, name: string) => apiPost<any>(`/api/love/albums/${id}/rename`, { name }),
  deleteLoveAlbum: (id: string) => apiPost<any>(`/api/love/albums/${id}/delete`, {}),
  loveAlbumAddPhoto: (albumId: string, photoId: string) =>
    apiPost<any>(`/api/love/albums/${albumId}/photo`, { photoId }),
  loveAlbumMovePhoto: (albumId: string, photoId: string, sourceAlbumId?: string | null) =>
    apiPost<any>(`/api/love/albums/${albumId}/photo-move`, { photoId, sourceAlbumId }),
  loveAlbumRemovePhoto: (albumId: string, photoId: string) =>
    apiPost<any>(`/api/love/albums/${albumId}/photo-remove`, { photoId }),
  // A11: sampul album + aksi massal galeri (hapus / visibilitas / pindah album).
  loveAlbumCover: (albumId: string, photoId?: string) =>
    apiPost<any>(`/api/love/albums/${albumId}/cover`, photoId ? { photoId } : {}),
  lovePhotosBulk: (body: { action: string; ids: string[]; albumId?: string; visibility?: string }) =>
    apiPost<any>('/api/love/photos/bulk', body),
  // Fetch a Love Space photo as a Blob (with auth) and return an object URL so
  // <img> can render it without exposing the session token in a plain URL.
  lovePhotoImage: (id: string): Promise<string> => {
    const headers: Record<string, string> = { Accept: 'image/*' };
    const token = authToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    return fetch(`${apiBase()}/api/love/photo/image?id=${encodeURIComponent(id)}`, { headers, credentials: 'include' })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.blob();
      })
      .then((b) => URL.createObjectURL(b));
  },
  loveCheckin: (body: Record<string, unknown>) => apiPost<any>('/api/love/checkin', body),
  lovePhoto: (path: string) => apiPost<any>('/api/love/photo', { path }),
  loveEvent: (body: Record<string, unknown>) => apiPost<any>('/api/love/events', body),
  // A09: edit acara (dulu hanya bisa hapus) + daftar acara/hari istimewa yang akan datang.
  loveEventUpdate: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/love/events/${id}/update`, body),
  loveEventsUpcoming: (days = 90) => apiGet<any>(`/api/love/events/upcoming?days=${days}`),
  // A12: pengingat dari hari istimewa Love Space. `<id>` = id acara ATAU kunci
  // profil (my_birthdate / partner_birthdate / start_date) → repeat_type 'yearly'.
  loveEventReminder: (id: string, body: Record<string, unknown> = {}) =>
    apiPost<any>(`/api/love/events/${encodeURIComponent(id)}/create-reminder`, body),
  loveWeekly: (body: Record<string, unknown>) => apiPost<any>('/api/love/weekly', body),
  loveCycle: (body: Record<string, unknown>) => apiPost<any>('/api/love/cycle', body),
  // A11: edit riwayat siklus + pengingat H-n dari prediksi siklus berikutnya.
  loveCycleUpdate: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/love/cycles/${id}/update`, body),
  loveCycleReminder: (body: Record<string, unknown>) => apiPost<any>('/api/love/cycles/create-reminder', body),
  lovePrompt: (body: Record<string, unknown>) => apiPost<any>('/api/love/prompt', body),
  setGeminiKey: (apiKey: string) => apiPost<any>('/api/learning/gemini-key', { apiKey }),
  friends: () => apiGet<any>('/api/friends'),
  friendProfile: (id: string) => apiGet<any>(`/api/friends/${id}/profile`),
  notifications: () => apiGet<any>('/api/notifications'),
  markNotifications: (id?: string) => apiPost<any>('/api/notifications/read', { id: id || 'all' }),
  guild: () => apiGet<any>('/api/guild'),
  pvp: () => apiGet<any>('/api/pvp'),
  love: () => apiGet<any>('/api/love'),
  generate: (kind: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/ai/${kind}`, body),
  searchMusic: (query: string) => apiPost<any>('/api/music/search', { query }),
  downloadMusic: (url: string) => apiPost<any>('/api/music/download', { url }),
  musicJob: (id: string) => apiGet<any>(`/api/music/jobs/${id}`),
  musicLibrary: () => apiGet<any>('/api/music/library'),
  addPlaylistTrack: (playlistId: string | number, path: string) =>
    apiPost<any>('/api/music/playlist-track', { playlistId, path }),
  // Lyrics (LRCLIB get/search multi-varian + lyrics.ovh + embedded) — parity _LyricsFetcher PyQt
  // A02: + album (akurasi versi) & prefer (indeks kandidat pilihan user).
  musicLyrics: (artist: string, title: string, path = '', opts?: { key?: string; duration?: number; refresh?: boolean; album?: string; prefer?: number }) =>
    apiGet<any>(`/api/music/lyrics?artist=${encodeURIComponent(artist)}&title=${encodeURIComponent(title)}&path=${encodeURIComponent(path)}` +
      `${opts?.key ? `&key=${encodeURIComponent(opts.key)}` : ''}${opts?.duration ? `&duration=${opts.duration}` : ''}` +
      `${opts?.album ? `&album=${encodeURIComponent(opts.album)}` : ''}${opts?.refresh ? '&refresh=1' : ''}` +
      `${opts?.prefer !== undefined ? `&prefer=${opts.prefer}` : ''}`),
  // A02: daftar kandidat lirik (album/durasi/versi) — user memilih sumber yang benar.
  musicLyricsCandidates: (opts: { artist?: string; title?: string; album?: string; duration?: number; path?: string; limit?: number }) =>
    apiGet<any>(`/api/music/lyrics-candidates?artist=${encodeURIComponent(opts.artist || '')}` +
      `&title=${encodeURIComponent(opts.title || '')}&album=${encodeURIComponent(opts.album || '')}` +
      `&path=${encodeURIComponent(opts.path || '')}${opts.duration ? `&duration=${opts.duration}` : ''}` +
      `${opts.limit ? `&limit=${opts.limit}` : ''}`),
  // A02: simpan kandidat pilihan user (source "user-pick", tidak tertimpa pencarian web).
  musicLyricsApply: (payload: { key: string; artist?: string; title?: string; plain?: string; synced?: string }) =>
    apiPost<any>('/api/music/lyrics-apply', payload),
  // A02: metadata batch (title/artist/album/duration) untuk trek di luar batas listing library.
  musicTrackMeta: (paths: string[]) =>
    apiGet<any>(`/api/music/track-meta?paths=${paths.map((p) => encodeURIComponent(p)).join('|')}`),
  // P58: lirik tersimpan per track — simpan / hapus / import manual / offset.
  musicLyricsSave: (payload: { key: string; title?: string; artist?: string; source?: string; plain?: string; synced?: string; offsetMs?: number }) =>
    apiPost<any>('/api/music/lyrics-save', payload),
  musicLyricsDelete: (key: string) => apiPost<any>('/api/music/lyrics-delete', { key }),
  // A03: import manual — server mengembalikan report validasi (format/baris/peringatan).
  musicLyricsImport: (payload: { key: string; title?: string; artist?: string; content: string; duration?: number; offsetMs?: number }) =>
    apiPost<any>('/api/music/lyrics-import', payload),
  // A03: cek file SEBELUM disimpan (bukan toast buta) → laporan baris/peringatan.
  musicLyricsValidate: (payload: { key?: string; content: string; duration?: number }) =>
    apiPost<any>('/api/music/lyrics-validate', payload),
  // A03.5: unduhan template/ekspor lirik kini lewat helper kanonik di client.ts
  // (downloadApiFile) — lihat LyricsImportDialog. Blob tidak dipakai lagi karena
  // Qt WebEngine membuang unduhan blob tanpa handler downloadRequested.
  musicLyricsOffset: (key: string, offsetMs: number) => apiPost<any>('/api/music/lyrics-offset', { key, offsetMs }),
  // P59: icon playlist khusus — emoji via JSON, foto via upload target playlist_icon.
  musicPlaylistIcon: (playlistId: string | number, icon: string) =>
    apiPost<any>('/api/music/playlist-icon', { playlistId, icon }),
  uploadPlaylistIcon: async (playlistId: string | number, file: File) => {
    const up = await apiUploadFile<any>('playlist_icon', file, { playlistId });
    return up && typeof up.result === 'object' && up.result ? up.result : up;
  },
  // P62: pembersihan DB bulanan (history tracker).
  cleanupStatus: () => apiGet<any>('/api/settings/cleanup'),
  cleanupSet: (payload: { retentionDays?: number; auto?: boolean; schedule?: string }) =>
    apiPost<any>('/api/settings/cleanup', { action: 'set', ...payload }),
  cleanupRun: () => apiPost<any>('/api/settings/cleanup', { action: 'run' }),
  cleanupCheckpoint: () => apiPost<any>('/api/settings/cleanup', { action: 'checkpoint' }),
  cleanupVacuum: () => apiPost<any>('/api/settings/cleanup', { action: 'vacuum' }),
  uploadMusicFile: async (file: File) => {
    // Parity MusicPage._add_files/_select_folder: file masuk folder library
    // musik server lalu direferensikan playlist berdasar path absolut.
    const up = await apiUploadFile<any>('music', file);
    return up && typeof up.result === 'object' && up.result ? up.result : up;
  },
  // Playlist management (rename/delete/remove/move/copy)
  renamePlaylist: (playlistId: string | number, name: string) =>
    apiPost<any>('/api/music/playlist-rename', { playlistId, name }),
  deletePlaylist: (playlistId: string | number) =>
    apiPost<any>('/api/music/playlist-delete', { playlistId }),
  removePlaylistTrack: (playlistId: string | number, index: number) =>
    apiPost<any>('/api/music/playlist-track-remove', { playlistId, index }),
  movePlaylistTrack: (fromPlaylistId: string | number, toPlaylistId: string | number, index: number) =>
    apiPost<any>('/api/music/playlist-track-move', { fromPlaylistId, toPlaylistId, index }),
  copyPlaylistTrack: (fromPlaylistId: string | number, toPlaylistId: string | number, index: number) =>
    apiPost<any>('/api/music/playlist-track-copy', { fromPlaylistId, toPlaylistId, index }),
  musicPlaylists: () => apiGet<any>('/api/music/playlists'),
};

