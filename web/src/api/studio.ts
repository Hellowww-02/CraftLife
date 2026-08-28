import { apiGet, apiPost } from './client';

export const studio = {
  addNotebook: (title: string, description?: string, icon?: string) =>
    apiPost<any>('/api/learning/notebooks', { title, description, icon }),
  deleteNotebook: (id: string) => apiPost<any>(`/api/learning/notebooks/${id}/delete`, {}),
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
  attackGuildBoss: (damage?: number) => apiPost<any>('/api/guild/boss/attack', { damage }),
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
};

