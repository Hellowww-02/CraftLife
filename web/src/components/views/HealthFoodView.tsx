import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { life } from '../../api/life';
import { apiBase } from '../../api/client';
import { DEFAULT_FOODS } from '../../data/gameData';
import { t } from '../../i18n';
import { Salad, Droplets, Plus, Trash2, Search, LineChart as LineIcon, ChefHat, X, Download, ChevronLeft, ChevronRight, Activity } from 'lucide-react';
import { LineChart } from '../charts';

// ── trv: terjemahan dengan interpolasi {var} (mendukung spec format {v:.1f}) ──
export function trv(key: string, vars: Record<string, string | number>, fallback: string): string {
  let s = t(key, fallback);
  for (const [k, v] of Object.entries(vars)) {
    s = s.replace(new RegExp(`\\{${k}(:[^}]*)?\\}`, 'g'), String(v));
  }
  return s.replace(/<[^>]*>/g, '');
}

const MEALS = ['breakfast', 'lunch', 'dinner', 'snack'] as const;
const ACTIVITY_FACTORS = [1.2, 1.375, 1.55, 1.725, 1.9];
const ACTIVITY_KEYS = ['food_bmi_activity_sedentary', 'food_bmi_activity_light', 'food_bmi_activity_moderate', 'food_bmi_activity_active', 'food_bmi_activity_very_active'];

const todayISO = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};
const shiftISO = (iso: string, delta: number) => {
  const d = new Date(iso + 'T00:00:00');
  d.setDate(d.getDate() + delta);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

type CatalogFood = { id: string; name: string; icon: string; calories: number; protein: number; carbs: number; fat: number; isCustom?: boolean };

/** HealthFoodPage PyQt → versi web. Seluruh data di server; UI hanya render. */
export const HealthFoodView: React.FC = () => {
  const { lang, showToast, applyLive } = useGame();

  // ── Date selector (parity _build_date_selector; ▶ disabled pada hari ini) ──
  const [day, setDay] = useState(todayISO());
  const [dayData, setDayData] = useState<any>(null);
  const [hist, setHist] = useState<any>(null);
  const loadDay = useCallback(() => {
    life.healthfoodDay(day).then((d) => { if (d?.ok !== false) setDayData(d); }).catch(() => undefined);
    life.healthfoodHistory().then((d) => { if (d?.ok !== false) setHist(d); }).catch(() => undefined);
  }, [day]);
  useEffect(() => { setDayData(null); loadDay(); }, [loadDay]);

  // Nutrition daily bonus (parity _check_nutrition_bonus): hanya tanggal hari ini, 1×/hari.
  const bonusCheckedRef = useRef<string>('');
  useEffect(() => {
    if (!dayData?.isToday || bonusCheckedRef.current === dayData.date) return;
    bonusCheckedRef.current = dayData.date;
    life.nutritionBonus(dayData.date).then((res: any) => {
      if (res?.ok && res?.result?.ok) {
        applyLive(res);
        let msg = trv('health_nutrition_bonus_msg', { xp: res.result.xp_gained ?? 50, gold: res.result.gold_gained ?? 10 }, '🍎 Bonus nutrisi!');
        if (res.result.leveled_up) msg += t('level_up_bonus', '\n🎉 LEVEL UP!');
        showToast('level_up', t('bonus_title', 'Bonus'), msg);
      }
    }).catch(() => undefined);
  }, [dayData, applyLive, showToast]);

  const dateLabel = new Date(day + 'T00:00:00').toLocaleDateString(lang === 'id' ? 'id-ID' : 'en-GB', {
    weekday: 'long', day: '2-digit', month: 'long', year: 'numeric',
  });

  const nutrition = dayData?.nutrition || { calories: 0, protein: 0, carbs: 0, fat: 0 };
  const goals = dayData?.goals || { calories: 2000, protein: 50, carbs: 250, fat: 70 };
  const calPct = goals.calories > 0 ? Math.round((nutrition.calories / goals.calories) * 100) : 0;
  const calBarColor = calPct >= 100 ? '#e05050' : calPct >= 80 ? '#f0a800' : '#80c000';

  const [editGoals, setEditGoals] = useState(false);
  const [goalForm, setGoalForm] = useState({ calories: 2000, protein: 50, carbs: 250, fat: 70 });
  const openGoals = () => { setGoalForm({ ...goals }); setEditGoals(true); };

  // ── Water section ──
  const water = dayData?.water || { totalMl: 0, goalMl: 2500, logs: [] };
  const [waterGoalInput, setWaterGoalInput] = useState(2500);
  const [waterCustom, setWaterCustom] = useState(1000);
  const [waterGoalOpen, setWaterGoalOpen] = useState(false);
  const addWater = async (amount: number) => {
    try {
      const res = await life.addWater(amount, day);
      applyLive(res);
      loadDay();
    } catch (e: any) {
      showToast('info', String(e?.message || e), '');
    }
  };
  const deleteWater = async (id: string) => {
    const res = await life.deleteWaterLog(id);
    applyLive(res);
    loadDay();
  };
  const saveWaterGoal = async () => {
    await life.setWaterGoal(waterGoalInput).catch(() => undefined);
    setWaterGoalOpen(false);
    loadDay();
  };

  // ── BMI section ──
  type BmiForm = { heightCm: number; weightKg: number; age: number; gender: string; activityFactor: number };
  const bmiInit = (dayData?.bmi || { heightCm: 170, weightKg: 70, age: 25, gender: 'male', activityFactor: 1.375 }) as BmiForm;
  const [bmiForm, setBmiForm] = useState<BmiForm>(bmiInit);
  const [bmiResult, setBmiResult] = useState<string | null>(null);
  useEffect(() => { if (dayData?.bmi) setBmiForm(dayData.bmi); }, [dayData?.bmi]);
  const bmiActivityIdx = Math.max(0, ACTIVITY_FACTORS.indexOf(Number(bmiForm.activityFactor)));
  const saveBmi = async () => {
    await life.saveBmi({
      heightCm: bmiForm.heightCm, weightKg: bmiForm.weightKg, age: bmiForm.age,
      gender: bmiForm.gender, activityFactor: ACTIVITY_FACTORS[bmiActivityIdx] ?? ACTIVITY_FACTORS[Array.from(ACTIVITY_KEYS).findIndex((_, i) => i === bmiActivityIdx)] ?? 1.375,
    }).catch(() => undefined);
    showToast('success', t('food_bmi_profile_saved', 'Profil BMI tersimpan'), '');
    loadDay();
  };
  const calcBmi = () => {
    const h = (Number(bmiForm.heightCm) || 170) / 100;
    const bmiVal = (Number(bmiForm.weightKg) || 0) / (h * h);
    const key = bmiVal < 18.5 ? 'underweight' : bmiVal < 25 ? 'normal' : bmiVal < 30 ? 'overweight' : 'obese';
    const color = bmiVal < 18.5 ? '#f0a800' : bmiVal < 25 ? '#80c000' : '#e05050';
    setBmiResult(trv('food_bmi_result_format', { color, bmi: bmiVal.toFixed(1), status: t('food_bmi_status_' + key, key) }, `BMI: ${bmiVal.toFixed(1)}`));
  };
  const setAutoGoals = async () => {
    const res = await life.autoNutritionGoals({
      weightKg: bmiForm.weightKg, heightCm: bmiForm.heightCm, age: bmiForm.age,
      gender: bmiForm.gender, activityFactor: ACTIVITY_FACTORS[bmiActivityIdx] ?? 1.375,
    }).catch(() => null);
    if (res?.ok) {
      applyLive(res);
      showToast('success', t('food_target_updated_title', 'Target diperbarui'), trv('food_target_updated_msg', { cal: res?.result?.calories ?? 0 }, ''));
      loadDay();
    }
  };

  // ── Health status + input ──
  const hlog = dayData?.healthLog || null;
  const hgoals = dayData?.healthGoals || { dailySteps: 10000, dailySleepHours: 7, heightCm: 170, weightKg: 70 };
  const [hForm, setHForm] = useState({ steps: 0, sleep: 0, hr: 0, weightKg: 70, heightCm: 170, mood: 'normal', stress: 'normal', notes: '' });
  useEffect(() => {
    setHForm({
      steps: hlog?.steps ?? 0,
      sleep: hlog?.sleep_hours ?? 0,
      hr: hlog?.resting_hr ?? 0,
      weightKg: hlog?.weight_kg ?? hgoals.weightKg,
      heightCm: hlog?.height_cm ?? hgoals.heightCm,
      mood: hlog?.mood ?? 'normal',
      stress: hlog?.stress_level ?? 'normal',
      notes: hlog?.notes ?? '',
    });
  }, [dayData?.healthLog]); // eslint-disable-line react-hooks/exhaustive-deps
  const saveHealth = async () => {
    const res = await life.saveHealthFull({
      steps: hForm.steps, sleepHours: hForm.sleep, heartRate: hForm.hr,
      weightKg: hForm.weightKg, heightCm: hForm.heightCm,
      mood: hForm.mood, stress: hForm.stress, notes: hForm.notes, logDate: day,
    });
    applyLive(res);
    showToast('success', t('health_data_saved', 'Data kesehatan tersimpan'), '');
    loadDay();
  };

  // ── Food: catalog, log, move, custom ──
  const [catalog, setCatalog] = useState<CatalogFood[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [portionInput, setPortionInput] = useState(1);
  const [mealTarget, setMealTarget] = useState<(typeof MEALS)[number]>('lunch');
  // Parity AddFoodDialog mode "log": kolom catatan per-entry (opsional).
  const [logNotes, setLogNotes] = useState('');
  const [recipeCreateOpen, setRecipeCreateOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [customOpen, setCustomOpen] = useState(false);
  const [custom, setCustom] = useState({ name: '', calories: 200, protein: 15, carbs: 20, fat: 5 });

  useEffect(() => {
    life.foodItems().then((d) => setCatalog(d.items || [])).catch(() => setCatalog([]));
  }, [day]);
  const dbFoods: CatalogFood[] = catalog.length
    ? catalog
    : DEFAULT_FOODS.map((f) => ({ id: f.id, name: lang === 'id' ? f.nameId : f.nameEn, icon: f.icon, calories: f.calories, protein: f.protein, carbs: f.carbs, fat: f.fat }));
  const filteredFoods = dbFoods.filter((f) => f.name.toLowerCase().includes(searchQuery.toLowerCase()));

  const logFood = async (food: CatalogFood) => {
    const res = await life.logFood({
      mealType: mealTarget, foodName: food.name, icon: food.icon, portion: portionInput,
      calories: food.calories, protein: food.protein, carbs: food.carbs, fat: food.fat, date: day,
      notes: logNotes.trim() || undefined,
    });
    applyLive(res);
    loadDay();
  };
  const addCustomAndLog = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!custom.name.trim()) return;
    // Parity AddFoodDialog mode "add": simpan ke katalog saja; pengguna kemudian
    // me-log dari food explorer (bukan auto-log ke meal).
    await life.addCustomFood({ name: custom.name, calories: custom.calories, protein: custom.protein, carbs: custom.carbs, fat: custom.fat }).catch(() => undefined);
    const items = await life.foodItems().catch(() => null);
    if (items?.items) setCatalog(items.items);
    setCustomOpen(false);
    setCustom({ name: '', calories: 200, protein: 15, carbs: 20, fat: 5 });
  };
  const removeFoodLog = async (id: string) => {
    const res = await life.deleteFoodLog(id);
    applyLive(res);
    loadDay();
  };
  const moveFoodLog = async (id: string, toMeal: string) => {
    const res = await life.moveFoodLog(id, toMeal);
    applyLive(res);
    loadDay();
  };

  // ── Recipes (parity RecipeManagerDialog, ringkas) ──
  type Recipe = { id: string; name: string; icon: string; servingSize: number; notes: string; items: { foodId: string; name: string; quantity: number }[] };
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const loadRecipes = useCallback(() => { life.listRecipes().then((d) => setRecipes(d?.recipes || [])).catch(() => undefined); }, []);
  useEffect(() => { loadRecipes(); }, [loadRecipes]);

  // ── Export (parity _export_nutrition) ──
  const doExport = async (fmt: 'csv' | 'xlsx' | 'docx') => {
    try {
      const resp = await fetch(`${apiBase()}/api/nutrition/export?format=${fmt}&days=30`, { credentials: 'include' });
      if (!resp.ok) throw new Error(String(resp.status));
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `craftlife_nutrition.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
      setExportOpen(false);
    } catch (e: any) {
      showToast('info', String(e?.message || e), '');
    }
  };

  const foodLogs: any[] = dayData?.foodLogs || [];
  const statusCards = [
    ['health_steps', trv('health_steps_value', { steps: hlog?.steps ?? 0, goal: hgoals.dailySteps }, ''), '#80c000'],
    ['health_sleep', trv('health_sleep_value', { sleep: (hlog?.sleep_hours ?? 0).toFixed(1), goal: hgoals.dailySleepHours }, ''), '#4da6ff'],
    ['health_water', trv('health_water_value', { water: water.totalMl, goal: water.goalMl }, ''), '#38bdf8'],
    ['health_mood', trv('health_mood_value', { mood: t('health_mood_' + (hlog?.mood ?? 'normal'), hlog?.mood ?? 'normal') }, ''), '#f0a800'],
    ['health_weight', trv('health_weight_value', { weight: hlog?.weight_kg ?? hgoals.weightKg }, ''), '#a97fff'],
    ['health_height', trv('health_height_value', { height: hgoals.heightCm }, ''), '#a97fff'],
    ['health_hr', trv('health_hr_value', { hr: hlog?.resting_hr ?? 0 }, ''), '#e05050'],
    ['health_stress', trv('health_stress_value', { stress: t('health_stress_' + (hlog?.stress_level ?? 'normal'), hlog?.stress_level ?? 'normal') }, ''), '#80c000'],
    ['health_calories', trv('health_calories_value', { cal: Math.round(nutrition.calories), goal: goals.calories }, ''), '#ff9f1c'],
    ['health_protein', trv('health_protein_value', { protein: Math.round(nutrition.protein), goal: goals.protein }, ''), '#f4a261'],
    ['health_burned', trv('health_burned_value', { burned: dayData?.caloriesBurned ?? 0 }, ''), '#e76f51'],
    ['health_net_calories', trv('health_net_calories_value', { net: dayData?.netCalories ?? 0, goal: goals.calories }, ''), '#2a9d8f'],
  ] as const;

  return (
    <div className="space-y-6">
      {/* ── Date selector (◀ [tanggal] ▶ [Hari ini]) ── */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 flex items-center gap-2 flex-wrap">
        <Salad className="w-6 h-6 text-teal-400" />
        <h2 className="text-xl font-black text-slate-100 mr-2">
          {lang === 'id' ? 'Kesehatan & Nutrisi' : 'Health & Food'}
        </h2>
        <div className="ml-auto flex items-center gap-2">
          <button type="button" onClick={() => setDay((d) => shiftISO(d, -1))} className="p-2 rounded-lg bg-slate-800 text-slate-200"><ChevronLeft className="w-4 h-4" /></button>
          <span className="text-xs font-bold text-slate-200 min-w-[210px] text-center">{dateLabel}</span>
          <button type="button" disabled={day >= todayISO()} onClick={() => setDay((d) => shiftISO(d, +1))} className="p-2 rounded-lg bg-slate-800 text-slate-200 disabled:opacity-30"><ChevronRight className="w-4 h-4" /></button>
          <button type="button" onClick={() => setDay(todayISO())} className="px-3 py-2 rounded-lg bg-amber-500 text-slate-950 text-xs font-black">{t('food_today', 'Hari Ini')}</button>
        </div>
      </div>

      {/* ── Nutrition summary (4 kartu + progress + target) ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {([
          ['food_cal_stat', `${Math.round(nutrition.calories)} / ${goals.calories} kcal`, '#f0a800'],
          ['food_protein_stat', `${Math.round(nutrition.protein)} / ${goals.protein} g`, '#80c000'],
          ['food_carbs_stat', `${Math.round(nutrition.carbs)} / ${goals.carbs} g`, '#4da6ff'],
          ['food_fat_stat', `${Math.round(nutrition.fat)} / ${goals.fat} g`, '#e05050'],
        ] as const).map(([key, val, color]) => (
          <div key={key} className="rounded-xl bg-slate-900 border border-slate-800 p-3">
            <div className="text-[11px] text-slate-400">{t(key, key)}</div>
            <div className="text-base font-bold" style={{ color }}>{val}</div>
          </div>
        ))}
      </div>
      <div className="w-full h-3 rounded-full bg-slate-800 border border-slate-700 overflow-hidden">
        <div className="h-full transition-all duration-300" style={{ width: `${Math.min(100, calPct)}%`, background: calBarColor }} />
      </div>
      <div className="flex justify-end">
        <button type="button" onClick={openGoals} className="px-4 py-2 rounded-xl bg-amber-500 text-slate-950 text-xs font-black">
          {t('food_set_goals_btn', '🎯 Atur Target Nutrisi')}
        </button>
      </div>

      {/* ── Water section (parity _build_water_section) ── */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2"><Droplets className="w-4 h-4 text-cyan-400" /> {t('food_tab_water', '💧 Tracker Air')}</h3>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-300">Target: {water.goalMl} ml</span>
            <button type="button" onClick={() => { setWaterGoalInput(water.goalMl); setWaterGoalOpen(true); }} className="px-3 py-1.5 rounded-xl bg-amber-500 text-slate-950 text-[11px] font-black">{t('food_water_set_goal', 'Atur Target')}</button>
          </div>
        </div>
        <div className="text-[11px] text-slate-400">{trv('water_progress_format', { current: water.totalMl, goal: water.goalMl }, `${water.totalMl} / ${water.goalMl} ml`)}</div>
        <div className="w-full h-5 rounded-full bg-slate-800 border border-slate-700 overflow-hidden">
          <div className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300" style={{ width: `${Math.min(100, (water.totalMl / Math.max(1, water.goalMl)) * 100)}%` }} />
        </div>
        <div className="flex gap-2 flex-wrap">
          {([250, 500, 1000] as const).map((amount) => (
            <button key={amount} type="button" onClick={() => addWater(amount)} className="px-3 py-2 rounded-xl bg-cyan-500/20 border border-cyan-500/40 text-cyan-300 text-xs font-bold">
              {t(`food_water_add_${amount}`, `+${amount} ml`)}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <label className="text-[11px] text-slate-400">{t('food_water_custom_label', 'Custom:')}</label>
          <input type="number" min={1} max={5000} value={waterCustom} onChange={(e) => setWaterCustom(Math.max(1, Math.min(5000, Number(e.target.value) || 1000)))}
            className="w-24 px-2 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs" />
          <span className="text-[11px] text-slate-500">{t('unit_ml', ' ml')}</span>
          <button type="button" onClick={() => addWater(waterCustom)} className="px-3 py-1.5 rounded-lg bg-cyan-600 text-white text-[11px] font-bold">{t('dialog_add', '➕  Tambah')}</button>
        </div>

        <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3 space-y-2">
          <div className="text-[11px] font-bold text-slate-400 uppercase">{t('food_water_log_title', 'Riwayat Air (hari ini)')}</div>
          {(!water.logs || water.logs.length === 0) ? (
            <p className="text-xs text-slate-500 text-center py-4">{t('food_no_water_today', 'Belum minum air hari ini.')}</p>
          ) : (
            <div className="space-y-1">
              {water.logs.map((w: any) => (
                <div key={w.id} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs">
                  <span>💧</span>
                  <span className="flex-1 font-bold text-slate-100">+{w.amountMl} ml</span>
                  <span className="text-slate-500">{w.time}</span>
                  <button type="button" onClick={() => deleteWater(w.id)} className="p-1 text-slate-500 hover:text-rose-400">🗑</button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── BMI section (parity _build_bmi_section) ── */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-3">
        <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2"><Activity className="w-4 h-4 text-emerald-400" /> {t('food_bmi_title', '📏 BMI & Profil Tubuh')}</h3>
        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
          <label className="space-y-1">
            <span className="text-slate-400">{t('food_bmi_height', 'Tinggi (cm)')}</span>
            <input type="number" min={100} max={250} step={0.5} value={bmiForm.heightCm} onChange={(e) => setBmiForm((f) => ({ ...f, heightCm: Number(e.target.value) || 170 }))} className="w-full px-2 py-2 rounded-lg bg-slate-800 border border-slate-700" />
          </label>
          <label className="space-y-1">
            <span className="text-slate-400">{t('food_bmi_weight', 'Berat (kg)')}</span>
            <input type="number" min={30} max={300} step={0.5} value={bmiForm.weightKg} onChange={(e) => setBmiForm((f) => ({ ...f, weightKg: Number(e.target.value) || 70 }))} className="w-full px-2 py-2 rounded-lg bg-slate-800 border border-slate-700" />
          </label>
          <label className="space-y-1">
            <span className="text-slate-400">{t('food_bmi_age', 'Usia (tahun)')}</span>
            <input type="number" min={15} max={100} value={bmiForm.age} onChange={(e) => setBmiForm((f) => ({ ...f, age: Math.max(15, Math.min(100, Number(e.target.value) || 25)) }))} className="w-full px-2 py-2 rounded-lg bg-slate-800 border border-slate-700" />
          </label>
          <label className="space-y-1">
            <span className="text-slate-400">{t('food_bmi_gender', 'Jenis Kelamin')}</span>
            <select value={String(bmiForm.gender).toLowerCase() === 'female' ? 'female' : 'male'} onChange={(e) => setBmiForm((f) => ({ ...f, gender: e.target.value }))} className="w-full px-2 py-2 rounded-lg bg-slate-800 border border-slate-700">
              <option value="male">{t('food_bmi_gender_m', 'Laki-laki')}</option>
              <option value="female">{t('food_bmi_gender_f', 'Perempuan')}</option>
            </select>
          </label>
          <label className="space-y-1 sm:col-span-2">
            <span className="text-slate-400">{t('food_bmi_activity', 'Tingkat Aktivitas')}</span>
            <select value={bmiActivityIdx} onChange={(e) => setBmiForm((f) => ({ ...f, activityFactor: ACTIVITY_FACTORS[Number(e.target.value)] ?? 1.375 }))} className="w-full px-2 py-2 rounded-lg bg-slate-800 border border-slate-700">
              {ACTIVITY_KEYS.map((k, i) => (<option key={i} value={i}>{t(k, k)}</option>))}
            </select>
          </label>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button type="button" onClick={saveBmi} className="px-3 py-2 rounded-xl bg-teal-600 text-white text-xs font-bold">{t('food_bmi_save_profile', '💾 Simpan Profil')}</button>
          <button type="button" onClick={calcBmi} className="px-3 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-bold">{t('food_bmi_calc', 'Hitung BMI')}</button>
          <button type="button" onClick={setAutoGoals} className="px-3 py-2 rounded-xl bg-amber-500 text-slate-950 text-xs font-black">{t('food_bmi_set_target', '🎯 Set Target Otomatis')}</button>
        </div>
        {bmiResult && (
          <div className="text-xs font-bold text-teal-300 bg-slate-950/60 rounded-lg p-2">{bmiResult}</div>
        )}
      </div>

      {/* ── Action buttons parity _build_action_buttons ── */}
      <div className="flex gap-2 flex-wrap">
        <button type="button" onClick={() => setCustomOpen(true)} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-bold border border-slate-700">{t('food_add_custom', '➕ Tambah Makanan Kustom')}</button>
        <button type="button" onClick={() => setRecipeCreateOpen(true)} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-bold border border-slate-700">{t('food_recipes', '📖 Resep')}</button>
        <button type="button" onClick={() => setExportOpen(true)} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-bold border border-slate-700 flex items-center gap-1"><Download className="w-3.5 h-3.5" /> {t('food_export', '📤 Ekspor Nutrisi')}</button>
      </div>

      {/* ── Food explorer (parity AddFoodDialog mode "log") + catatan makanan (parity _refresh_food_log) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Database Makanan' : 'Food Database'}</h3>
            <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 p-1 rounded-xl text-xs">
              {MEALS.map((m) => (
                <button key={m} type="button" onClick={() => setMealTarget(m)} className={`px-2.5 py-1 rounded-lg capitalize font-semibold transition-colors ${mealTarget === m ? 'bg-teal-500 text-slate-950' : 'text-slate-400 hover:text-slate-200'}`}>
                  {t('food_meal_' + m, m)}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={lang === 'id' ? 'Cari makanan (Ayam, Nasi, Telur...)' : 'Search food items...'}
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-100 focus:outline-none focus:border-teal-500" />
            </div>
            <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 px-2 py-1.5 rounded-xl text-xs">
              <span className="text-slate-400 font-semibold">{lang === 'id' ? 'Porsi:' : 'Portion:'}</span>
              <input type="number" step="0.5" min="0.5" max="10" value={portionInput} onChange={(e) => setPortionInput(Math.max(0.5, Number(e.target.value)))} className="w-12 bg-slate-800 text-slate-100 rounded px-1.5 py-0.5 text-center font-bold" />
            </div>
          </div>
          {/* Parity AddFoodDialog log-mode: kolom catatan diterapkan ke semua log berikutnya */}
          <input
            type="text"
            value={logNotes}
            onChange={(e) => setLogNotes(e.target.value)}
            placeholder={lang === 'id' ? 'Catatan log (opsional, mis. tanpa nasi, double protein)...' : 'Log notes (optional, e.g. no rice, double protein)...'}
            className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-100 focus:outline-none focus:border-teal-500"
          />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-80 overflow-y-auto pr-1">
            {filteredFoods.slice(0, 60).map((food) => (
              <div key={food.id} className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-teal-500/40 flex items-center justify-between gap-3 transition-all">
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="text-2xl">{food.icon}</span>
                  <div className="min-w-0">
                    <div className="font-bold text-xs text-slate-100 truncate">{food.name}{food.isCustom ? ' ★' : ''}</div>
                    <div className="text-[10px] text-slate-400">{Math.round(food.calories * portionInput)} kcal · {Math.round(food.protein * portionInput * 10) / 10}g Pro</div>
                  </div>
                </div>
                <button type="button" onClick={() => logFood(food)} className="px-2.5 py-1.5 rounded-lg bg-teal-500/20 hover:bg-teal-500/30 text-teal-300 font-bold text-xs border border-teal-500/40 flex items-center gap-1 shrink-0">
                  <Plus className="w-3.5 h-3.5" /> {t('food_log', 'Log')}
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Catatan makanan tanggal ini (parity: grouped per meal, move cross-meal, delete) */}
        <div className="space-y-3">
          <h3 className="font-bold text-sm text-slate-200">{t('food_log_group_title', '📝 Catatan Makanan')}</h3>
          {foodLogs.length === 0 ? (
            <p className="text-xs text-slate-500 text-center py-8 bg-slate-900/40 rounded-xl border border-slate-800/80">{t('food_no_logs_today', 'Belum ada catatan makanan untuk tanggal ini.')}</p>
          ) : (
            MEALS.map((meal) => {
              const items = foodLogs.filter((l) => l.mealType === meal);
              if (!items.length) return null;
              return (
                <div key={meal} className="space-y-1.5">
                  <div className="text-[11px] font-bold text-slate-300 uppercase">{t('food_meal_' + meal, meal)}</div>
                  {items.map((log) => (
                    <div key={log.id} className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 flex items-start gap-2">
                      <span className="text-xl">{log.icon}</span>
                      <div className="flex-1 min-w-0">
                        <div className="font-bold text-xs text-slate-100">{trv('food_log_name_serving', { name: log.name, serving: Number(log.serving).toFixed(1) }, `${log.name} (${log.serving}x)`)}</div>
                        <div className="text-[10px] text-slate-400">{trv('food_nutrition_detail', { cal: Math.round(log.calories), protein: Math.round(log.protein), carbs: Math.round(log.carbs), fat: Math.round(log.fat) }, `${Math.round(log.calories)} kcal`)}</div>
                        {!!log.notes && <div className="text-[10px] text-slate-500 italic">📝 {log.notes}</div>}
                        {/* Pindah meal (parity drag-drop _refresh_food_log drop area) */}
                        <select
                          value={log.mealType}
                          onChange={(e) => moveFoodLog(log.id, e.target.value)}
                          className="mt-1 text-[10px] px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300"
                        >
                          {MEALS.map((m) => (<option key={m} value={m}>{t('food_meal_' + m, m)}</option>))}
                        </select>
                      </div>
                      <button type="button" onClick={() => removeFoodLog(log.id)} className="p-1 text-slate-500 hover:text-rose-400"><Trash2 className="w-3.5 h-3.5" /></button>
                    </div>
                  ))}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* ── Health status grid (parity _refresh_health_status 12 kartu + catatan) ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {statusCards.map(([key, val, color]) => (
          <div key={key} className="rounded-xl bg-slate-900 border border-slate-800 p-2.5">
            <div className="text-[10px] text-slate-400">{t(key, key)}</div>
            <div className="text-sm font-bold truncate" style={{ color }}>{val}</div>
          </div>
        ))}
      </div>
      <div className="rounded-xl bg-slate-900 border border-slate-800 p-3 text-xs italic text-slate-400">
        {hlog?.notes ? `📝  ${hlog.notes}` : t('health_note_placeholder', 'Belum ada catatan untuk tanggal ini.')}
      </div>

      {/* ── Health input (parity _build_health_input_section) ── */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-3">
        <h3 className="font-bold text-sm text-slate-200">{t('health_tab_input', '📥 Input Data Kesehatan')}</h3>
        <div className="grid md:grid-cols-3 gap-4 text-xs">
          <div className="space-y-2 rounded-xl bg-slate-950/50 border border-slate-800 p-3">
            <div className="font-bold text-slate-300">{t('health_activity_group', '🏃 Aktivitas Fisik')}</div>
            <label className="block"><span className="text-slate-400">{t('health_steps_label', 'Langkah')}</span>
              <input type="number" min={0} max={50000} value={hForm.steps} onChange={(e) => setHForm((f) => ({ ...f, steps: Math.max(0, Math.min(50000, Number(e.target.value) || 0)) }))} className="w-full mt-0.5 px-2 py-1.5 rounded-lg bg-slate-800 border border-slate-700" /></label>
            <label className="block"><span className="text-slate-400">{t('health_hr_label', 'HR Istirahat')}</span>
              <input type="number" min={0} max={220} value={hForm.hr} onChange={(e) => setHForm((f) => ({ ...f, hr: Math.max(0, Math.min(220, Number(e.target.value) || 0)) }))} className="w-full mt-0.5 px-2 py-1.5 rounded-lg bg-slate-800 border border-slate-700" /></label>
            <label className="block"><span className="text-slate-400">{t('health_weight', 'Berat (kg)')}</span>
              <input type="number" min={30} max={300} step={0.5} value={hForm.weightKg} onChange={(e) => setHForm((f) => ({ ...f, weightKg: Math.max(30, Math.min(300, Number(e.target.value) || 70)) }))} className="w-full mt-0.5 px-2 py-1.5 rounded-lg bg-slate-800 border border-slate-700" /></label>
            <label className="block"><span className="text-slate-400">{t('health_height', 'Tinggi (cm)')}</span>
              <input type="number" min={100} max={250} step={0.5} value={hForm.heightCm} onChange={(e) => setHForm((f) => ({ ...f, heightCm: Math.max(100, Math.min(250, Number(e.target.value) || 170)) }))} className="w-full mt-0.5 px-2 py-1.5 rounded-lg bg-slate-800 border border-slate-700" /></label>
          </div>
          <div className="space-y-2 rounded-xl bg-slate-950/50 border border-slate-800 p-3">
            <div className="font-bold text-slate-300">{t('health_sleep_group', '😴 Tidur & Suasana')}</div>
            <label className="block"><span className="text-slate-400">{t('health_sleep_label', 'Durasi Tidur (jam)')}</span>
              <input type="number" min={0} max={24} step={0.5} value={hForm.sleep} onChange={(e) => setHForm((f) => ({ ...f, sleep: Math.max(0, Math.min(24, Number(e.target.value) || 0)) }))} className="w-full mt-0.5 px-2 py-1.5 rounded-lg bg-slate-800 border border-slate-700" /></label>
            <label className="block"><span className="text-slate-400">{t('health_stress_label', 'Stres')}</span>
              <select value={hForm.stress} onChange={(e) => setHForm((f) => ({ ...f, stress: e.target.value }))} className="w-full mt-0.5 px-2 py-1.5 rounded-lg bg-slate-800 border border-slate-700">
                <option value="low">{t('health_stress_low', 'Rendah')}</option>
                <option value="normal">{t('health_stress_normal', 'Normal')}</option>
                <option value="high">{t('health_stress_high', 'Tinggi')}</option>
              </select></label>
            <label className="block"><span className="text-slate-400">{t('health_mood_label', 'Mood')}</span>
              <select value={hForm.mood} onChange={(e) => setHForm((f) => ({ ...f, mood: e.target.value }))} className="w-full mt-0.5 px-2 py-1.5 rounded-lg bg-slate-800 border border-slate-700">
                <option value="happy">{t('health_mood_happy', 'Senang')}</option>
                <option value="normal">{t('health_mood_normal', 'Normal')}</option>
                <option value="tired">{t('health_mood_tired', 'Lelah')}</option>
                <option value="sad">{t('health_mood_sad', 'Sedih')}</option>
              </select></label>
          </div>
          <div className="space-y-2 rounded-xl bg-slate-950/50 border border-slate-800 p-3 flex flex-col">
            <div className="font-bold text-slate-300">{t('health_notes_group', '📝 Catatan')}</div>
            <input type="text" value={hForm.notes} onChange={(e) => setHForm((f) => ({ ...f, notes: e.target.value }))} placeholder={t('health_notes_placeholder', 'Bagaimana kondisi tubuhmu hari ini…')}
              className="w-full px-2 py-2 rounded-lg bg-slate-800 border border-slate-700" />
            <button type="button" onClick={saveHealth} className="mt-auto px-3 py-2 rounded-xl bg-teal-500 text-slate-950 text-xs font-black">{t('health_save', '💾 Simpan Data')}</button>
          </div>
        </div>
      </div>

      {/* ── History charts (parity _refresh_history_charts) ── */}
      {hist && (
        <div className="space-y-4">
          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
            <h3 className="font-bold text-sm text-slate-200 mb-3 flex items-center gap-2"><LineIcon className="w-4 h-4 text-teal-400" /> {t('health_avg_7days', '📊 Rata-rata 7 Hari')}</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {([
                ['health_avg_steps', String(hist.avg7?.steps ?? 0), '#80c000', ''],
                ['health_avg_sleep', `${hist.avg7?.sleep ?? 0} ${t('health_unit_hour', 'jam')}`, '#4da6ff', ''],
                ['health_avg_water', `${hist.avg7?.water ?? 0} ${t('health_unit_ml', 'ml')}`, '#38bdf8', ''],
                ['health_avg_hr', `${hist.avg7?.hr ?? 0} ${t('health_unit_bpm', 'bpm')}`, '#e05050', ''],
              ] as const).map(([key, val, color]) => (
                <div key={key} className="rounded-xl bg-slate-950/60 border border-slate-800 p-3">
                  <div className="text-[10px] text-slate-400">{t(key, key)}</div>
                  <div className="text-sm font-black" style={{ color }}>{val}</div>
                  <div className="text-[9px] text-slate-500">{t('health_avg_7days_suffix', '/7 hari')}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
              <h4 className="text-xs font-bold text-slate-300 mb-2">{t('health_weight_trend', '⚖️ Tren Berat Badan')}</h4>
              <LineChart data={hist.weightSeries || []} color="#80c000" width={460} height={140} />
            </div>
            <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
              <h4 className="text-xs font-bold text-slate-300 mb-2">{t('health_height_trend', '📏 Tren Tinggi Badan')}</h4>
              <LineChart data={hist.heightSeries || []} color="#4da6ff" width={460} height={140} />
            </div>
          </div>
          <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
            <h4 className="text-xs font-bold text-slate-300 mb-1">💡 {t('health_tips', 'Tips')}</h4>
            <p className="text-xs text-slate-300">
              {t(hist.tips?.static || 'health_tip_static_1', '')} {t(hist.tips?.dynamic || 'health_tip_calorie_normal', '')}
            </p>
          </div>
        </div>
      )}

      {/* ── Recipes panel parity RecipeManagerDialog (log/delete/manage) ── */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <ChefHat className="w-5 h-5 text-amber-400" />
            <h3 className="font-bold text-sm text-slate-200">{t('food_recipes', '📖 Resep Makanan')}</h3>
          </div>
          <button type="button" onClick={() => setRecipeCreateOpen(true)} className="px-3 py-1.5 rounded-xl bg-amber-600 text-white text-xs font-bold flex items-center gap-1">
            <Plus className="w-3.5 h-3.5" /> {lang === 'id' ? 'Kelola / Baru' : 'Manage / New'}
          </button>
        </div>
        {recipes.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-4">{lang === 'id' ? 'Belum ada resep.' : 'No recipes yet.'}</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {recipes.map((r) => (
              <div key={r.id} className="p-3 rounded-xl bg-slate-800/60 border border-slate-700 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xl">{r.icon}</span>
                  <div className="min-w-0">
                    <div className="font-bold text-slate-100 text-sm truncate">{r.name}</div>
                    <div className="text-[11px] text-slate-400">{r.items.length} {lang === 'id' ? 'bahan' : 'ingredients'} · {r.servingSize} {lang === 'id' ? 'porsi' : 'serving'}</div>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button type="button" onClick={async () => { const res = await life.logRecipe(r.id, { servingMultiplier: 1, mealType: mealTarget }); applyLive(res); loadDay(); }} className="px-2 py-1 rounded-lg bg-teal-500/20 text-teal-300 text-[10px] font-bold">{t('food_log', 'Log')}</button>
                  <button type="button" onClick={() => life.deleteRecipe(r.id).then(() => { loadRecipes(); loadDay(); })} className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Custom food modal (parity AddFoodDialog mode "add") ── */}
      {customOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-black text-slate-100">{t('food_add_custom', '➕ Tambah Makanan Kustom')}</h3>
            <form onSubmit={addCustomAndLog} className="space-y-3 text-xs">
              <input type="text" required value={custom.name} onChange={(e) => setCustom((c) => ({ ...c, name: e.target.value }))} placeholder="Nama makanan…" className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" />
              <div className="grid grid-cols-2 gap-3">
                {(([['calories', 'Calories (kcal)'], ['protein', 'Protein (g)'], ['carbs', 'Carbs (g)'], ['fat', 'Fat (g)']] as const)).map(([k, l]) => (
                  <label key={k} className="block text-slate-300 font-semibold">
                    {l}
                    <input type="number" value={custom[k]} onChange={(e) => setCustom((c) => ({ ...c, [k]: Number(e.target.value) }))} className="w-full mt-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" />
                  </label>
                ))}
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button type="button" onClick={() => setCustomOpen(false)} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 font-semibold">{lang === 'id' ? 'Batal' : 'Cancel'}</button>
                <button type="submit" className="px-4 py-2 rounded-xl bg-teal-500 text-slate-950 font-bold">{t('dialog_add', '➕  Tambah')}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Nutrition goals dialog (parity SetGoalsDialog) ── */}
      {editGoals && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-sm w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-3">
            <h3 className="text-lg font-black text-slate-100">{t('health_daily_targets', '🎯 Target Nutrisi Harian')}</h3>
            <label className="block text-xs text-slate-300">{t('food_calories_label', 'Kalori (kcal)')}
              <input type="number" min={500} max={10000} value={goalForm.calories} onChange={(e) => setGoalForm((g) => ({ ...g, calories: Math.max(500, Math.min(10000, Number(e.target.value) || 2000)) }))} className="w-full mt-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" /></label>
            <label className="block text-xs text-slate-300">{t('food_protein_label', 'Protein (g)')}
              <input type="number" min={0} max={500} value={goalForm.protein} onChange={(e) => setGoalForm((g) => ({ ...g, protein: Math.max(0, Math.min(500, Number(e.target.value) || 0)) }))} className="w-full mt-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" /></label>
            <label className="block text-xs text-slate-300">{t('food_carbs_label', 'Karbohidrat (g)')}
              <input type="number" min={0} max={500} value={goalForm.carbs} onChange={(e) => setGoalForm((g) => ({ ...g, carbs: Math.max(0, Math.min(500, Number(e.target.value) || 0)) }))} className="w-full mt-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" /></label>
            <label className="block text-xs text-slate-300">{t('food_fat_label', 'Lemak (g)')}
              <input type="number" min={0} max={200} value={goalForm.fat} onChange={(e) => setGoalForm((g) => ({ ...g, fat: Math.max(0, Math.min(200, Number(e.target.value) || 0)) }))} className="w-full mt-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" /></label>
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" onClick={() => setEditGoals(false)} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold">{lang === 'id' ? 'Batal' : 'Cancel'}</button>
              <button type="button" onClick={async () => { await life.saveNutritionGoals(goalForm).catch(() => undefined); setEditGoals(false); showToast('success', t('food_save_goals', 'Target nutrisi tersimpan'), ''); loadDay(); }} className="px-4 py-2 rounded-xl bg-amber-500 text-slate-950 text-xs font-black">{t('food_save_goals', '💾 Simpan Target')}</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Water goal dialog (parity QInputDialog) ── */}
      {waterGoalOpen && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-xs w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-3">
            <h3 className="text-base font-black text-slate-100">{t('food_water_goal_dialog_title', 'Atur Target Air')}</h3>
            <label className="block text-xs text-slate-300">{t('food_water_goal_dialog_label', 'Target harian (ml):')}
              <input type="number" min={500} max={10000} step={100} value={waterGoalInput} onChange={(e) => setWaterGoalInput(Math.max(500, Math.min(10000, Number(e.target.value) || 2500)))} className="w-full mt-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" /></label>
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" onClick={() => setWaterGoalOpen(false)} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold">{lang === 'id' ? 'Batal' : 'Cancel'}</button>
              <button type="button" onClick={saveWaterGoal} className="px-4 py-2 rounded-xl bg-amber-500 text-slate-950 text-xs font-black">💾 {lang === 'id' ? 'Simpan' : 'Save'}</button>
            </div>
          </div>
        </div>
      )}

      {/* ── New recipe modal (parity AddRecipeDialog, ringkas) ── */}
      {recipeCreateOpen && (
        <NewRecipeModal
          onClose={() => setRecipeCreateOpen(false)}
          onDone={() => { setRecipeCreateOpen(false); loadRecipes(); loadDay(); }}
        />
      )}

      {/* ── Export dialog (parity _export_nutrition) ── */}
      {exportOpen && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-sm w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-black text-slate-100">{t('food_export_format_title', '📤 Ekspor Data Nutrisi')}</h3>
              <button onClick={() => setExportOpen(false)} className="text-slate-400 hover:text-slate-200"><X className="w-5 h-5" /></button>
            </div>
            <p className="text-xs text-slate-400">{t('economy_export_label', 'Pilih format file:')} (30 hari terakhir)</p>
            <div className="grid gap-2">
              <button type="button" onClick={() => doExport('csv')} className="w-full px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-bold text-left">{t('export_csv_option', 'CSV (.csv)')}</button>
              <button type="button" onClick={() => doExport('xlsx')} className="w-full px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-bold text-left">Excel (.xlsx)</button>
              <button type="button" onClick={() => doExport('docx')} className="w-full px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-bold text-left">Word (.docx)</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/** Modal resep baru (parity AddRecipeDialog): nama, ikon, porsi, bahan dari katalog. */
export const NewRecipeModal: React.FC<{ onClose: () => void; onDone: () => void }> = ({ onClose, onDone }) => {
  const { lang } = useGame();
  const [name, setName] = useState('');
  const [icon, setIcon] = useState('🍲');
  const [servingSize, setServingSize] = useState(1);
  const [items, setItems] = useState<{ foodId: string; name: string; quantity: number }[]>([]);
  const [catalog, setCatalog] = useState<any[]>([]);
  const [qty, setQty] = useState(1);
  const [sel, setSel] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    life.foodItems().then((d) => {
      setCatalog(d.items || []);
      if (d.items?.length) setSel(d.items[0].id);
    }).catch(() => undefined);
  }, []);

  const addItem = () => {
    const f = catalog.find((x) => x.id === sel);
    if (!f) return;
    setItems((prev) => ([...prev.filter((x) => x.foodId !== f.id), { foodId: f.id, name: f.name, quantity: qty }]));
  };
  const totalCal = items.reduce((s, it) => s + ((catalog.find((x) => x.id === it.foodId)?.calories || 0) * it.quantity), 0);
  const submit = async () => {
    if (!name.trim() || !items.length) return;
    setBusy(true);
    try {
      await life.addRecipe({ name, icon, servingSize, notes: '', items: items.map((x) => ({ foodId: x.foodId, quantity: x.quantity })) });
      onDone();
    } catch { /* noop */ }
    setBusy(false);
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="max-w-lg w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-black text-slate-100">{lang === 'id' ? '🍲 Buat Resep Baru' : '🍲 Create New Recipe'}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200"><X className="w-5 h-5" /></button>
        </div>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <label className="block text-slate-300 font-semibold">{lang === 'id' ? 'Nama Resep' : 'Recipe Name'}
            <input value={name} onChange={(e) => setName(e.target.value)} className="w-full mt-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" />
          </label>
          <label className="block text-slate-300 font-semibold">{lang === 'id' ? 'Ikon' : 'Icon'}
            <input value={icon} onChange={(e) => setIcon(e.target.value)} className="w-full mt-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" />
          </label>
          <label className="block text-slate-300 font-semibold">{lang === 'id' ? 'Jumlah Porsi' : 'Servings'}
            <input type="number" step="0.5" min="0.5" value={servingSize} onChange={(e) => setServingSize(Math.max(0.5, Number(e.target.value) || 1))} className="w-full mt-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" />
          </label>
        </div>
        <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3 space-y-2 text-xs">
          <div className="font-bold text-slate-300">{lang === 'id' ? 'Bahan' : 'Ingredients'}</div>
          <div className="flex gap-2">
            <select value={sel} onChange={(e) => setSel(e.target.value)} className="flex-1 px-2 py-2 rounded-lg bg-slate-800 border border-slate-700">
              {catalog.map((f) => (<option key={f.id} value={f.id}>{f.icon} {f.name}</option>))}
            </select>
            <input type="number" step="0.5" min="0.5" value={qty} onChange={(e) => setQty(Math.max(0.5, Number(e.target.value) || 1))} className="w-16 px-2 py-2 rounded-lg bg-slate-800 border border-slate-700 text-center" />
            <button type="button" onClick={addItem} className="px-3 py-2 rounded-lg bg-amber-600 text-white font-bold">+</button>
          </div>
          {items.length > 0 && (
            <div className="space-y-1 pt-1">
              {items.map((it) => (
                <div key={it.foodId} className="flex items-center justify-between text-slate-200">
                  <span>{it.name} × {it.quantity}</span>
                  <button type="button" onClick={() => setItems((p) => p.filter((x) => x.foodId !== it.foodId))} className="text-slate-500 hover:text-rose-400"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              ))}
            </div>
          )}
          <div className="text-[10px] text-slate-500">{lang === 'id' ? 'Total kalori' : 'Total calories'}: {Math.round(totalCal)} kcal</div>
        </div>
        <div className="flex justify-end gap-2 text-xs">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 font-bold">{lang === 'id' ? 'Batal' : 'Cancel'}</button>
          <button type="button" disabled={busy || !name.trim() || !items.length} onClick={submit} className="px-4 py-2 rounded-xl bg-amber-500 text-slate-950 font-black disabled:opacity-50">💾 {lang === 'id' ? 'Simpan' : 'Save'}</button>
        </div>
      </div>
    </div>
  );
};
