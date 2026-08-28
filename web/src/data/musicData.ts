import { MusicTrack } from '../types';

export const DEFAULT_MUSIC_TRACKS: MusicTrack[] = [
  {
    id: 'lofi_cozy_coffee',
    title: 'Rainy Cafe Chillhop',
    artist: 'Lofi Study Beats',
    duration: '3:45',
    url: 'https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=lofi-study-112191.mp3',
    coverEmoji: '☕',
    category: 'lofi',
    isFavorite: true,
  },
  {
    id: 'lofi_midnight_focus',
    title: 'Midnight Coding Flow',
    artist: 'Deep Work Radio',
    duration: '4:12',
    url: 'https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0a13f69d2.mp3?filename=chill-abstract-intention-12099.mp3',
    coverEmoji: '🌙',
    category: 'focus',
    isFavorite: true,
  },
  {
    id: 'ambient_rain_forest',
    title: 'Kyoto Rain & Bamboo',
    artist: 'Nature Soundscapes',
    duration: '5:30',
    url: 'https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8b417c093.mp3?filename=soft-rain-ambient-111154.mp3',
    coverEmoji: '🎋',
    category: 'ambient',
  },
  {
    id: 'synth_alpha_waves',
    title: 'Alpha Wave 10Hz Focus',
    artist: 'Binaural Laboratory',
    duration: '6:00',
    url: 'https://cdn.pixabay.com/download/audio/2021/08/04/audio_0625c1539c.mp3?filename=relaxing-mountains-nature-walk-11263.mp3',
    coverEmoji: '🧠',
    category: 'synth',
  },
];

export const AMBIENT_SOUNDS = [
  { id: 'rain', nameEn: 'Gentle Rain', nameId: 'Hujan Lembut', icon: '🌧️', defaultVolume: 60 },
  { id: 'fire', nameEn: 'Fireplace Hearth', nameId: 'Perapian Kayu', icon: '🔥', defaultVolume: 50 },
  { id: 'waves', nameEn: 'Ocean Tide', nameId: 'Ombak Pantai', icon: '🌊', defaultVolume: 40 },
  { id: 'birds', nameEn: 'Forest Birds', nameId: 'Burung Hutan', icon: '🌲', defaultVolume: 45 },
  { id: 'cafe', nameEn: 'Cozy Coffee Shop', nameId: 'Suasana Kafe', icon: '☕', defaultVolume: 35 },
  { id: 'wind', nameEn: 'Mountain Breeze', nameId: 'Angin Gunung', icon: '🍃', defaultVolume: 30 },
  { id: 'whitenoise', nameEn: 'White Noise Flow', nameId: 'Derau Putih', icon: '📻', defaultVolume: 25 },
];
