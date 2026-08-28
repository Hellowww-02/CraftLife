import React, { useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { life } from '../../api/life';
import { DEFAULT_FOODS } from '../../data/gameData';
import { Salad, Droplets, Plus, Trash2, Search, RotateCcw } from 'lucide-react';

type CatalogFood = {
  id: string;
  name: string;
  icon: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  isCustom?: boolean;
};

export const NutritionView: React.FC = () => {
  const { mealLogs, addMealLog, deleteMealLog, waterLog, addWater, resetWater, lang, healthLogs, addHealthLog } = useGame();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMealType, setSelectedMealType] = useState<'breakfast' | 'lunch' | 'dinner' | 'snack'>('lunch');
  const [portionInput, setPortionInput] = useState<number>(1);
  const [isCustomModalOpen, setIsCustomModalOpen] = useState(false);
  const [catalog, setCatalog] = useState<CatalogFood[]>([]);
  const [goals, setGoals] = useState({ calories: 2000, protein: 50, carbs: 250, fat: 70 });
  const [waterGoal, setWaterGoal] = useState(waterLog.targetMl || 2000);

  // Custom Food Form
  const [customName, setCustomName] = useState('');
  const [customCal, setCustomCal] = useState(200);
  const [customPro, setCustomPro] = useState(15);
  const [customCarb, setCustomCarb] = useState(20);
  const [customFat, setCustomFat] = useState(5);

  useEffect(() => {
    life.foodItems().then((d) => setCatalog(d.items || [])).catch(() => setCatalog([]));
    life.nutritionGoals().then((d) => {
      if (d.goals) setGoals(d.goals);
    }).catch(() => undefined);
  }, [mealLogs.length]);

  const dbFoods: CatalogFood[] = catalog.length
    ? catalog
    : DEFAULT_FOODS.map((f) => ({
        id: f.id,
        name: lang === 'id' ? f.nameId : f.nameEn,
        icon: f.icon,
        calories: f.calories,
        protein: f.protein,
        carbs: f.carbs,
        fat: f.fat,
      }));

  const filteredFoods = dbFoods.filter((f) =>
    f.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const totalCalories = mealLogs.reduce((acc, m) => acc + m.calories, 0);
  const totalProtein = Math.round(mealLogs.reduce((acc, m) => acc + m.protein, 0) * 10) / 10;
  const totalCarbs = Math.round(mealLogs.reduce((acc, m) => acc + m.carbs, 0) * 10) / 10;
  const totalFat = Math.round(mealLogs.reduce((acc, m) => acc + m.fat, 0) * 10) / 10;

  const handleAddPresetFood = (food: CatalogFood) => {
    addMealLog(
      selectedMealType,
      food.name,
      food.icon,
      portionInput,
      food.calories,
      food.protein,
      food.carbs,
      food.fat
    );
  };

  const handleAddCustomFood = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customName.trim()) return;
    life.addCustomFood({
      name: customName,
      calories: customCal,
      protein: customPro,
      carbs: customCarb,
      fat: customFat,
    }).then(() => life.foodItems().then((d) => setCatalog(d.items || []))).catch(() => undefined);
    addMealLog(
      selectedMealType,
      customName,
      '🍽️',
      portionInput,
      customCal,
      customPro,
      customCarb,
      customFat
    );
    setIsCustomModalOpen(false);
    setCustomName('');
  };

  const waterPct = Math.min(100, Math.round((waterLog.amountMl / waterLog.targetMl) * 100));

  return (
    <div className="space-y-6">
      {/* Top Banner: Macros Summary & Water Hydration */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Daily Macros Summary */}
        <div className="lg:col-span-2 rounded-2xl bg-gradient-to-r from-teal-950/40 via-slate-900 to-slate-900 border border-teal-500/30 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Salad className="w-6 h-6 text-teal-400" />
              <h2 className="text-xl font-black text-slate-100">{lang === 'id' ? 'Nutrisi & Kalori Harian' : 'Daily Nutrition & Macros'}</h2>
            </div>
            <p className="text-xs text-slate-400">
              {lang === 'id'
                ? 'Pantau asupan kalori dan makronutrisi harian untuk menjaga stamina dan energi petualangmu.'
                : 'Track daily calorie and macronutrient intake to sustain peak energy throughout your heroic journey.'}
            </p>
          </div>

          <div className="grid grid-cols-4 gap-3 mt-4 pt-3 border-t border-slate-800 text-center">
            <div>
              <div className="text-[10px] text-slate-400 font-bold uppercase">{lang === 'id' ? 'Total Kalori' : 'Calories'}</div>
              <div className="text-base font-black text-teal-300">{totalCalories} <span className="text-xs font-normal">/ {goals.calories} kcal</span></div>
            </div>
            <div>
              <div className="text-[10px] text-slate-400 font-bold uppercase">Protein</div>
              <div className="text-base font-black text-rose-400">{totalProtein}g</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-400 font-bold uppercase">Carbs</div>
              <div className="text-base font-black text-amber-400">{totalCarbs}g</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-400 font-bold uppercase">Fat</div>
              <div className="text-base font-black text-sky-400">{totalFat}g</div>
            </div>
          </div>
        </div>

        {/* Water Hydration Tracker */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">{lang === 'id' ? 'Target Air Minum' : 'Water Hydration'}</span>
              <Droplets className="w-5 h-5 text-cyan-400" />
            </div>
            <div className="text-2xl font-black text-cyan-400 mt-2">{waterLog.amountMl} / {waterGoal} ml</div>
            <div className="text-xs text-slate-400 mt-1">
              {waterPct}% {lang === 'id' ? 'tercapai hari ini' : 'of daily goal'}
            </div>
          </div>

          <div className="space-y-2 mt-4">
            <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
                style={{ width: `${waterPct}%` }}
              />
            </div>

            <div className="grid grid-cols-3 gap-1.5 pt-1">
              <button
                onClick={() => addWater(250)}
                className="py-1.5 px-2 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 font-bold text-[11px] border border-cyan-500/40"
              >
                +250ml (Gelas)
              </button>
              <button
                onClick={() => addWater(600)}
                className="py-1.5 px-2 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 font-bold text-[11px] border border-cyan-500/40"
              >
                +600ml (Botol)
              </button>
              <button
                onClick={resetWater}
                className="py-1.5 px-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 font-semibold text-[11px] flex items-center justify-center gap-1"
                title="Reset Water"
              >
                <RotateCcw className="w-3 h-3" /> Reset
              </button>
            </div>
            <div className="flex items-center gap-1 pt-1">
              <input
                type="number"
                value={waterGoal}
                onChange={(e) => setWaterGoal(Number(e.target.value))}
                className="w-20 px-2 py-1 rounded-lg bg-slate-800 border border-slate-700 text-[11px]"
              />
              <button
                type="button"
                onClick={() => life.setWaterGoal(waterGoal).catch(() => undefined)}
                className="px-2 py-1 rounded-lg bg-cyan-500/20 text-cyan-300 text-[11px] font-bold"
              >
                {lang === 'id' ? 'Set target air' : 'Set water goal'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Food Database & Log Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Food Explorer */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Database Makanan & Resep' : 'Food Database'}</h3>

            {/* Meal Selector */}
            <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 p-1 rounded-xl text-xs">
              {(['breakfast', 'lunch', 'dinner', 'snack'] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setSelectedMealType(m)}
                  className={`px-2.5 py-1 rounded-lg capitalize font-semibold transition-colors ${
                    selectedMealType === m ? 'bg-teal-500 text-slate-950' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={lang === 'id' ? 'Cari makanan (Ayam, Nasi, Telur...)' : 'Search food items...'}
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-100 focus:outline-none focus:border-teal-500"
              />
            </div>

            <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 px-2 py-1.5 rounded-xl text-xs">
              <span className="text-slate-400 font-semibold">{lang === 'id' ? 'Porsi:' : 'Portion:'}</span>
              <input
                type="number"
                step="0.5"
                min="0.5"
                max="10"
                value={portionInput}
                onChange={(e) => setPortionInput(Math.max(0.5, Number(e.target.value)))}
                className="w-12 bg-slate-800 text-slate-100 rounded px-1.5 py-0.5 text-center font-bold"
              />
            </div>

            <button
              onClick={() => setIsCustomModalOpen(true)}
              className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-teal-400 font-bold text-xs border border-teal-500/30 whitespace-nowrap"
            >
              + Custom
            </button>
          </div>

          {/* Grid of Foods */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-96 overflow-y-auto pr-1">
            {filteredFoods.map((food) => (
              <div
                key={food.id}
                className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-teal-500/40 flex items-center justify-between gap-3 transition-all"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="text-2xl">{food.icon}</span>
                  <div className="min-w-0">
                    <div className="font-bold text-xs text-slate-100 truncate">
                      {food.name}{food.isCustom ? ' ★' : ''}
                    </div>
                    <div className="text-[10px] text-slate-400">
                      {Math.round(food.calories * portionInput)} kcal · {Math.round(food.protein * portionInput * 10) / 10}g Pro
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => handleAddPresetFood(food)}
                  className="px-2.5 py-1.5 rounded-lg bg-teal-500/20 hover:bg-teal-500/30 text-teal-300 font-bold text-xs border border-teal-500/40 flex items-center gap-1 shrink-0"
                >
                  <Plus className="w-3.5 h-3.5" /> Log
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Right Col: Today's Logged Meals */}
        <div className="space-y-4">
          <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Catatan Makanan Hari Ini' : "Today's Meal Log"}</h3>

          <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
            {mealLogs.map((m) => (
              <div
                key={m.id}
                className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between gap-2"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="text-xl">{m.icon}</span>
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-xs text-slate-100 truncate">{m.foodName}</span>
                      <span className="px-1.5 py-0.2 text-[9px] font-bold rounded-full bg-slate-800 text-teal-400 capitalize">
                        {m.mealType}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400">
                      {m.calories} kcal · {m.protein}g Pro · {m.carbs}g Carb
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => deleteMealLog(m.id)}
                  className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}

            {mealLogs.length === 0 && (
              <div className="text-center py-8 text-xs text-slate-400 bg-slate-900/40 rounded-xl border border-slate-800/80">
                {lang === 'id' ? 'Belum ada makanan yang dicatat hari ini.' : 'No meals logged for today.'}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-3">
        <h3 className="text-sm font-bold text-slate-200">{lang === 'id' ? 'Metrik kesehatan (HealthFoodPage)' : 'Health metrics (HealthFoodPage)'}</h3>
        <form
          className="grid sm:grid-cols-3 gap-2 text-xs"
          onSubmit={(e) => {
            e.preventDefault();
            const fd = new FormData(e.currentTarget);
            addHealthLog(
              Number(fd.get('steps') || 0),
              Number(fd.get('sleep') || 0),
              Number(fd.get('weight') || 0),
              Number(fd.get('hr') || 0),
              'good',
              String(fd.get('notes') || ''),
            );
          }}
        >
          <input name="steps" type="number" placeholder="steps" className="px-2 py-2 rounded-lg bg-slate-950 border border-slate-800" />
          <input name="sleep" type="number" step="0.5" placeholder="sleep h" className="px-2 py-2 rounded-lg bg-slate-950 border border-slate-800" />
          <input name="weight" type="number" step="0.1" placeholder="kg" className="px-2 py-2 rounded-lg bg-slate-950 border border-slate-800" />
          <input name="hr" type="number" placeholder="bpm" className="px-2 py-2 rounded-lg bg-slate-950 border border-slate-800" />
          <input name="notes" placeholder="notes" className="px-2 py-2 rounded-lg bg-slate-950 border border-slate-800 sm:col-span-2" />
          <button type="submit" className="px-3 py-2 rounded-lg bg-teal-500 text-slate-950 font-black">
            {lang === 'id' ? 'Simpan kesehatan' : 'Save health'}
          </button>
        </form>
        {healthLogs.slice(0, 5).map((h) => (
          <div key={h.id} className="text-[11px] text-slate-400">
            {h.date} · {h.steps} steps · {h.sleepHours}h
          </div>
        ))}
      </div>

      {/* Custom Food Modal */}
      {isCustomModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-black text-slate-100">{lang === 'id' ? 'Tambah Makanan Kustom' : 'Add Custom Food'}</h3>

            <form onSubmit={handleAddCustomFood} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Nama Makanan' : 'Food Name'}</label>
                <input
                  type="text"
                  required
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  placeholder="e.g. Sup Buntut / Protein Bar"
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-teal-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Calories (kcal)</label>
                  <input
                    type="number"
                    value={customCal}
                    onChange={(e) => setCustomCal(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Protein (g)</label>
                  <input
                    type="number"
                    value={customPro}
                    onChange={(e) => setCustomPro(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Carbs (g)</label>
                  <input
                    type="number"
                    value={customCarb}
                    onChange={(e) => setCustomCarb(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Fat (g)</label>
                  <input
                    type="number"
                    value={customFat}
                    onChange={(e) => setCustomFat(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-teal-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCustomModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold"
                >
                  {lang === 'id' ? 'Batal' : 'Cancel'}
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold"
                >
                  {lang === 'id' ? 'Simpan & Log' : 'Save & Log'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
