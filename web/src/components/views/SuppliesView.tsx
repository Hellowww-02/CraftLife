import React, { useCallback, useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { life } from '../../api/life';
import { t } from '../../i18n';
import { Package, Plus, Trash2, Equal, Pencil, X, ArrowDownToLine, ArrowUpFromLine } from 'lucide-react';

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
  economyCategory: string;
};

type TxKind = 'in' | 'out' | 'adjust';

function fmtQty(v: number) {
  return Number.isInteger(v) ? String(v) : String(v);
}

export const SuppliesView: React.FC = () => {
  const { lang, showToast } = useGame();
  const [items, setItems] = useState<SupplyItem[]>([]);
  const [loadTick, setLoadTick] = useState(0);

  // Item add/edit modal
  const [itemModal, setItemModal] = useState<{ open: boolean; editing: SupplyItem | null }>({ open: false, editing: null });
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [unit, setUnit] = useState('pcs');
  const [stock, setStock] = useState('0');
  const [minStock, setMinStock] = useState('0');
  const [price, setPrice] = useState('0');
  const [location, setLocation] = useState('');
  const [notes, setNotes] = useState('');
  const [econCat, setEconCat] = useState('Supplies');

  // Transaction modal
  const [txModal, setTxModal] = useState<{ open: boolean; item: SupplyItem | null; initial: TxKind }>({ open: false, item: null, initial: 'in' });
  const [txKind, setTxKind] = useState<TxKind>('in');
  const [txQty, setTxQty] = useState('1');
  const [txNote, setTxNote] = useState('');
  const [txLogEconomy, setTxLogEconomy] = useState(false);
  const [txAmount, setTxAmount] = useState('0');
  const [txEconCat, setTxEconCat] = useState('Supplies');

  const load = useCallback(async () => {
    try {
      const data = await life.listSupplies();
      setItems((data.items || []).map((it: any) => ({
        ...it,
        economyCategory: it.economyCategory || it.economy_category || 'Supplies',
      })));
    } catch {
      setItems([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, loadTick]);

  const openAdd = () => {
    setName(''); setCategory(''); setUnit('pcs'); setStock('0'); setMinStock('0'); setPrice('0');
    setLocation(''); setNotes(''); setEconCat('Supplies');
    setItemModal({ open: true, editing: null });
  };

  const openEdit = (it: SupplyItem) => {
    setName(it.name); setCategory(it.category); setUnit(it.unit || 'pcs');
    setStock(fmtQty(it.stock)); setMinStock(fmtQty(it.minStock)); setPrice(fmtQty(it.price));
    setLocation(it.location); setNotes(it.notes); setEconCat(it.economyCategory || 'Supplies');
    setItemModal({ open: true, editing: it });
  };

  const saveItem = async () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    if (itemModal.editing) {
      await life.updateSupply(itemModal.editing.id, {
        name: trimmed, category, unit, minStock: Number(minStock) || 0,
        price: Number(price) || 0, location, notes, economy_category: econCat,
      });
    } else {
      await life.addSupply({
        name: trimmed, category, unit, stock: Number(stock) || 0,
        minStock: Number(minStock) || 0, price: Number(price) || 0,
        location, notes, economy_category: econCat,
      });
    }
    setItemModal({ open: false, editing: null });
    setLoadTick((v) => v + 1);
  };

  const openTx = (it: SupplyItem, kind: TxKind) => {
    setTxKind(kind === 'adjust' ? 'adjust' : kind === 'out' ? 'out' : 'in');
    setTxQty(kind === 'adjust' ? fmtQty(it.stock) : '1');
    setTxNote(''); setTxLogEconomy(kind === 'in'); setTxAmount(fmtQty(it.price)); setTxEconCat(it.economyCategory || 'Supplies');
    setTxModal({ open: true, item: it, initial: kind });
  };

  const submitTx = async () => {
    if (!txModal.item) return;
    const qty = Number(txQty);
    if (Number.isNaN(qty)) return;
    if (txKind !== 'adjust' && qty <= 0) return;
    const res = await life.supplyTx(txModal.item.id, {
      kind: txKind,
      qty,
      note: txNote,
      logEconomy: txLogEconomy,
      economyAmount: Number(txAmount) || 0,
      economyCategory: txEconCat || 'Supplies',
    });
    if (res?.result?.ok === false) {
      showToast('info', String(res.result.code || 'error'), '');
    } else if (txLogEconomy && (Number(txAmount) || 0) > 0) {
      showToast('success', t('web_supplies_title', lang === 'id' ? 'Persediaan' : 'Supplies'), lang === 'id' ? 'Dicatat ke ekonomi' : 'Logged to economy');
    }
    setTxModal({ open: false, item: null, initial: 'in' });
    setLoadTick((v) => v + 1);
  };

  const remove = async (id: string) => {
    await life.deleteSupply(id);
    setLoadTick((v) => v + 1);
  };

  const low = items.filter((it) => it.minStock > 0 && it.stock <= it.minStock).length;
  const value = items.reduce((acc, it) => acc + it.stock * it.price, 0);

  const fieldCls = 'bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3 bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
        <div className="flex items-center gap-3">
          <Package className="w-8 h-8 text-amber-400" />
          <div>
            <h1 className="text-xl font-bold text-slate-100">{t('web_supplies_title', lang === 'id' ? 'Persediaan rumah' : 'Household supplies')}</h1>
            <p className="text-xs text-slate-400">{t('web_supplies_sub', lang === 'id' ? 'Stok barang harian, disimpan di SQLite lokal.' : 'Daily stock, stored in local SQLite.')}</p>
            <p className="text-[11px] text-slate-500 mt-1">
              {items.length} {lang === 'id' ? 'barang' : 'items'} · {low} {lang === 'id' ? 'menipis' : 'low'} · {lang === 'id' ? 'nilai' : 'value'} {value.toLocaleString()}
            </p>
          </div>
        </div>
        <button onClick={openAdd} className="px-4 py-2 rounded-xl bg-emerald-600 text-white text-sm font-bold flex items-center gap-1 shrink-0">
          <Plus className="w-4 h-4" /> {t('web_supplies_add', lang === 'id' ? 'Tambah' : 'Add')}
        </button>
      </div>

      <div className="space-y-2">
        {items.length === 0 && <p className="text-sm text-slate-500">{lang === 'id' ? 'Belum ada stok.' : 'No supplies yet.'}</p>}
        {items.map((it) => (
          <div key={it.id} className="flex items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/70 border border-slate-800">
            <div className="min-w-0">
              <div className="font-semibold text-sm text-slate-100 truncate">{it.name}</div>
              <div className="text-[11px] text-slate-500">
                {it.category || '—'} · {it.stock} {it.unit}
                {it.location ? ` · ${it.location}` : ''}
                {it.minStock > 0 && it.stock <= it.minStock ? ` · ${lang === 'id' ? 'stok rendah' : 'low stock'}` : ''}
              </div>
              {it.notes && <div className="text-[10px] text-slate-600 truncate">{it.notes}</div>}
            </div>
            <div className="flex items-center gap-1">
              <button onClick={() => openTx(it, 'in')} className="p-2 rounded-lg bg-emerald-500/20 text-emerald-300" title={lang === 'id' ? 'Stok masuk' : 'Stock in'}><ArrowDownToLine className="w-4 h-4" /></button>
              <button onClick={() => openTx(it, 'out')} className="p-2 rounded-lg bg-amber-500/20 text-amber-300" title={lang === 'id' ? 'Stok keluar' : 'Stock out'}><ArrowUpFromLine className="w-4 h-4" /></button>
              <button onClick={() => openTx(it, 'adjust')} className="p-2 rounded-lg bg-sky-500/20 text-sky-300" title={lang === 'id' ? 'Set stok' : 'Set stock'}><Equal className="w-4 h-4" /></button>
              <button onClick={() => openEdit(it)} className="p-2 rounded-lg bg-slate-800 text-slate-300" title={lang === 'id' ? 'Edit' : 'Edit'}><Pencil className="w-4 h-4" /></button>
              <button onClick={() => remove(it.id)} className="p-2 rounded-lg bg-rose-500/10 text-rose-400"><Trash2 className="w-4 h-4" /></button>
            </div>
          </div>
        ))}
      </div>

      {/* Item add / edit modal */}
      {itemModal.open && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-black text-slate-100">
                {t(itemModal.editing ? 'supplies_dlg_title_edit' : 'supplies_dlg_title_add', itemModal.editing ? (lang === 'id' ? 'Edit Barang' : 'Edit Item') : (lang === 'id' ? 'Tambah Barang' : 'Add Item'))}
              </h3>
              <button onClick={() => setItemModal({ open: false, editing: null })} className="text-slate-400 hover:text-slate-200"><X className="w-5 h-5" /></button>
            </div>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder={t('supplies_name_ph', lang === 'id' ? 'Nama barang…' : 'Item name…')} className={`${fieldCls} w-full`} />
            <div className="grid grid-cols-2 gap-2">
              <input value={category} onChange={(e) => setCategory(e.target.value)} placeholder={t('supplies_category_ph', lang === 'id' ? 'Kategori' : 'Category')} className={fieldCls} />
              <input value={unit} onChange={(e) => setUnit(e.target.value)} placeholder={t('supplies_unit_ph', lang === 'id' ? 'satuan' : 'unit')} className={fieldCls} />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-[10px] text-slate-400 font-semibold">{t('supplies_stock_lbl', lang === 'id' ? 'Stok' : 'Stock')}</label>
                <input value={stock} onChange={(e) => setStock(e.target.value)} type="number" disabled={!!itemModal.editing} className={`${fieldCls} w-full disabled:opacity-60`} />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 font-semibold">{t('supplies_min_lbl', lang === 'id' ? 'Stok min.' : 'Min. stock')}</label>
                <input value={minStock} onChange={(e) => setMinStock(e.target.value)} type="number" className={`${fieldCls} w-full`} />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 font-semibold">{t('supplies_price_lbl', lang === 'id' ? 'Harga' : 'Price')}</label>
                <input value={price} onChange={(e) => setPrice(e.target.value)} type="number" className={`${fieldCls} w-full`} />
              </div>
            </div>
            <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder={t('supplies_location_ph', lang === 'id' ? 'Lokasi…' : 'Location…')} className={`${fieldCls} w-full`} />
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder={t('supplies_notes_ph', lang === 'id' ? 'Catatan…' : 'Notes…')} rows={2} className={`${fieldCls} w-full resize-none`} />
            <div>
              <label className="text-[10px] text-slate-400 font-semibold">{t('supplies_economy_lbl', lang === 'id' ? 'Kategori Ekonomi' : 'Economy category')}</label>
              <input value={econCat} onChange={(e) => setEconCat(e.target.value)} className={`${fieldCls} w-full`} />
            </div>
            <div className="flex items-center justify-end gap-2 pt-1">
              <button onClick={() => setItemModal({ open: false, editing: null })} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold text-xs">{t('btn_cancel', lang === 'id' ? 'Batal' : 'Cancel')}</button>
              <button onClick={saveItem} disabled={!name.trim()} className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-slate-950 font-bold text-xs">{t('btn_save', lang === 'id' ? '💾 Simpan' : '💾 Save')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Transaction modal */}
      {txModal.open && txModal.item && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-black text-slate-100">
                {t('supplies_tx_title', lang === 'id' ? 'Transaksi Stok' : 'Stock Transaction')} — {txModal.item.name}
              </h3>
              <button onClick={() => setTxModal({ open: false, item: null, initial: 'in' })} className="text-slate-400 hover:text-slate-200"><X className="w-5 h-5" /></button>
            </div>
            <p className="text-xs text-slate-400">
              {lang === 'id' ? 'Stok sekarang:' : 'Current stock:'} {fmtQty(txModal.item.stock)} {txModal.item.unit}
            </p>
            <div className="grid grid-cols-3 gap-2">
              {(['in', 'out', 'adjust'] as TxKind[]).map((k) => (
                <button key={k} onClick={() => setTxKind(k)}
                  className={`py-2 px-2 rounded-xl text-xs font-bold border transition-colors flex items-center justify-center gap-1 ${
                    txKind === k ? 'bg-sky-500/20 text-sky-300 border-sky-500/50' : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}>
                  {k === 'in' ? <ArrowDownToLine className="w-3.5 h-3.5" /> : k === 'out' ? <ArrowUpFromLine className="w-3.5 h-3.5" /> : <Equal className="w-3.5 h-3.5" />}
                  {t(k === 'in' ? 'supplies_tx_in' : k === 'out' ? 'supplies_tx_out' : 'supplies_tx_adjust', k === 'in' ? (lang === 'id' ? 'Tambah' : 'In') : k === 'out' ? (lang === 'id' ? 'Kurangi' : 'Out') : (lang === 'id' ? 'Set' : 'Adjust'))}
                </button>
              ))}
            </div>
            <div>
              <label className="text-[10px] text-slate-400 font-semibold">{t('supplies_qty_lbl', lang === 'id' ? 'Jumlah' : 'Quantity')}</label>
              <input value={txQty} onChange={(e) => setTxQty(e.target.value)} type="number" className={`${fieldCls} w-full`} />
            </div>
            <input value={txNote} onChange={(e) => setTxNote(e.target.value)} placeholder={t('supplies_note_ph', lang === 'id' ? 'Catatan…' : 'Note…')} className={`${fieldCls} w-full`} />
            <label className="flex items-center gap-2 text-xs text-slate-300 font-semibold">
              <input type="checkbox" checked={txLogEconomy} onChange={(e) => setTxLogEconomy(e.target.checked)} className="accent-emerald-500" />
              {t('supplies_restock_expense', lang === 'id' ? 'Catat sebagai pengeluaran ekonomi' : 'Log as economy expense')}
            </label>
            {txLogEconomy && (
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-slate-400 font-semibold">{t('supplies_economy_amount', lang === 'id' ? 'Nominal ekonomi' : 'Economy amount')}</label>
                  <input value={txAmount} onChange={(e) => setTxAmount(e.target.value)} type="number" className={`${fieldCls} w-full`} />
                </div>
                <div>
                  <label className="text-[10px] text-slate-400 font-semibold">{t('supplies_economy_category_ph', lang === 'id' ? 'Kategori ekonomi' : 'Economy category')}</label>
                  <input value={txEconCat} onChange={(e) => setTxEconCat(e.target.value)} className={`${fieldCls} w-full`} />
                </div>
              </div>
            )}
            <div className="flex items-center justify-end gap-2 pt-1">
              <button onClick={() => setTxModal({ open: false, item: null, initial: 'in' })} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold text-xs">{t('btn_cancel', lang === 'id' ? 'Batal' : 'Cancel')}</button>
              <button onClick={submitTx} className="px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold text-xs">{t('btn_save', lang === 'id' ? '💾 Simpan' : '💾 Save')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
