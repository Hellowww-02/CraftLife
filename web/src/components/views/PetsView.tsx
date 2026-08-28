import React from 'react';
import { useGame } from '../../context/GameContext';
import { livePets } from '../../data/liveCatalog';
import { Dog, Heart, Zap, Sparkles, Coins, Check, ArrowRight } from 'lucide-react';

export const PetsView: React.FC = () => {
  const { user, userPets, adoptPet, feedPet, trainPet, equipPet, unequipPet, lang } = useGame();
  const PETS_DATA = livePets();
  const allPetsList = Object.values(PETS_DATA);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Dog className="w-6 h-6 text-indigo-400" />
            <h2 className="text-xl font-black text-slate-100">{lang === 'id' ? 'Kandang Pet Sahabat' : 'Pet Sanctuary & Companions'}</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {lang === 'id'
              ? 'Adopsi hewan pendamping setia, beri makan, latih ketangkasan mereka, dan aktifkan buff bonus XP/Gold di setiap pertarungan!'
              : 'Adopt loyal companions, feed them, train their combat agility, and summon passive buffs for your adventure!'}
          </p>
        </div>
      </div>

      {/* Adopted Pets Section */}
      <div className="space-y-3">
        <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Hewan Peliharaan Dimiliki' : 'Your Adopted Companions'} ({userPets.length})</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {userPets.map((pet) => {
            const petMeta = PETS_DATA[pet.petId];
            if (!petMeta) return null;

            const nextXp = pet.level * 60;
            const xpPct = Math.min(100, Math.round((pet.xp / nextXp) * 100));

            return (
              <div
                key={pet.petId}
                className={`p-4.5 rounded-2xl border flex flex-col justify-between gap-4 transition-all ${
                  pet.isEquipped
                    ? 'bg-indigo-950/30 border-indigo-500/50 shadow-lg shadow-indigo-500/10'
                    : 'bg-slate-900/80 border-slate-800'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-3xl shrink-0">
                        {petMeta.icon}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-extrabold text-sm text-slate-100">{pet.nickname || petMeta.name}</h4>
                          <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                            Lv.{pet.level}
                          </span>
                        </div>
                        <div className="text-[11px] font-bold text-emerald-400 mt-0.5">
                          ✨ {petMeta.bonus}
                        </div>
                      </div>
                    </div>

                    {pet.isEquipped && (
                      <span className="px-2 py-0.5 text-[10px] font-extrabold rounded-full bg-indigo-500 text-slate-950">
                        Active
                      </span>
                    )}
                  </div>

                  {/* Level Progress Bar */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[10px] text-slate-400">
                      <span>Pet XP</span>
                      <span>{pet.xp} / {nextXp}</span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-300"
                        style={{ width: `${xpPct}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Pet Care Controls */}
                <div className="pt-3 border-t border-slate-800 space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => feedPet(pet.petId)}
                      className="py-1.5 px-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-amber-300 font-bold text-xs flex items-center justify-center gap-1 border border-slate-700"
                      title="Feed Pet (15 Gold)"
                    >
                      <span>🍖</span> {lang === 'id' ? 'Beri Makan (15g)' : 'Feed (15g)'}
                    </button>
                    <button
                      onClick={() => trainPet(pet.petId)}
                      className="py-1.5 px-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-sky-300 font-bold text-xs flex items-center justify-center gap-1 border border-slate-700"
                      title="Train Pet (15 MP)"
                    >
                      <span>⚡</span> {lang === 'id' ? 'Latih (15 MP)' : 'Train (15 MP)'}
                    </button>
                  </div>

                  {pet.isEquipped ? (
                    <button
                      onClick={unequipPet}
                      className="w-full py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs"
                    >
                      {lang === 'id' ? 'Istirahatkan Pet' : 'Rest Companion'}
                    </button>
                  ) : (
                    <button
                      onClick={() => equipPet(pet.petId)}
                      className="w-full py-1.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-slate-950 font-bold text-xs"
                    >
                      {lang === 'id' ? 'Panggil Bertualang' : 'Summon to Battle'}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Sanctuary Market - Pets to Adopt */}
      <div className="space-y-3 pt-4 border-t border-slate-800">
        <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Pilihan Pet untuk Diadopsi' : 'Adoption Sanctuary'}</h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {allPetsList.map((pet) => {
            const isOwned = userPets.some((p) => p.petId === pet.id);
            const canAfford = user.gold >= pet.cost;

            return (
              <div
                key={pet.id}
                className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 flex items-center justify-between gap-3"
              >
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-3xl shrink-0">
                    {pet.icon}
                  </div>
                  <div>
                    <h4 className="font-bold text-sm text-slate-100">{pet.name}</h4>
                    <div className="text-[11px] font-bold text-emerald-400">{pet.bonus}</div>
                    <div className="text-xs font-bold text-amber-300 mt-0.5">{pet.cost} Gold</div>
                  </div>
                </div>

                {isOwned ? (
                  <span className="px-3 py-1 rounded-xl bg-slate-800 text-emerald-400 text-xs font-bold flex items-center gap-1">
                    <Check className="w-3.5 h-3.5" /> {lang === 'id' ? 'Dimiliki' : 'Owned'}
                  </span>
                ) : (
                  <button
                    onClick={() => adoptPet(pet.id)}
                    disabled={!canAfford}
                    className={`px-3.5 py-2 rounded-xl font-bold text-xs transition-all ${
                      canAfford
                        ? 'bg-indigo-500 hover:bg-indigo-400 text-slate-950 shadow-md active:scale-95'
                        : 'bg-slate-800 text-slate-400 cursor-not-allowed'
                    }`}
                  >
                    {lang === 'id' ? 'Adopsi' : 'Adopt'}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
