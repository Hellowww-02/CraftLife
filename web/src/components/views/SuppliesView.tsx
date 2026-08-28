import React, { useCallback, useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { life } from '../../api/life';
import { t } from '../../i18n';
import { Package, Plus, Minus, Trash2, Equal } from 'lucide-react';

type SupplyItem = {
  id: string;
  name: string;
  category: string;
  unit: string;
  stock: number;
  minStock: number;
  price: number;
  location: string;
  notes: string;
};

export const SuppliesView: React.FC = () => {
  const { lang, showToast } = useGame();
  const [items, setItems] = useState<SupplyItem[]>([]);
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [stock, setStock] = useState('1');
  const [unit, setUnit] = useState('pcs');
  const [minStock, setMinStock] = useState('0');
  const [price, setPrice] = useState('0');
  const [location, setLocation] = useState('');

  const load = useCallback(async () => {
    try {
      const data = await life.listSupplies();
      setItems(data.items || []);
    } catch {
      setItems([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const addItem = async () => {
    if (!name.trim()) return;
    await life.addSupply({
      name: name.trim(),
      category,
      unit,
      stock: Number(stock) || 0,
      minStock: Number(minStock) || 0,
      price: Number(price) || 0,
      location,
    });
    setName('');
    showToast('success', t('web_supplies_title', lang === 'id' ? 'Persediaan' : 'Supplies'), name);
    load();
  };

  const tx = async (id: string, kind: 'in' | 'out' | 'adjust') => {
    const qty = kind === 'adjust' ? Number(window.prompt(lang === 'id' ? 'Stok baru:' : 'New stock:', '0')) : 1;
    if (Number.isNaN(qty)) return;
    const res = await life.supplyTx(id, kind, qty);
    if (res?.result?.ok === false) {
      showToast('info', String(res.result.code || 'error'), '');
    }
    load();
  };

  const remove = async (id: string) => {
    await life.deleteSupply(id);
    load();
  };

  const low = items.filter((it) => it.minStock > 0 && it.stock <= it.minStock).length;
  const value = items.reduce((acc, it) => acc + it.stock * it.price, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
        <Package className="w-8 h-8 text-amber-400" />
        <div>
          <h1 className="text-xl font-bold text-slate-100">{t('web_supplies_title', lang === 'id' ? 'Persediaan rumah' : 'Household supplies')}</h1>
          <p className="text-xs text-slate-400">{t('web_supplies_sub', lang === 'id' ? 'Stok barang harian, disimpan di SQLite lokal.' : 'Daily stock, stored in local SQLite.')}</p>
          <p className="text-[11px] text-slate-500 mt-1">
            {items.length} {lang === 'id' ? 'barang' : 'items'} · {low} {lang === 'id' ? 'menipis' : 'low'} · {lang === 'id' ? 'nilai' : 'value'} {value.toLocaleString()}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 p-4 bg-slate-900/70 border border-slate-800 rounded-2xl">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder={lang === 'id' ? 'Nama barang' : 'Item name'} className="bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm flex-1 min-w-[140px]" />
        <input value={category} onChange={(e) => setCategory(e.target.value)} placeholder={lang === 'id' ? 'Kategori' : 'Category'} className="bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm w-32" />
        <input value={unit} onChange={(e) => setUnit(e.target.value)} className="bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm w-16" />
        <input value={stock} onChange={(e) => setStock(e.target.value)} type="number" title="stock" className="bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm w-16" />
        <input value={minStock} onChange={(e) => setMinStock(e.target.value)} type="number" title="min" className="bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm w-16" />
        <input value={price} onChange={(e) => setPrice(e.target.value)} type="number" title="price" className="bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm w-20" />
        <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder={lang === 'id' ? 'Lokasi' : 'Location'} className="bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm w-28" />
        <button onClick={addItem} className="px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm font-bold flex items-center gap-1">
          <Plus className="w-4 h-4" /> {t('web_supplies_add', lang === 'id' ? 'Tambah' : 'Add')}
        </button>
      </div>

      <div className="space-y-2">
        {items.length === 0 && <p className="text-sm text-slate-500">{lang === 'id' ? 'Belum ada stok.' : 'No supplies yet.'}</p>}
        {items.map((it) => (
          <div key={it.id} className="flex items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/70 border border-slate-800">
            <div>
              <div className="font-semibold text-sm text-slate-100">{it.name}</div>
              <div className="text-[11px] text-slate-500">
                {it.category || '—'} · {it.stock} {it.unit}
                {it.location ? ` · ${it.location}` : ''}
                {it.minStock > 0 && it.stock <= it.minStock ? ` · ${lang === 'id' ? 'stok rendah' : 'low stock'}` : ''}
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button onClick={() => tx(it.id, 'in')} className="p-2 rounded-lg bg-emerald-500/20 text-emerald-300" title="+1"><Plus className="w-4 h-4" /></button>
              <button onClick={() => tx(it.id, 'out')} className="p-2 rounded-lg bg-amber-500/20 text-amber-300" title="-1"><Minus className="w-4 h-4" /></button>
              <button onClick={() => tx(it.id, 'adjust')} className="p-2 rounded-lg bg-sky-500/20 text-sky-300" title={lang === 'id' ? 'Set stok' : 'Set stock'}><Equal className="w-4 h-4" /></button>
              <button
                type="button"
                onClick={async () => {
                  const loc = window.prompt(lang === 'id' ? 'Lokasi:' : 'Location:', it.location || '') ?? it.location;
                  await life.updateSupply(it.id, { location: loc, name: it.name, minStock: it.minStock, price: it.price });
                  load();
                }}
                className="px-2 py-1 rounded-lg bg-slate-800 text-[10px] font-bold text-slate-300"
              >
                {lang === 'id' ? 'Edit' : 'Edit'}
              </button>
              <button onClick={() => remove(it.id)} className="p-2 rounded-lg bg-rose-500/10 text-rose-400"><Trash2 className="w-4 h-4" /></button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
