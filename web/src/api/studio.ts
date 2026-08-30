import { apiGet, apiPost, authToken, apiBase, apiUploadFile } from './client';

export const studio = {
  addNotebook: (title: string, description?: string, icon?: string) =>
    apiPost<any>('/api/learning/notebooks', { title, description, icon }),
  deleteNotebook: (id: string) => apiPost<any>(`/api/learning/notebooks/${id}/delete`, {}),
  listNotebooks: () => apiGet<any>('/api/learning/notebooks'),
  renameNotebook: (id: string, title: string) =>
    apiPost<any>(`/api/learning/notebooks/${id}/rename`, { title }),
  generateNotebook: (notebookId: string, type: string, topic = '') =>
    apiPost<any>('/api/learning/generate', { notebookId, type, topic }),
  deleteGeneration: (notebookId: string, generationId: string) =>
    apiPost<any>('/api/learning/generations/delete', { notebookId, generationId }),
  uploadLearningSource: async (notebookId: string, file: File) => {
    // Parity LearningPage._add_source_files: upload mentah lalu server ekstrak.
    const up = await apiUploadFile<any>('learning_source', file);
    const inner = up && typeof up.result === 'object' && up.result ? up.result : up;
    if (!inner || inner.ok === false || !inner.path) return inner;
    return apiPost<any>(`/api/learning/notebooks/${notebookId}/upload-source`, { path: inner.path });
  },
  learningSourceContent: (notebookId: string, sourceId: string) =>
    apiPost<any>('/api/learning/source-content', { notebookId, sourceId }),
  addSource: (notebookId: string, title: string, content: string, type?: string) =>
    apiPost<any>(`/api/learning/notebooks/${notebookId}/sources`, { title, content, type }),
  deleteSource: (notebookId: string, sourceId: string) =>
    apiPost<any>(`/api/learning/notebooks/${notebookId}/sources/${sourceId}/delete`, {}),
  chat: (notebookId: string, text: string) =>
    apiPost<any>(`/api/learning/notebooks/${notebookId}/chat`, { text }),
  logMusic: (path: string, title?: string, artist?: string) =>
    apiPost<any>('/api/music/play', { path, title, artist }),
  createPlaylist: (name: string) => apiPost<any>('/api/music/playlists', { name }),
  updateLove: (updates: Record<string, unknown>) => apiPost<any>('/api/love/profile', updates),
  addMemory: (title: string, date: string, description: string, emoji?: string) =>
    apiPost<any>('/api/love/memories', { title, date, description, emoji }),
  toggleBucket: (id: string) => apiPost<any>(`/api/love/bucket/${id}/toggle`, {}),
  addBucket: (title: string) => apiPost<any>('/api/love/bucket', { title }),
  sendChat: (text: string, otherId?: string) =>
    apiPost<any>('/api/social/messages', { text, otherId }),
  sendGuild: (text: string) => apiPost<any>('/api/guild/messages', { text }),
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
  acceptGuildInvite: (id: string) => apiPost<any>(`/api/guild/invites/${id}/accept`, {}),
  rejectGuildInvite: (id: string) => apiPost<any>(`/api/guild/invites/${id}/reject`, {}),
  removeFriend: (friendId: string) => apiPost<any>('/api/friends/remove', { friendId }),
  transferGuild: (userId: string) => apiPost<any>('/api/guild/transfer', { userId }),
  acceptGuildTransfer: (transferId: string) => apiPost<any>('/api/guild/accept-transfer', { transferId }),
  guildDescription: (description: string) => apiPost<any>('/api/guild/description', { description }),
  clearGuildChat: () => apiPost<any>('/api/guild/clear-chat', {}),
  // ── Friends chat lokal (parity ChatDialog) ──────────────────────────────
  friendChat: (friendId: number | string, limit = 100) =>
    apiGet<any>(`/api/friends/${friendId}/chat` + (limit ? `?limit=${limit}` : '')),
  sendFriendChat: (friendId: number | string, text: string, replyToId?: string | number | null) =>
    apiPost<any>(`/api/friends/${friendId}/chat`, { text, replyToId: replyToId || null }),
  clearFriendChat: (friendId: number | string) =>
    apiPost<any>(`/api/friends/${friendId}/clear`, {}),
  editFriendMessage: (mid: string | number, text: string) =>
    apiPost<any>(`/api/friends/messages/${mid}/edit`, { text }),
  deleteFriendMessage: (mid: string | number) =>
    apiPost<any>(`/api/friends/messages/${mid}/delete`, {}),
  reactFriendMessage: (mid: string | number, reaction: string | null) =>
    apiPost<any>(`/api/friends/messages/${mid}/reaction`, { reaction }),
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
  loveWeekly: (body: Record<string, unknown>) => apiPost<any>('/api/love/weekly', body),
  loveCycle: (body: Record<string, unknown>) => apiPost<any>('/api/love/cycle', body),
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
  // Lyrics (3-provider: LRCLIB get/search + lyrics.ovh) — parity dengan _LyricsFetcher PyQt
  musicLyrics: (artist: string, title: string) =>
    apiGet<any>(`/api/music/lyrics?artist=${encodeURIComponent(artist)}&title=${encodeURIComponent(title)}`),
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

