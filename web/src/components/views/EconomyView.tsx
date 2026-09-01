import React, { useState } from 'react';
import { useGame } from '../../context/GameContext';
import { Wallet, Plus, Trash2, TrendingUp, TrendingDown, CreditCard, DollarSign, CheckCircle, Activity, PieChart, Package, Search, FolderOpen, Pencil } from 'lucide-react';
import { DualLineChart, DonutChart } from '../charts';
import { t } from '../../i18n';
import { formatMoney as fmtMoney } from '../../utils/currency';
import { TaskFolderBar } from '../TaskFolderBar';
import { life } from '../../api/life';
import { fmtYmd, addDays } from '../../utils/serverTime';

export const EconomyView: React.FC<{ onNavigate?: (tab: any) => void }> = ({ onNavigate }) => {
  const {
    transactions, addTransaction, deleteTransaction, moveTransaction, debts, addDebt, payDebtInstallment, deleteDebt,
    savings, addSaving, addToSaving, withdrawFromSaving, deleteSaving,
    investments, addInvestment, collectInvestmentReturn, withdrawInvestment,
    subscriptions, addSubscription, renewSubscription, deleteSubscription,
    debtNotes, addDebtNote, settleDebtNote, deleteDebtNote,
    lang, user, today, nowDate,
  } = useGame();
  const currency = user.currency || 'IDR';

  const [activeTab, setActiveTab] = useState<'transactions' | 'debts' | 'savings' | 'invest' | 'subs' | 'notes'>('transactions');
  const [svName, setSvName] = useState('');
  const [svTarget, setSvTarget] = useState(1000000);
  const [invName, setInvName] = useState('');
  const [invAmt, setInvAmt] = useState(100000);
  const [subName, setSubName] = useState('');
  const [subAmt, setSubAmt] = useState(50000);
  const [subDue, setSubDue] = useState(today);
  const [dnName, setDnName] = useState('');
  const [dnAmt, setDnAmt] = useState(50000);
  const [isTxModalOpen, setIsTxModalOpen] = useState(false);
  const [isDebtModalOpen, setIsDebtModalOpen] = useState(false);

  // Transaction Form
  const [txType, setTxType] = useState<'income' | 'expense'>('expense');
  const [txCategory, setTxCategory] = useState('Food & Groceries');
  const [txAmount, setTxAmount] = useState<number>(50000);
  const [txNotes, setTxNotes] = useState('');
  const [txFolderId, setTxFolderId] = useState<string | null>(null);
  const [txName, setTxName] = useState('');
  const [txDate, setTxDate] = useState(today);
  const [editingTx, setEditingTx] = useState<any>(null);
  const { applyLive, showToast } = useGame();

  // Debt Form
  const [debtTitle, setDebtTitle] = useState('');
  // debt tab = hutang saja (payable); piutang → tab Catatan Hutang (parity PyQt).
  const [debtTotal, setDebtTotal] = useState<number>(200000);
  const [debtDueDate, setDebtDueDate] = useState(today);
  const [debtFormNotes, setDebtFormNotes] = useState('');

  // Installment input for pay
  const [payAmountInput, setPayAmountInput] = useState<Record<string, number>>({});
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | 'income' | 'expense'>('all');
  const [trendDays, setTrendDays] = useState<7 | 30 | 90>(30);
  const [selectedFolder, setSelectedFolder] = useState('all');

  const filteredTx = transactions.filter((tx) => {
    if (typeFilter !== 'all' && tx.type !== typeFilter) return false;
    if (selectedFolder !== 'all') {
      if ((tx.folderId || null) !== selectedFolder) return false;
    }
    const q = search.trim().toLowerCase();
    if (q) {
      const hay = `${tx.category || ''} ${tx.notes || ''} ${tx.name || ''}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  // (folder id list dipakai oleh komponen TaskFolderBar & per-tx pill)

  const totalIncome = transactions.filter((t) => t.type === 'income').reduce((acc, t) => acc + t.amount, 0);
  const totalExpense = transactions.filter((t) => t.type === 'expense').reduce((acc, t) => acc + t.amount, 0);
  const netBalance = totalIncome - totalExpense;

  const totalPayableRemaining = debts.filter((d) => d.type === 'payable' && !d.isPaid).reduce((acc, d) => acc + d.remainingAmount, 0);
  const totalReceivableRemaining = debts.filter((d) => d.type === 'receivable' && !d.isPaid).reduce((acc, d) => acc + d.remainingAmount, 0);

  const handleCreateTx = async (e: React.FormEvent) => {
    e.preventDefault();
    if (txAmount <= 0) return;
    // Parity AddEconomyDialog._save: nama transaksi wajib diisi.
    if (!txName.trim()) {
      showToast('info', t('msg_name_empty', lang === 'id' ? 'Nama belum diisi.' : 'Name is empty.'), '');
      return;
    }
    if (editingTx) {
      // Parity AddEconomyDialog mode edit → db.update_economy_item.
      const res = await life.updateEconomy(editingTx.id, {
        name: txName.trim() || undefined, type: txType, category: txCategory,
        amount: txAmount, notes: txNotes, date: txDate, folderId: txFolderId,
      }).catch(() => null);
      if (res) applyLive(res);
      setEditingTx(null);
    } else {
      addTransaction(txType, txCategory, txAmount, txNotes, txFolderId, txName.trim() || undefined, txDate);
    }
    setIsTxModalOpen(false);
    setTxNotes(''); setTxName(''); setTxDate(today); setTxFolderId(null);
  };
  const openEditTx = (tx: any) => {
    setEditingTx(tx);
    setTxType(tx.type); setTxCategory(tx.category || '');
    setTxAmount(Math.round(tx.amount)); setTxNotes(tx.notes || '');
    setTxFolderId(tx.folderId || null); setTxName(tx.name || tx.category || '');
    setTxDate(tx.date || today);
    setIsTxModalOpen(true);
  };

  const [editingDebt, setEditingDebt] = useState<any>(null);
  const [editingSub, setEditingSub] = useState<any>(null);
  const handleCreateDebt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!debtTitle.trim() || debtTotal <= 0) return;
    if (editingDebt) {
      // Parity EditDebtDialog: update debt.
      const res = await life.updateDebt(editingDebt.id, {
        title: debtTitle, totalAmount: debtTotal, dueDate: debtDueDate, notes: debtFormNotes,
      }).catch(() => null);
      if (res) applyLive(res);
      setEditingDebt(null);
    } else {
      // Parity PyQt EconomyPage: tab ini hanya untuk hutang (payable);
      // piutang dicatat di tab Catatan Hutang (debt_notes).
      addDebt(debtTitle, 'payable', debtTotal, debtDueDate, debtFormNotes);
    }
    setIsDebtModalOpen(false);
    setDebtTitle('');
    setDebtFormNotes('');
  };
  const openEditDebt = (debt: any) => {
    setEditingDebt(debt);
    setDebtTitle(debt.title || ''); setDebtTotal(debt.totalAmount || 0);
    setDebtDueDate(debt.dueDate || today);
    setDebtFormNotes(debt.notes || '');
    setIsDebtModalOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Financial Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4.5 rounded-2xl bg-gradient-to-r from-emerald-950/40 via-slate-900 to-slate-900 border border-emerald-500/30">
          <div className="flex items-center justify-between text-xs text-slate-400 font-bold uppercase">
            <span>{lang === 'id' ? 'Total Pemasukan' : 'Total Income'}</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-black text-emerald-400 mt-2">
            {fmtMoney(totalIncome, currency)}
          </div>
        </div>

        <div className="p-4.5 rounded-2xl bg-gradient-to-r from-rose-950/40 via-slate-900 to-slate-900 border border-rose-500/30">
          <div className="flex items-center justify-between text-xs text-slate-400 font-bold uppercase">
            <span>{lang === 'id' ? 'Total Pengeluaran' : 'Total Expenses'}</span>
            <TrendingDown className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-xl font-black text-rose-400 mt-2">
            {fmtMoney(totalExpense, currency)}
          </div>
        </div>

        <div className="p-4.5 rounded-2xl bg-gradient-to-r from-blue-950/40 via-slate-900 to-slate-900 border border-blue-500/30">
          <div className="flex items-center justify-between text-xs text-slate-400 font-bold uppercase">
            <span>{lang === 'id' ? 'Saldo Bersih' : 'Net Balance'}</span>
            <Wallet className="w-4 h-4 text-blue-400" />
          </div>
          <div className={`text-xl font-black mt-2 ${netBalance >= 0 ? 'text-blue-400' : 'text-rose-400'}`}>
            {fmtMoney(netBalance, currency)}
          </div>
        </div>
      </div>

      {/* Trend Widget (parity with PyQt EconomyTrendWidget) */}
      {(() => {
        const dayLabel = (d: Date) => `${d.getDate()}/${d.getMonth() + 1}`;
        const t0 = nowDate() ?? new Date();
        const start = addDays(t0, -(trendDays - 1));
        const buckets: { date: string; income: number; expense: number }[] = [];
        for (let i = 0; i < trendDays; i++) {
          const d = addDays(start, i);
          buckets.push({ date: fmtYmd(d), income: 0, expense: 0 });
        }
        const bucketByDate = new Map(buckets.map((b) => [b.date, b]));
        transactions.forEach((tx) => {
          const d = (tx.date || '').slice(0, 10);
          const bucket = bucketByDate.get(d);
          if (!bucket) return;
          if (tx.type === 'income') bucket.income += tx.amount;
          else bucket.expense += tx.amount;
        });
        const labelStep = trendDays <= 7 ? 1 : trendDays <= 30 ? 5 : 15;
        const labels = buckets.map((b, i) => (i % labelStep === 0 ? dayLabel(new Date(b.date)) : ''));
        const incomeSeries = buckets.map((b) => ({ label: b.date, value: Math.round(b.income) }));
        const expenseSeries = buckets.map((b) => ({ label: b.date, value: Math.round(b.expense) }));
        const periodIncome = incomeSeries.reduce((s, d) => s + d.value, 0);
        const periodExpense = expenseSeries.reduce((s, d) => s + d.value, 0);
        const periodNet = periodIncome - periodExpense;
        // expense split by category for the donut
        const byCat = new Map<string, number>();
        transactions.forEach((tx) => {
          if (tx.type !== 'expense') return;
          const d = (tx.date || '').slice(0, 10);
          if (!bucketByDate.has(d)) return;
          const cat = tx.category && tx.category.trim() ? tx.category.trim() : 'Other';
          byCat.set(cat, (byCat.get(cat) || 0) + tx.amount);
        });
        const catColors = ['#34d399', '#3b82f6', '#f43f5e', '#f59e0b', '#8b5cf6', '#10b981', '#06b6d4', '#64748b'];
        const donutData = [...byCat.entries()]
          .sort((x, y) => y[1] - x[1])
          .slice(0, 8)
          .map(([label, value], i) => ({ label, value: Math.round(value), color: catColors[i % catColors.length] }));
        const isEmpty = periodIncome === 0 && periodExpense === 0;
        const periodKey = trendDays === 7 ? 'economy_period_7d' : trendDays === 30 ? 'economy_period_30d' : 'economy_period_90d';
        return (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Trend chart */}
            <div className="lg:col-span-2 p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
              <div className="flex items-center justify-between gap-3 mb-4">
                <div className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-emerald-400" />
                  <h2 className="font-bold text-slate-100">{t('economy_trend_title', lang === 'id' ? 'Tren Keuangan' : 'Financial Trend')}</h2>
                </div>
                <div className="flex items-center gap-1 bg-slate-800 p-1 rounded-lg text-[11px] font-bold">
                  {([7, 30, 90] as const).map((d) => (
                    <button
                      key={d}
                      onClick={() => setTrendDays(d)}
                      className={`px-2.5 py-1 rounded-md transition-all ${trendDays === d ? 'bg-emerald-500 text-slate-950' : 'text-slate-400 hover:text-slate-200'}`}
                    >
                      {t(`economy_period_${d}d`, d === 7 ? '7 days' : d === 30 ? '30 days' : '90 days')}
                    </button>
                  ))}
                </div>
              </div>
              {isEmpty ? (
                <p className="text-sm text-slate-500 py-10 text-center">{t('economy_trend_empty', lang === 'id' ? 'Belum ada transaksi pada periode ini.' : 'No transactions in this period.')}</p>
              ) : (
                <>
                  <div className="grid grid-cols-3 gap-2 mb-3 text-center">
                    <div>
                      <div className="text-[10px] uppercase text-slate-400 font-bold">{t('economy_trend_income', lang === 'id' ? 'Pemasukan' : 'Income')}</div>
                      <div className="text-emerald-400 text-sm font-black">{fmtMoney(periodIncome, currency)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase text-slate-400 font-bold">{t('economy_trend_expense', lang === 'id' ? 'Pengeluaran' : 'Expense')}</div>
                      <div className="text-rose-400 text-sm font-black">{fmtMoney(periodExpense, currency)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase text-slate-400 font-bold">{t('economy_trend_net', lang === 'id' ? 'Selisih' : 'Net')}</div>
                      <div className={`text-sm font-black ${periodNet >= 0 ? 'text-blue-400' : 'text-rose-400'}`}>{fmtMoney(periodNet, currency)}</div>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <div className="min-w-[300px]">
                      <DualLineChart labels={labels} a={incomeSeries} b={expenseSeries} colorA="#34d399" colorB="#f43f5e" width={620} height={190} />
                      <div className="flex justify-center gap-5 mt-2 text-[11px] font-bold">
                        <span className="flex items-center gap-1.5 text-emerald-300"><span className="w-3 h-0.5 bg-emerald-400 rounded" />{t('economy_trend_income', lang === 'id' ? 'Pemasukan' : 'Income')}</span>
                        <span className="flex items-center gap-1.5 text-rose-300"><span className="w-3 h-0.5 bg-rose-400 rounded" />{t('economy_trend_expense', lang === 'id' ? 'Pengeluaran' : 'Expense')}</span>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
            {/* Expense breakdown donut */}
            <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
              <div className="flex items-center gap-2 mb-3">
                <PieChart className="w-5 h-5 text-rose-400" />
                <h2 className="font-bold text-slate-100">{t('economy_expense_split', lang === 'id' ? 'Rincian Pengeluaran' : 'Expense Breakdown')}</h2>
              </div>
              {donutData.length === 0 ? (
                <p className="text-sm text-slate-500 py-10 text-center">{lang === 'id' ? 'Belum ada pengeluaran.' : 'No expenses yet.'}</p>
              ) : (
                <div className="flex flex-col items-center gap-4">
                  <DonutChart data={donutData} size={150} strokeWidth={16} centerLabel={fmtMoney(periodExpense, currency)} centerSub={lang === 'id' ? 'total' : 'total'} />
                  <div className="space-y-1.5 w-full">
                    {donutData.map((d) => (
                      <div key={d.label} className="flex items-center justify-between text-[11px]">
                        <span className="flex items-center gap-1.5 text-slate-300"><span className="w-2.5 h-2.5 rounded-full" style={{ background: d.color }} />{d.label}</span>
                        <span className="text-slate-400 font-semibold">{fmtMoney(d.value, currency)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })()}

      {/* Tabs and Create Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1 rounded-xl text-xs">
          <button
            onClick={() => setActiveTab('transactions')}
            className={`px-3.5 py-1.5 rounded-lg font-bold transition-all ${
              activeTab === 'transactions' ? 'bg-emerald-500 text-slate-950 shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {lang === 'id' ? 'Arus Kas (Transaksi)' : 'Transactions'} ({transactions.length})
          </button>
          <button
            onClick={() => setActiveTab('debts')}
            className={`px-3.5 py-1.5 rounded-lg font-bold transition-all ${
              activeTab === 'debts' ? 'bg-emerald-500 text-slate-950 shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {lang === 'id' ? 'Hutang' : 'Debts'} ({debts.length})
          </button>
          <button onClick={() => setActiveTab('savings')} className={`px-3.5 py-1.5 rounded-lg font-bold ${activeTab === 'savings' ? 'bg-emerald-500 text-slate-950' : 'text-slate-400'}`}>{lang === 'id' ? 'Tabungan' : 'Savings'}</button>
          <button onClick={() => setActiveTab('invest')} className={`px-3.5 py-1.5 rounded-lg font-bold ${activeTab === 'invest' ? 'bg-emerald-500 text-slate-950' : 'text-slate-400'}`}>{lang === 'id' ? 'Investasi' : 'Invest'}</button>
          <button onClick={() => setActiveTab('subs')} className={`px-3.5 py-1.5 rounded-lg font-bold ${activeTab === 'subs' ? 'bg-emerald-500 text-slate-950' : 'text-slate-400'}`}>{lang === 'id' ? 'Langganan' : 'Subs'}</button>
          <button onClick={() => setActiveTab('notes')} className={`px-3.5 py-1.5 rounded-lg font-bold ${activeTab === 'notes' ? 'bg-emerald-500 text-slate-950' : 'text-slate-400'}`}>{lang === 'id' ? 'Catatan Hutang' : 'IOU notes'}</button>
        </div>

        {activeTab === 'transactions' ? (
          <button
            id="btn-add-tx"
            onClick={() => setIsTxModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all shrink-0"
          >
            <Plus className="w-4 h-4" /> {lang === 'id' ? 'Catat Transaksi' : 'New Transaction'}
          </button>
        ) : activeTab === 'debts' ? (
          <button
            id="btn-add-debt"
            onClick={() => setIsDebtModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all shrink-0"
          >
            <Plus className="w-4 h-4" /> {lang === 'id' ? 'Catat Hutang' : 'New Debt'}
          </button>
        ) : null}
      </div>

      {/* TRANSACTIONS VIEW */}
      {activeTab === 'transactions' && (
        <div className="space-y-3">
          {/* Parity EconomyPage: folder bar + search + filter */}
          <div className="flex flex-col lg:flex-row lg:items-center gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={t('economy_search', lang === 'id' ? 'Cari transaksi…' : 'Search transactions…')}
                className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs"
              />
            </div>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as any)} className="px-3 py-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs">
              <option value="all">{t('economy_filter_all', lang === 'id' ? 'Semua' : 'All')}</option>
              <option value="income">{t('economy_filter_income', lang === 'id' ? 'Pemasukan' : 'Income')}</option>
              <option value="expense">{t('economy_filter_expense', lang === 'id' ? 'Pengeluaran' : 'Expense')}</option>
            </select>
            <button onClick={() => onNavigate?.('supplies')} className="px-3 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-300 flex items-center gap-1.5">
              <Package className="w-3.5 h-3.5" /> {t('economy_open_supplies', lang === 'id' ? 'Buka Persediaan' : 'Open Supplies')}
            </button>
          </div>
          <TaskFolderBar
            mode="economy"
            selected={selectedFolder}
            onSelect={setSelectedFolder}
            accent="emerald"
            allLabel={lang === 'id' ? 'Semua' : 'All'}
            allCount={transactions.length}
            onDropInto={(fid) => undefined}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {filteredTx.map((tx) => (
              <div
                key={tx.id}
                className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex items-center justify-between gap-3 hover:border-slate-700 transition-all"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg shrink-0 ${
                      tx.type === 'income' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                    }`}
                  >
                    {tx.type === 'income' ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                  </div>
                  <div className="min-w-0">
                    <div className="font-bold text-xs text-slate-100 truncate">{tx.category}</div>
                    <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                      <span>{tx.date}</span>
                      {tx.notes && <span className="truncate max-w-[140px] italic">· {tx.notes}</span>}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <div className={`font-black text-xs ${tx.type === 'income' ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {tx.type === 'income' ? '+' : '-'}{fmtMoney(tx.amount, currency)}
                  </div>
                  {/* Pindah folder (parity drag-drop EconomyPage) */}
                  <TxFolderPill tx={tx} />
                  <button
                    onClick={() => openEditTx(tx)}
                    className="p-1 rounded text-slate-400 hover:text-emerald-300 hover:bg-emerald-500/10 transition-colors"
                    title={lang === 'id' ? 'Edit transaksi' : 'Edit transaction'}
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => deleteTransaction(tx.id)}
                    className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {filteredTx.length === 0 && (
            <div className="text-center py-12 text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800/80">
              <Wallet className="w-8 h-8 text-emerald-500/40 mx-auto mb-2" />
              <p className="text-sm font-semibold">{lang === 'id' ? 'Belum ada transaksi tercatat.' : 'No transactions recorded.'}</p>
            </div>
          )}
        </div>
      )}

      {/* DEBTS / RECEIVABLES VIEW */}
      {activeTab === 'debts' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs">
              <span className="text-slate-400 font-bold uppercase">{lang === 'id' ? 'Total Hutang Saya' : 'Total Payable (I Owe)'}</span>
              <div className="text-base font-black text-rose-400 mt-1">{fmtMoney(totalPayableRemaining, currency)}</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs">
              <span className="text-slate-400 font-bold uppercase">{lang === 'id' ? 'Total Piutang Saya' : 'Total Receivable (Owed to Me)'}</span>
              <div className="text-base font-black text-emerald-400 mt-1">{fmtMoney(totalReceivableRemaining, currency)}</div>
            </div>
          </div>

          <div className="space-y-3">
            {debts.map((debt) => {
              const currentInput = payAmountInput[debt.id] || Math.min(50000, debt.remainingAmount);

              return (
                <div
                  key={debt.id}
                  className={`p-4.5 rounded-2xl border flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all ${
                    debt.isPaid
                      ? 'bg-slate-900/40 border-slate-800/60 opacity-60'
                      : 'bg-slate-900/90 border-slate-800'
                  }`}
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h4 className="font-bold text-sm text-slate-100">{debt.title}</h4>
                      <span
                        className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
                          debt.type === 'payable'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        }`}
                      >
                        {debt.type === 'payable' ? (lang === 'id' ? 'Hutang Saya' : 'Payable') : (lang === 'id' ? 'Piutang' : 'Receivable')}
                      </span>
                      {debt.isPaid && (
                        <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 text-emerald-400 flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" /> {lang === 'id' ? 'Lunas' : 'Paid Off'}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400 flex items-center gap-3">
                      <span>Jatuh Tempo: {debt.dueDate}</span>
                      <span>Total: {fmtMoney(debt.totalAmount, currency)}</span>
                    </div>
                    {debt.notes && <p className="text-xs text-slate-400">{debt.notes}</p>}
                  </div>

                  {/* Payment Progress & Action */}
                  <div className="flex items-center gap-3 shrink-0">
                    <div className="text-right">
                      <div className="text-xs text-slate-400 font-medium">{lang === 'id' ? 'Sisa Tagihan' : 'Remaining'}</div>
                      <div className="text-sm font-extrabold text-amber-400">
                        {fmtMoney(debt.remainingAmount, currency)}
                      </div>
                    </div>

                    {!debt.isPaid && (
                      <div className="flex items-center gap-1.5">
                        <input
                          type="number"
                          step="10000"
                          value={currentInput}
                          onChange={(e) =>
                            setPayAmountInput({ ...payAmountInput, [debt.id]: Number(e.target.value) })
                          }
                          className="w-24 px-2 py-1 text-xs rounded-lg bg-slate-800 border border-slate-700 text-slate-100"
                        />
                        <button
                          onClick={() => payDebtInstallment(debt.id, currentInput)}
                          className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs"
                        >
                          {lang === 'id' ? 'Bayar / Cicil' : 'Pay'}
                        </button>
                      </div>
                    )}

                    <button
                      onClick={() => openEditDebt(debt)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-300 hover:bg-emerald-500/10"
                      title={lang === 'id' ? 'Edit hutang' : 'Edit debt'}
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => deleteDebt(debt.id)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {activeTab === 'savings' && (
        <div className="space-y-3">
          <div className="flex gap-2">
            <input value={svName} onChange={(e) => setSvName(e.target.value)} placeholder={lang === 'id' ? 'Nama tabungan' : 'Saving name'} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs flex-1" />
            <input type="number" value={svTarget} onChange={(e) => setSvTarget(Number(e.target.value))} className="w-32 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs" />
            <button onClick={() => { if (svName.trim()) { addSaving(svName.trim(), svTarget); setSvName(''); } }} className="px-3 py-2 rounded-xl bg-emerald-500 text-slate-950 font-bold text-xs">+</button>
          </div>
          {savings.map((s) => (
            <div key={s.id} className="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between gap-3">
              <div>
                <div className="font-bold text-sm">{s.icon} {s.name}</div>
                <div className="text-xs text-slate-400">{fmtMoney(s.currentAmount, currency)} / {fmtMoney(s.targetAmount, currency)}</div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => addToSaving(s.id, 50000)} className="px-2 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 text-xs font-bold">+50k</button>
                <button onClick={() => withdrawFromSaving(s.id, 50000)} className="px-2 py-1 rounded-lg bg-amber-500/20 text-amber-300 text-xs font-bold">-50k</button>
                <button onClick={() => deleteSaving(s.id)} className="text-rose-400"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
          ))}
        </div>
      )}
      {activeTab === 'invest' && (
        <div className="space-y-3">
          <div className="flex gap-2">
            <input value={invName} onChange={(e) => setInvName(e.target.value)} placeholder={lang === 'id' ? 'Nama investasi' : 'Investment'} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs flex-1" />
            <input type="number" value={invAmt} onChange={(e) => setInvAmt(Number(e.target.value))} className="w-32 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs" />
            <button onClick={() => { if (invName.trim()) { addInvestment(invName.trim(), invAmt); setInvName(''); } }} className="px-3 py-2 rounded-xl bg-emerald-500 text-slate-950 font-bold text-xs">+</button>
          </div>
          {investments.map((i) => (
            <div key={i.id} className="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div className="font-bold text-sm">{i.icon} {i.name} · {fmtMoney(i.amount, currency)}</div>
              <div className="flex gap-2">
                <button onClick={() => collectInvestmentReturn(i.id)} className="px-2 py-1 rounded-lg bg-amber-500/20 text-amber-300 text-xs font-bold">+5%</button>
                <button onClick={() => withdrawInvestment(i.id)} className="px-2 py-1 rounded-lg bg-blue-500/20 text-blue-300 text-xs font-bold">{lang === 'id' ? 'Tarik' : 'Withdraw'}</button>
              </div>
            </div>
          ))}
        </div>
      )}
      {activeTab === 'subs' && (
        <div className="space-y-3">
          <div className="flex gap-2 flex-wrap items-center">
            <input value={subName} onChange={(e) => setSubName(e.target.value)} placeholder={lang === 'id' ? 'Langganan' : 'Subscription'} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs flex-1 min-w-[8rem]" />
            <input type="number" value={subAmt} onChange={(e) => setSubAmt(Number(e.target.value))} className="w-28 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs" />
            <input type="date" value={subDue} onChange={(e) => setSubDue(e.target.value)} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs" />
            {editingSub ? (
              <>
                <button onClick={async () => {
                  if (!subName.trim()) return;
                  // Parity EditSubscription dialog PyQt.
                  const res = await life.updateSubscription(editingSub.id, { name: subName.trim(), amount: subAmt, dueDate: subDue }).catch(() => null);
                  if (res) applyLive(res);
                  setEditingSub(null); setSubName('');
                }} className="px-3 py-2 rounded-xl bg-amber-500 text-slate-950 font-bold text-xs">{lang === 'id' ? 'Simpan' : 'Save'}</button>
                <button onClick={() => { setEditingSub(null); setSubName(''); }} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs">{lang === 'id' ? 'Batal' : 'Cancel'}</button>
              </>
            ) : (
              <button onClick={() => { if (subName.trim()) { addSubscription(subName.trim(), subAmt, subDue); setSubName(''); } }} className="px-3 py-2 rounded-xl bg-emerald-500 text-slate-950 font-bold text-xs">+</button>
            )}
          </div>
          {subscriptions.map((s) => (
            <div key={s.id} className="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div className="text-sm font-bold">{s.icon} {s.name} · {fmtMoney(s.amount, currency)} · {s.dueDate}</div>
              <div className="flex gap-2">
                <button onClick={() => renewSubscription(s.id)} className="px-2 py-1 rounded-lg bg-sky-500/20 text-sky-300 text-xs font-bold">{lang === 'id' ? 'Perpanjang' : 'Renew'}</button>
                <button onClick={() => { setEditingSub(s); setSubName(s.name); setSubAmt(Math.round(s.amount)); setSubDue(s.dueDate || ''); }} className="px-2 py-1 rounded-lg bg-slate-800 text-slate-300 text-xs font-bold" title={lang === 'id' ? 'Edit' : 'Edit'}><Pencil className="w-3.5 h-3.5" /></button>
                <button onClick={() => deleteSubscription(s.id)} className="text-rose-400"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
          ))}
        </div>
      )}
      {activeTab === 'notes' && (
        <div className="space-y-3">
          <div className="flex gap-2">
            <input value={dnName} onChange={(e) => setDnName(e.target.value)} placeholder={lang === 'id' ? 'Nama orang' : 'Person'} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs flex-1" />
            <input type="number" value={dnAmt} onChange={(e) => setDnAmt(Number(e.target.value))} className="w-32 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs" />
            <button onClick={() => { if (dnName.trim()) { addDebtNote(dnName.trim(), dnAmt); setDnName(''); } }} className="px-3 py-2 rounded-xl bg-emerald-500 text-slate-950 font-bold text-xs">+</button>
          </div>
          {debtNotes.map((n) => (
            <div key={n.id} className="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div className="text-sm font-bold">{n.personName} · {fmtMoney(n.amount, currency)} · {n.status}</div>
              <div className="flex gap-2">
                {n.status !== 'paid' && <button onClick={() => settleDebtNote(n.id)} className="px-2 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 text-xs font-bold">{lang === 'id' ? 'Lunas' : 'Settle'}</button>}
                <button onClick={() => deleteDebtNote(n.id)} className="text-rose-400"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Transaction Modal */}
      {isTxModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-black text-slate-100">{editingTx ? (lang === 'id' ? 'Edit Transaksi' : 'Edit Transaction') : (lang === 'id' ? 'Catat Transaksi Keuangan' : 'Log Transaction')}</h3>

            <form onSubmit={handleCreateTx} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Nama transaksi' : 'Transaction name'}</label>
                <input
                  type="text"
                  value={txName}
                  onChange={(e) => setTxName(e.target.value)}
                  placeholder={lang === 'id' ? 'mis. Makan siang' : 'e.g. Lunch'}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Tanggal' : 'Date'}</label>
                <input
                  type="date"
                  value={txDate}
                  onChange={(e) => setTxDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setTxType('expense')}
                  className={`py-2 rounded-xl font-bold border transition-colors ${
                    txType === 'expense'
                      ? 'bg-rose-500/20 text-rose-300 border-rose-500/50'
                      : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}
                >
                  - {lang === 'id' ? 'Pengeluaran' : 'Expense'}
                </button>
                <button
                  type="button"
                  onClick={() => setTxType('income')}
                  className={`py-2 rounded-xl font-bold border transition-colors ${
                    txType === 'income'
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50'
                      : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}
                >
                  + {lang === 'id' ? 'Pemasukan' : 'Income'}
                </button>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Kategori Transaksi' : 'Category'}</label>
                <input
                  type="text"
                  value={txCategory}
                  onChange={(e) => setTxCategory(e.target.value)}
                  list="economy-cat-suggest"
                  placeholder={t('economy_category_ph', lang === 'id' ? 'Contoh: Makanan, Gaji, Transport, Hiburan...' : 'Example: Food, Salary, Transport, Entertainment...')}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
                <datalist id="economy-cat-suggest">
                  {[...new Set(transactions.map((t) => t.category).filter(Boolean))].map((c) => (
                    <option key={c} value={c} />
                  ))}
                </datalist>
                <p className="text-[10px] text-slate-500 mt-1">{t('economy_category_hint', lang === 'id' ? '💡 Bebas isi apapun. Nanti akan muncul sebagai tab filter.' : '💡 Enter anything. It appears as a filter tab.')}</p>
              </div>

              {/* Folder target (parity economy_folder_label) */}
              <TxFolderSelect folderId={txFolderId} setFolderId={setTxFolderId} />

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? `Nominal (${currency})` : `Amount (${currency})`}</label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  value={txAmount}
                  onChange={(e) => setTxAmount(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Catatan Tambahan' : 'Notes'}</label>
                <input
                  type="text"
                  value={txNotes}
                  onChange={(e) => setTxNotes(e.target.value)}
                  placeholder="e.g. Makan siang bersama tim"
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => { setIsTxModalOpen(false); setEditingTx(null); }}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold"
                >
                  {lang === 'id' ? 'Batal' : 'Cancel'}
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold"
                >
                  {lang === 'id' ? 'Simpan' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Debt Modal */}
      {isDebtModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-black text-slate-100">{lang === 'id' ? 'Tambah Hutang' : 'Add Debt'}</h3>

            <form onSubmit={handleCreateDebt} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Keterangan Hutang' : 'Title / Person'}</label>
                <input
                  type="text"
                  required
                  value={debtTitle}
                  onChange={(e) => setDebtTitle(e.target.value)}
                  placeholder="e.g. Pinjaman Laptop / Piutang ke Budi"
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="p-3 rounded-xl bg-slate-800/60 text-slate-300 text-xs flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-rose-400 shrink-0" />
                <span>
                  {lang === 'id'
                    ? 'Hutang pribadi dengan cicilan (bayar sebagian, auto-catat sebagai pengeluaran). Untuk piutang / orang meminjam ke kamu, pakai tab Catatan Hutang.'
                    : 'Personal debt with installments (pay in parts, auto-logged as expense). For IOUs others owe you, use the IOU notes tab.'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? `Total Jumlah (${currency})` : `Total (${currency})`}</label>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    value={debtTotal}
                    onChange={(e) => setDebtTotal(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Jatuh Tempo' : 'Due Date'}</label>
                  <input
                    type="date"
                    value={debtDueDate}
                    onChange={(e) => setDebtDueDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsDebtModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold"
                >
                  {lang === 'id' ? 'Batal' : 'Cancel'}
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold"
                >
                  {lang === 'id' ? 'Simpan' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

/** Select folder target di dialog tambah transaksi (parity Folder keuangan). */
const TxFolderSelect: React.FC<{ folderId: string | null; setFolderId: (v: string | null) => void }> = ({ folderId, setFolderId }) => {
  const { taskFolders } = useGame();
  const folders = taskFolders.filter((f: any) => f.mode === 'economy');
  if (folders.length === 0) return null;
  return (
    <div>
      <label className="block text-slate-300 font-semibold mb-1 text-xs"><FolderOpen className="w-3.5 h-3.5 inline mr-1" />Folder</label>
      <select
        value={folderId || ''}
        onChange={(e) => setFolderId(e.target.value || null)}
        className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500 text-xs"
      >
        <option value="">📂 Root</option>
        {folders.map((f: any) => (<option key={f.id} value={f.id}>{f.icon || '📁'} {f.name}</option>))}
      </select>
    </div>
  );
};

/** Pill kecil memindahkan transaksi antar-folder (parity drag-drop PyQt). */
const TxFolderPill: React.FC<{ tx: any }> = ({ tx }) => {
  const { taskFolders, moveTransaction } = useGame();
  const folders = taskFolders.filter((f: any) => f.mode === 'economy');
  if (folders.length === 0) return null;
  return (
    <select
      value={tx.folderId || ''}
      onChange={(e) => moveTransaction(tx.id, e.target.value || null)}
      className="px-1.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-[10px] text-slate-300"
      title={tx.folderId ? undefined : 'Root'}
    >
      <option value="">📂 Root</option>
      {folders.map((f: any) => (<option key={f.id} value={f.id}>{f.icon || '📁'} {f.name}</option>))}
    </select>
  );
};
