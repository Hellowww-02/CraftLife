import React, { useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { life } from '../../api/life';
import { DEFAULT_FOODS } from '../../data/gameData';
import { Salad, Droplets, Plus, Trash2, Search, RotateCcw, LineChart as LineIcon, ChefHat, X } from 'lucide-react';
import { LineChart, DonutChart } from '../charts';

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
  const { mealLogs, addMealLog, deleteMealLog, waterLog, addWater, resetWater, lang, healthLogs, addHealthLog, showToast } = useGame();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMealType, setSelectedMealType] = useState<'breakfast' | 'lunch' | 'dinner' | 'snack'>('lunch');
  const [portionInput, setPortionInput] = useState<number>(1);
  const [isCustomModalOpen, setIsCustomModalOpen] = useState(false);
  const [catalog, setCatalog] = useState<CatalogFood[]>([]);
  const [goals, setGoals] = useState({ calories: 2000, protein: 50, carbs: 250, fat: 70 });
  const [editingGoals, setEditingGoals] = useState(false);
  const [waterGoal, setWaterGoal] = useState(waterLog.targetMl || 2000);

  // Recipe manager (parity with PyQt AddRecipeDialog / RecipeManagerDialog)
  type Recipe = { id: string; name: string; icon: string; servingSize: number; notes: string; items: { foodId: string; name: string; quantity: number }[] };
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [recipeModal, setRecipeModal] = useState(false);
  const [rcName, setRcName] = useState('');
  const [rcIcon, setRcIcon] = useState('🍲');
  const [rcServing, setRcServing] = useState(1);
  const [rcNotes, setRcNotes] = useState('');
  const [rcIngredients, setRcIngredients] = useState<{ foodId: string; quantity: number }[]>([{ foodId: '', quantity: 1 }]);
  const [rcLogTarget, setRcLogTarget] = useState<Recipe | null>(null);

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
    life.listRecipes().then((d) => setRecipes(d?.recipes || [])).catch(() => setRecipes([]));
  }, [mealLogs.length]);

  const loadRecipes = () => {
    life.listRecipes().then((d) => setRecipes(d?.recipes || [])).catch(() => setRecipes([]));
  };

  const saveRecipe = async () => {
    if (!rcName.trim()) return;
    const items = rcIngredients.filter((i) => i.foodId);
    if (items.length === 0) return;
    await life.addRecipe({ name: rcName.trim(), icon: rcIcon, servingSize: rcServing, notes: rcNotes, items });
    setRecipeModal(false);
    loadRecipes();
    showToast('success', lang === 'id' ? 'Resep disimpan' : 'Recipe saved', rcName.trim());
  };

  const logRecipe = async (r: Recipe, mult: number) => {
    await life.logRecipe(r.id, { servingMultiplier: mult, mealType: selectedMealType });
    setRcLogTarget(null);
    showToast('success', lang === 'id' ? 'Resep dicatat ke makanan' : 'Recipe logged', r.name);
  };

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

          {editingGoals ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3">
              {(['calories', 'protein', 'carbs', 'fat'] as const).map((k) => (
                <div key={k}>
                  <label className="text-[9px] text-slate-400 font-bold uppercase">{k}</label>
                  <input
                    type="number"
                    value={goals[k]}
                    onChange={(e) => setGoals((g) => ({ ...g, [k]: Number(e.target.value) }))}
                    className="w-full px-2 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-100"
                  />
                </div>
              ))}
              <div className="col-span-2 sm:col-span-4 flex gap-2 justify-end">
                <button onClick={() => setEditingGoals(false)} className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-[11px] font-bold">{lang === 'id' ? 'Batal' : 'Cancel'}</button>
                <button
                  onClick={async () => {
                    await life.saveNutritionGoals({ calories: goals.calories, protein: goals.protein, carbs: goals.carbs, fat: goals.fat });
                    setEditingGoals(false);
                    showToast('success', lang === 'id' ? 'Target nutrisi tersimpan' : 'Nutrition goals saved', '');
                  }}
                  className="px-3 py-1.5 rounded-lg bg-teal-500 text-slate-950 text-[11px] font-bold"
                >
                  {lang === 'id' ? 'Simpan' : 'Save'}
                </button>
              </div>
            </div>
          ) : (
            <button onClick={() => setEditingGoals(true)} className="mt-3 text-[11px] font-bold text-teal-300 hover:text-teal-200">
              {lang === 'id' ? 'Edit target nutrisi' : 'Edit nutrition goals'}
            </button>
          )}
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

      {/* Health Chart (parity with PyQt HealthChartWidget: steps/sleep/mood) */}
      {(() => {
        const sorted = [...healthLogs].sort((a, b) => (a.date < b.date ? -1 : 1)).slice(-14);
        const stepData = sorted.map((h) => ({ label: h.date.slice(5), value: h.steps }));
        const sleepData = sorted.map((h) => ({ label: h.date.slice(5), value: h.sleepHours }));
        const moodCount = new Map<string, number>();
        sorted.forEach((h) => moodCount.set(h.mood || 'good', (moodCount.get(h.mood || 'good') || 0) + 1));
        const moodColors: Record<string, string> = { great: '#34d399', good: '#38bdf8', neutral: '#a78bfa', tired: '#f59e0b', stressed: '#f43f5e' };
        const moodData = [...moodCount.entries()].map(([k, v]) => ({ label: k, value: v, color: moodColors[k] || '#64748b' }));
        return (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
              <div className="flex items-center gap-2 mb-3">
                <LineIcon className="w-5 h-5 text-teal-400" />
                <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Kesehatan (Langkah & Tidur)' : 'Health (Steps & Sleep)'}</h3>
              </div>
              {sorted.length === 0 ? (
                <p className="text-sm text-slate-500 py-6 text-center">{lang === 'id' ? 'Belum ada data kesehatan.' : 'No health data yet.'}</p>
              ) : (
                <>
                  <div className="text-[10px] uppercase text-slate-400 font-bold mb-1">{lang === 'id' ? 'Langkah' : 'Steps'}</div>
                  <LineChart data={stepData} color="#34d399" width={680} height={120} />
                  <div className="text-[10px] uppercase text-slate-400 font-bold mt-4 mb-1">{lang === 'id' ? 'Jam Tidur' : 'Sleep (h)'}</div>
                  <LineChart data={sleepData} color="#38bdf8" width={680} height={120} showGrid={false} />
                </>
              )}
            </div>
            <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
              <div className="flex items-center gap-2 mb-3">
                <Droplets className="w-5 h-5 text-violet-400" />
                <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Mood' : 'Mood'}</h3>
              </div>
              {moodData.length === 0 ? (
                <p className="text-sm text-slate-500 py-6 text-center">{lang === 'id' ? 'Belum ada data mood.' : 'No mood data yet.'}</p>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <DonutChart data={moodData} size={140} strokeWidth={16} centerLabel={String(sorted.length)} centerSub={lang === 'id' ? 'hari' : 'days'} />
                  <div className="space-y-1 w-full">
                    {moodData.map((m) => (
                      <div key={m.label} className="flex items-center justify-between text-[11px]">
                        <span className="flex items-center gap-1.5 text-slate-300"><span className="w-2.5 h-2.5 rounded-full" style={{ background: m.color }} />{m.label}</span>
                        <span className="text-slate-400 font-semibold">{m.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })()}

      {/* Recipe Manager (parity with PyQt AddRecipeDialog / RecipeManagerDialog) */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <ChefHat className="w-5 h-5 text-amber-400" />
            <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Resep Makanan' : 'Food Recipes'}</h3>
          </div>
          <button onClick={() => { setRcName(''); setRcIcon('🍲'); setRcServing(1); setRcNotes(''); setRcIngredients([{ foodId: '', quantity: 1 }]); setRecipeModal(true); }} className="px-3 py-1.5 rounded-xl bg-amber-600 text-white text-xs font-bold flex items-center gap-1">
            <Plus className="w-3.5 h-3.5" /> {lang === 'id' ? 'Resep baru' : 'New recipe'}
          </button>
        </div>
        {recipes.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-4">{lang === 'id' ? 'Belum ada resep.' : 'No recipes yet.'}</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {recipes.map((r) => (
              <div key={r.id} className="p-3 rounded-xl bg-slate-800/60 border border-slate-700">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-xl">{r.icon}</span>
                    <div className="min-w-0">
                      <div className="font-bold text-slate-100 text-sm truncate">{r.name}</div>
                      <div className="text-[11px] text-slate-400">{r.items.length} {lang === 'id' ? 'bahan' : 'ingredients'} · {r.servingSize} {lang === 'id' ? 'porsi' : 'serving'}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button onClick={() => setRcLogTarget(r)} className="px-2 py-1 rounded-lg bg-teal-500/20 text-teal-300 text-[10px] font-bold">{lang === 'id' ? 'Log' : 'Log'}</button>
                    <button onClick={() => life.deleteRecipe(r.id).then(loadRecipes)} className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400"><Trash2 className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
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

      {/* Add Recipe Modal */}
      {recipeModal && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-3 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-black text-slate-100">{lang === 'id' ? 'Resep Baru' : 'New Recipe'}</h3>
              <button onClick={() => setRecipeModal(false)} className="text-slate-400 hover:text-slate-200"><X className="w-5 h-5" /></button>
            </div>
            <input value={rcName} onChange={(e) => setRcName(e.target.value)} placeholder={lang === 'id' ? 'Nama resep…' : 'Recipe name…'} className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm" />
            <div className="grid grid-cols-[auto,1fr] gap-2 items-center">
              <label className="text-slate-400 text-xs">{lang === 'id' ? 'Ikon' : 'Icon'}</label>
              <input value={rcIcon} onChange={(e) => setRcIcon(e.target.value)} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm w-20" />
            </div>
            <div className="grid grid-cols-[auto,1fr] gap-2 items-center">
              <label className="text-slate-400 text-xs">{lang === 'id' ? 'Porsi' : 'Serving'}</label>
              <input type="number" min={1} value={rcServing} onChange={(e) => setRcServing(Math.max(1, Number(e.target.value) || 1))} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm w-24" />
            </div>
            <textarea value={rcNotes} onChange={(e) => setRcNotes(e.target.value)} placeholder={lang === 'id' ? 'Instruksi…' : 'Instructions…'} rows={2} className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm resize-none" />
            <div>
              <label className="text-slate-300 text-xs font-semibold">{lang === 'id' ? 'Bahan' : 'Ingredients'}</label>
              <div className="space-y-2 mt-1">
                {rcIngredients.map((ing, idx) => (
                  <div key={idx} className="flex gap-2">
                    <select value={ing.foodId} onChange={(e) => { const next = [...rcIngredients]; next[idx] = { ...ing, foodId: e.target.value }; setRcIngredients(next); }} className="flex-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs">
                      <option value="">— {lang === 'id' ? 'pilih bahan' : 'choose food'} —</option>
                      {dbFoods.map((f) => <option key={f.id} value={f.id}>{f.icon} {f.name}</option>)}
                    </select>
                    <input type="number" min={0.1} step={0.5} value={ing.quantity} onChange={(e) => { const next = [...rcIngredients]; next[idx] = { ...ing, quantity: Number(e.target.value) }; setRcIngredients(next); }} className="w-16 px-2 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs" />
                    <button onClick={() => setRcIngredients(rcIngredients.filter((_, i) => i !== idx))} className="px-2 text-rose-400"><X className="w-4 h-4" /></button>
                  </div>
                ))}
              </div>
              <button onClick={() => setRcIngredients([...rcIngredients, { foodId: '', quantity: 1 }])} className="mt-2 px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-bold">{lang === 'id' ? '+ Tambah bahan' : '+ Add ingredient'}</button>
            </div>
            <div className="flex items-center justify-end gap-2 pt-1">
              <button onClick={() => setRecipeModal(false)} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold text-xs">{lang === 'id' ? 'Batal' : 'Cancel'}</button>
              <button onClick={saveRecipe} disabled={!rcName.trim() || !rcIngredients.some((i) => i.foodId)} className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-slate-950 font-bold text-xs">{lang === 'id' ? 'Simpan' : 'Save'}</button>
            </div>
          </div>
        </div>
      )}

      {/* Log Recipe Modal */}
      {rcLogTarget && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-sm w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-black text-slate-100">{lang === 'id' ? 'Catat Resep' : 'Log Recipe'} — {rcLogTarget.name}</h3>
              <button onClick={() => setRcLogTarget(null)} className="text-slate-400 hover:text-slate-200"><X className="w-5 h-5" /></button>
            </div>
            <div>
              <label className="text-slate-300 text-xs font-semibold">{lang === 'id' ? 'Jumlah porsi' : 'Servings'}</label>
              <input type="number" min={0.5} step={0.5} defaultValue={1} id={`rc-mult-${rcLogTarget.id}`} className="w-full mt-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm" />
            </div>
            <div className="flex items-center justify-end gap-2 pt-1">
              <button onClick={() => setRcLogTarget(null)} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold text-xs">{lang === 'id' ? 'Batal' : 'Cancel'}</button>
              <button onClick={() => logRecipe(rcLogTarget, Number((document.getElementById(`rc-mult-${rcLogTarget.id}`) as HTMLInputElement)?.value || 1))} className="px-4 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs">{lang === 'id' ? 'Log' : 'Log'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
