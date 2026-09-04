import React, { useState, useMemo } from 'react';
import { useGame } from '../../context/GameContext';
import { Wallet, Plus, Trash2, TrendingUp, TrendingDown, CreditCard, DollarSign, CheckCircle, Activity, PieChart, Package, Search, FolderOpen, Pencil } from 'lucide-react';
import { DualLineChart, DonutChart } from '../charts';
import { t } from '../../i18n';
import { formatMoney as fmtMoney, currencySymbol } from '../../utils/currency';
import { MoneyInput } from '../MoneyInput';
// TaskFolderBar dihapus dari Economy (bukan elemen PyQt EconomyPage — lihat komentar di atas).
import { life } from '../../api/life';
import { fmtYmd, addDays } from '../../utils/serverTime';

export const EconomyView: React.FC<{ onNavigate?: (tab: any) => void }> = ({ onNavigate }) => {
  const {
    transactions, addTransaction, deleteTransaction, debts, addDebt, payDebtInstallment, deleteDebt,
    savings, addSaving, addToSaving, withdrawFromSaving, deleteSaving,
    investments, addInvestment, withdrawInvestment,
    subscriptions, addSubscription, renewSubscription, deleteSubscription,
    debtNotes, addDebtNote, settleDebtNote, deleteDebtNote,
    user, today, nowDate,
  } = useGame();
  const currency = user.currency || 'IDR';

  const [activeTab, setActiveTab] = useState<'transactions' | 'debts' | 'savings' | 'invest' | 'subs' | 'notes'>('transactions');
  const [svName, setSvName] = useState('');
  const [svTarget, setSvTarget] = useState(1000000);
  // Invest (parity AddInvestmentDialog PyQt: name + icon + amount + notes)
  const [invName, setInvName] = useState('');
  const [invAmt, setInvAmt] = useState(50000);
  const [invIcon, setInvIcon] = useState('📈');
  const [invNotes, setInvNotes] = useState('');
  const [isInvestModalOpen, setIsInvestModalOpen] = useState(false);
  // Collect return (parity _collect_return: input jumlah return manual)
  const [returnModal, setReturnModal] = useState<{ open: boolean; id: string }>({ open: false, id: '' });
  const [returnAmt, setReturnAmt] = useState(10000);
  // Subs (parity AddSubscriptionDialog PyQt: name + icon + amount + due + period + autorenew + notes)
  const [subName, setSubName] = useState('');
  const [subAmt, setSubAmt] = useState(10000);
  const [subDue, setSubDue] = useState(today);
  const [subIcon, setSubIcon] = useState('📅');
  const [subPeriod, setSubPeriod] = useState<'monthly' | 'yearly' | 'one-time'>('monthly');
  const [subNotes, setSubNotes] = useState('');
  const [subRecurring, setSubRecurring] = useState(true);
  const [isSubModalOpen, setIsSubModalOpen] = useState(false);
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
  // Nominal bebas per tabungan (parity AddToSavingDialog / withdraw PyQt).
  const [savingInput, setSavingInput] = useState<Record<string, number>>({});
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | 'income' | 'expense'>('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [trendDays, setTrendDays] = useState<7 | 30 | 90>(30);
  // [P25-fix] selectedFolder dihapus — TaskFolderBar (folder strip) tidak ada di PyQt EconomyPage.

  // Daftar kategori unik dari transaksi (parity PyQt economy category_combo / sub-tab).
  const uniqueCategories = useMemo(
    () => [...new Set(transactions.map((t: any) => (t.category || '').trim()).filter(Boolean))].sort(),
    [transactions],
  );

  const filteredTx = transactions.filter((tx) => {
    if (typeFilter !== 'all' && tx.type !== typeFilter) return false;
    // [P25-fix] filter folder dihapus (tidak ada di PyQt EconomyPage)
    if (categoryFilter !== 'all' && (tx.category || '').trim() !== categoryFilter) return false;
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
      showToast('info', t('msg_name_empty', 'Name cannot be empty!'), '');
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
            <span>{t('economy_total_income_label', 'Total Income')}</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-black text-emerald-400 mt-2">
            {fmtMoney(totalIncome, currency)}
          </div>
        </div>

        <div className="p-4.5 rounded-2xl bg-gradient-to-r from-rose-950/40 via-slate-900 to-slate-900 border border-rose-500/30">
          <div className="flex items-center justify-between text-xs text-slate-400 font-bold uppercase">
            <span>{t('economy_total_expense_label', 'Total Expenses')}</span>
            <TrendingDown className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-xl font-black text-rose-400 mt-2">
            {fmtMoney(totalExpense, currency)}
          </div>
        </div>

        <div className="p-4.5 rounded-2xl bg-gradient-to-r from-blue-950/40 via-slate-900 to-slate-900 border border-blue-500/30">
          <div className="flex items-center justify-between text-xs text-slate-400 font-bold uppercase">
            <span>{t('economy_net_balance_label', 'Net Balance')}</span>
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
                  <h2 className="font-bold text-slate-100">{t('economy_trend_title', 'Financial Trend')}</h2>
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
                <p className="text-sm text-slate-500 py-10 text-center">{t('economy_trend_empty', 'No transactions in this period.')}</p>
              ) : (
                <>
                  <div className="grid grid-cols-3 gap-2 mb-3 text-center">
                    <div>
                      <div className="text-[10px] uppercase text-slate-400 font-bold">{t('economy_trend_income', 'Income')}</div>
                      <div className="text-emerald-400 text-sm font-black">{fmtMoney(periodIncome, currency)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase text-slate-400 font-bold">{t('economy_trend_expense', 'Expense')}</div>
                      <div className="text-rose-400 text-sm font-black">{fmtMoney(periodExpense, currency)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase text-slate-400 font-bold">{t('economy_trend_net', 'Net')}</div>
                      <div className={`text-sm font-black ${periodNet >= 0 ? 'text-blue-400' : 'text-rose-400'}`}>{fmtMoney(periodNet, currency)}</div>
                    </div>
                  </div>
                  <div className="overflow-x-auto">
                    <div className="min-w-[300px]">
                      <DualLineChart labels={labels} a={incomeSeries} b={expenseSeries} colorA="#34d399" colorB="#f43f5e" width={620} height={190} />
                      <div className="flex justify-center gap-5 mt-2 text-[11px] font-bold">
                        <span className="flex items-center gap-1.5 text-emerald-300"><span className="w-3 h-0.5 bg-emerald-400 rounded" />{t('economy_trend_income', 'Income')}</span>
                        <span className="flex items-center gap-1.5 text-rose-300"><span className="w-3 h-0.5 bg-rose-400 rounded" />{t('economy_trend_expense', 'Expense')}</span>
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
                <h2 className="font-bold text-slate-100">{t('economy_expense_split', 'Expense Breakdown')}</h2>
              </div>
              {donutData.length === 0 ? (
                <p className="text-sm text-slate-500 py-10 text-center">{t('economy_donut_empty', 'No expenses yet.')}</p>
              ) : (
                <div className="flex flex-col items-center gap-4">
                  <DonutChart data={donutData} size={150} strokeWidth={16} centerLabel={fmtMoney(periodExpense, currency)} centerSub={t('economy_donut_total', 'total')} />
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
            {t('economy_tab_transactions', 'Transactions')} ({transactions.length})
          </button>
          <button
            onClick={() => setActiveTab('debts')}
            className={`px-3.5 py-1.5 rounded-lg font-bold transition-all ${
              activeTab === 'debts' ? 'bg-emerald-500 text-slate-950 shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {t('economy_tab_debts', 'Debts')} ({debts.length})
          </button>
          <button onClick={() => setActiveTab('savings')} className={`px-3.5 py-1.5 rounded-lg font-bold ${activeTab === 'savings' ? 'bg-emerald-500 text-slate-950' : 'text-slate-400'}`}>{t('economy_tab_savings', 'Savings')}</button>
          <button onClick={() => setActiveTab('invest')} className={`px-3.5 py-1.5 rounded-lg font-bold ${activeTab === 'invest' ? 'bg-emerald-500 text-slate-950' : 'text-slate-400'}`}>{t('economy_tab_investments', 'Invest')}</button>
          <button onClick={() => setActiveTab('subs')} className={`px-3.5 py-1.5 rounded-lg font-bold ${activeTab === 'subs' ? 'bg-emerald-500 text-slate-950' : 'text-slate-400'}`}>{t('economy_tab_subs', 'Subs')}</button>
          <button onClick={() => setActiveTab('notes')} className={`px-3.5 py-1.5 rounded-lg font-bold ${activeTab === 'notes' ? 'bg-emerald-500 text-slate-950' : 'text-slate-400'}`}>{t('economy_tab_iou', 'IOU notes')}</button>
        </div>

        {activeTab === 'transactions' ? (
          <button
            id="btn-add-tx"
            onClick={() => setIsTxModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all shrink-0"
          >
            <Plus className="w-4 h-4" /> {t('economy_new_transaction', 'New Transaction')}
          </button>
        ) : activeTab === 'debts' ? (
          <button
            id="btn-add-debt"
            onClick={() => setIsDebtModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all shrink-0"
          >
            <Plus className="w-4 h-4" /> {t('economy_new_debt', 'New Debt')}
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
                placeholder={t('economy_search', 'Search transactions…')}
                className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs"
              />
            </div>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value as any)} className="px-3 py-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs">
              <option value="all">{t('economy_filter_all', 'All')}</option>
              <option value="income">{t('economy_filter_income', 'Income')}</option>
              <option value="expense">{t('economy_filter_expense', 'Expense')}</option>
            </select>
            {/* Kategori filter (parity PyQt economy category_combo) */}
            <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="px-3 py-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs">
              <option value="all">{t('economy_all_categories', 'All Categories')}</option>
              {uniqueCategories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <button onClick={() => onNavigate?.('supplies')} className="px-3 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-300 flex items-center gap-1.5">
              <Package className="w-3.5 h-3.5" /> {t('economy_open_supplies', 'Open Supplies')}
            </button>
          </div>
          {/* P25-fix: PyQt EconomyPage TIDAK punya folder-chip strip (TaskFolderBar) di
              daftar — hanya folder_btn (add) + kategori + tipe + cari. Strip folder
              adalah pola TaskPage (habits/dailies/quests) dan membuat folder habit
              bocor muncul di Economy. Dihapus agar 1:1 PyQt. */}
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
                    {/* Parity _make_card PyQt: judul = nama transaksi (bukan kategori). */}
                    <div className="font-bold text-xs text-slate-100 truncate">{tx.name || tx.category}</div>
                    <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
                      <span>{tx.date}</span>
                      {tx.name && tx.category && tx.category !== tx.name && (
                        <span className="text-slate-500 truncate max-w-[120px]">{tx.category}</span>
                      )}
                      {tx.notes && <span className="truncate max-w-[140px] italic">· {tx.notes}</span>}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <div className={`font-black text-xs ${tx.type === 'income' ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {tx.type === 'income' ? '+' : '-'}{fmtMoney(tx.amount, currency)}
                  </div>
                  {/* [P25-fix] folder pill per-item dihapus (tidak ada di PyQt EconomyPage list) */}
                  <button
                    onClick={() => openEditTx(tx)}
                    className="p-1 rounded text-slate-400 hover:text-emerald-300 hover:bg-emerald-500/10 transition-colors"
                    title={t('economy_edit_transaction_tooltip', 'Edit transaction')}
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
              <p className="text-sm font-semibold">{t('economy_empty_transactions', 'No transactions recorded.')}</p>
            </div>
          )}
        </div>
      )}

      {/* DEBTS / RECEIVABLES VIEW */}
      {activeTab === 'debts' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs">
              <span className="text-slate-400 font-bold uppercase">{t('economy_debt_total_payable', 'Total Payable (I Owe)')}</span>
              <div className="text-base font-black text-rose-400 mt-1">{fmtMoney(totalPayableRemaining, currency)}</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs">
              <span className="text-slate-400 font-bold uppercase">{t('economy_debt_total_receivable', 'Total Receivable (Owed to Me)')}</span>
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
                        {debt.type === 'payable' ? t('economy_debt_type_payable', 'Payable') : t('economy_debt_type_receivable', 'Receivable')}
                      </span>
                      {debt.isPaid && (
                        <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 text-emerald-400 flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" /> {t('economy_debt_paid', 'Paid Off')}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400 flex items-center gap-3">
                      <span>{t('economy_due_label', 'Due')}: {debt.dueDate}</span>
                      <span>{t('economy_total_label', 'Total')}: {fmtMoney(debt.totalAmount, currency)}</span>
                    </div>
                    {debt.notes && <p className="text-xs text-slate-400">{debt.notes}</p>}
                  </div>

                  {/* Payment Progress & Action */}
                  <div className="flex items-center gap-3 shrink-0">
                    <div className="text-right">
                      <div className="text-xs text-slate-400 font-medium">{t('economy_remaining_label', 'Remaining')}</div>
                      <div className="text-sm font-extrabold text-amber-400">
                        {fmtMoney(debt.remainingAmount, currency)}
                      </div>
                    </div>

                    {!debt.isPaid && (
                      <div className="flex items-center gap-1.5">
                        <MoneyInput
                          value={currentInput}
                          onValueChange={(n) => setPayAmountInput({ ...payAmountInput, [debt.id]: n })}
                          currency={currency}
                          className="w-28"
                          inputClassName="py-1 text-xs rounded-lg"
                        />
                        <button
                          onClick={() => payDebtInstallment(debt.id, currentInput)}
                          className="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs"
                        >
                          {t('economy_pay_installment', 'Pay')}
                        </button>
                      </div>
                    )}

                    <button
                      onClick={() => openEditDebt(debt)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-300 hover:bg-emerald-500/10"
                      title={t('economy_edit_debt_tooltip', 'Edit debt')}
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
            <input value={svName} onChange={(e) => setSvName(e.target.value)} placeholder={t('economy_saving_name_ph', 'Saving name')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs flex-1" />
            <MoneyInput value={svTarget} onValueChange={(n) => setSvTarget(n)} currency={currency} className="w-36" inputClassName="py-2 text-xs rounded-xl" />
            <button onClick={() => { if (svName.trim()) { addSaving(svName.trim(), svTarget); setSvName(''); } }} className="px-3 py-2 rounded-xl bg-emerald-500 text-slate-950 font-bold text-xs">+</button>
          </div>
          {savings.map((s) => {
            const amt = savingInput[s.id] ?? 10000;
            return (
              <div key={s.id} className="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-bold text-sm">{s.icon} {s.name}</div>
                  <div className="text-xs text-slate-400">{fmtMoney(s.currentAmount, currency)} / {fmtMoney(s.targetAmount, currency)}</div>
                </div>
                <div className="flex items-center gap-2">
                  <MoneyInput value={amt} onValueChange={(n) => setSavingInput({ ...savingInput, [s.id]: n })} currency={currency} className="w-28" inputClassName="py-1.5 text-xs rounded-lg" />
                  <button
                    onClick={() => { if (amt > 0) addToSaving(s.id, amt); }}
                    title={t('economy_saving_add_funds', 'Add Funds to Savings')}
                    className="px-2.5 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 text-xs font-bold hover:bg-emerald-500/30"
                  >
                    ＋
                  </button>
                  <button
                    onClick={() => { if (amt > 0) withdrawFromSaving(s.id, amt); }}
                    title={t('economy_saving_withdraw_btn', 'Withdraw')}
                    className="px-2.5 py-1.5 rounded-lg bg-amber-500/20 text-amber-300 text-xs font-bold hover:bg-amber-500/30"
                  >
                    −
                  </button>
                  <button onClick={() => deleteSaving(s.id)} className="text-rose-400"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
            );
          })}
        </div>
      )}
      {activeTab === 'invest' && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <button
              id="btn-add-invest"
              onClick={() => { setInvName(''); setInvAmt(50000); setInvIcon('📈'); setInvNotes(''); setIsInvestModalOpen(true); }}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-lg shadow-amber-500/20 transition-all shrink-0"
            >
              <Plus className="w-4 h-4" /> {t('economy_invest_add', 'Add Investment')}
            </button>
          </div>
          {investments.map((i) => (
            <div key={i.id} className="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="font-bold text-sm text-slate-100">{i.icon} {i.name}</div>
                <div className="text-sm font-extrabold text-amber-400 mt-0.5">{fmtMoney(i.amount, currency)}</div>
                {i.investedDate && (
                  <div className="text-[11px] text-slate-500">{t('economy_invest_date_label', 'Invested: {date}').replace('{date}', i.investedDate)}</div>
                )}
                {i.notes && <div className="text-xs text-slate-400 italic">📝 {i.notes}</div>}
              </div>
              <div className="flex gap-2">
                <button onClick={() => { setReturnAmt(10000); setReturnModal({ open: true, id: i.id }); }} className="px-2.5 py-1.5 rounded-lg bg-amber-500/20 text-amber-300 text-xs font-bold hover:bg-amber-500/30">{t('economy_invest_collect', 'Collect Return')}</button>
                <button onClick={() => withdrawInvestment(i.id)} className="px-2.5 py-1.5 rounded-lg bg-blue-500/20 text-blue-300 text-xs font-bold hover:bg-blue-500/30">{t('economy_withdraw_btn', 'Withdraw')}</button>
                <button onClick={() => life.deleteInvestment(i.id).then((r) => applyLive(r)).catch(() => undefined)} className="text-rose-400 p-1"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
          ))}
          {investments.length === 0 && (
            <div className="text-center py-12 text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800/80">
              <p className="text-sm font-semibold">{t('economy_invest_empty', 'No investments yet.')}</p>
            </div>
          )}
        </div>
      )}
      {activeTab === 'subs' && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <button
              id="btn-add-sub"
              onClick={() => { setEditingSub(null); setSubName(''); setSubAmt(10000); setSubIcon('📅'); setSubDue(today); setSubPeriod('monthly'); setSubNotes(''); setSubRecurring(true); setIsSubModalOpen(true); }}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all shrink-0"
            >
              <Plus className="w-4 h-4" /> {t('economy_sub_add', 'Add Subscription')}
            </button>
          </div>
          {subscriptions.map((s) => {
            const overdue = String(s.dueDate || '') < String(today || '');
            return (
              <div
                key={s.id}
                className={`p-4 rounded-2xl border flex flex-wrap items-center justify-between gap-3 ${overdue ? 'bg-slate-900 border-rose-600/60 border-l-4' : 'bg-slate-900 border-slate-800'}`}
              >
                <div className="min-w-0">
                  <div className="font-bold text-sm text-slate-100">{s.icon} {s.name}</div>
                  <div className="text-xs font-bold text-emerald-400 mt-0.5">
                    {t('subscription_amount_period', '{amount} per {period}')
                      .replace('{amount}', fmtMoney(s.amount, currency))
                      .replace('{period}', t('sub_period_' + (s.period === 'one-time' ? 'onetime' : s.period), s.period))}
                  </div>
                  <div className={`text-[11px] mt-0.5 ${overdue ? 'text-rose-400 font-bold' : 'text-slate-500'}`}>
                    {t('economy_sub_due_format', 'Due: {date}').replace('{date}', s.dueDate)}
                  </div>
                  {s.notes && <div className="text-xs text-slate-400 italic">📝 {s.notes}</div>}
                </div>
                <div className="flex gap-2">
                  {overdue && (
                    <button onClick={() => renewSubscription(s.id)} className="px-2.5 py-1.5 rounded-lg bg-sky-500/20 text-sky-300 text-xs font-bold hover:bg-sky-500/30">{t('economy_sub_renew', 'Renew')}</button>
                  )}
                  <button onClick={() => { setEditingSub(s); setSubName(s.name); setSubAmt(Math.round(s.amount)); setSubIcon(s.icon || '📅'); setSubDue(s.dueDate || today); setSubPeriod((['monthly', 'yearly', 'one-time'].includes(s.period) ? s.period : 'monthly') as any); setSubNotes(s.notes || ''); setSubRecurring(s.isRecurring !== false); setIsSubModalOpen(true); }} className="px-2 py-1 rounded-lg bg-slate-800 text-slate-300 text-xs font-bold" title={t('economy_edit_tooltip', 'Edit')}><Pencil className="w-3.5 h-3.5" /></button>
                  <button onClick={() => deleteSubscription(s.id)} className="text-rose-400 p-1"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
            );
          })}
          {subscriptions.length === 0 && (
            <div className="text-center py-12 text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800/80">
              <p className="text-sm font-semibold">{t('economy_sub_empty', 'No subscriptions yet.')}</p>
            </div>
          )}
        </div>
      )}
      {activeTab === 'notes' && (
        <div className="space-y-3">
          <div className="flex gap-2">
            <input value={dnName} onChange={(e) => setDnName(e.target.value)} placeholder={t('economy_iou_person_ph', 'Person')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs flex-1" />
            <MoneyInput value={dnAmt} onValueChange={(n) => setDnAmt(n)} currency={currency} className="w-36" inputClassName="py-2 text-xs rounded-xl" />
            <button onClick={() => { if (dnName.trim()) { addDebtNote(dnName.trim(), dnAmt); setDnName(''); } }} className="px-3 py-2 rounded-xl bg-emerald-500 text-slate-950 font-bold text-xs">+</button>
          </div>
          {debtNotes.map((n) => (
            <div key={n.id} className="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div className="text-sm font-bold">{n.personName} · {fmtMoney(n.amount, currency)} · {n.status === 'paid' ? t('economy_status_paid', 'Paid') : t('economy_status_unpaid', 'Unpaid')}</div>
              <div className="flex gap-2">
                {n.status !== 'paid' && <button onClick={() => settleDebtNote(n.id)} className="px-2 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 text-xs font-bold">{t('economy_settle_btn', 'Settle')}</button>}
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
            <h3 className="text-lg font-black text-slate-100">{editingTx ? t('economy_transaction_title_edit', 'Edit Transaction') : t('economy_transaction_title_add', 'Log Transaction')}</h3>

            <form onSubmit={handleCreateTx} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('economy_transaction_name', 'Transaction name')}</label>
                <input
                  type="text"
                  value={txName}
                  onChange={(e) => setTxName(e.target.value)}
                  placeholder={t('economy_tx_name_ph', 'e.g. Lunch')}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('economy_date_label', 'Date')}</label>
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
                  - {t('economy_filter_expense', 'Expense')}
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
                  + {t('economy_filter_income', 'Income')}
                </button>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('economy_category_label', 'Category')}</label>
                <input
                  type="text"
                  value={txCategory}
                  onChange={(e) => setTxCategory(e.target.value)}
                  list="economy-cat-suggest"
                  placeholder={t('economy_category_ph', 'Example: Food, Salary, Transport, Entertainment...')}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
                <datalist id="economy-cat-suggest">
                  {[...new Set(transactions.map((t) => t.category).filter(Boolean))].map((c) => (
                    <option key={c} value={c} />
                  ))}
                </datalist>
                <p className="text-[10px] text-slate-500 mt-1">{t('economy_category_hint', '💡 Enter anything. It appears as a filter tab.')}</p>
              </div>

              {/* Folder target (parity economy_folder_label) */}
              <TxFolderSelect folderId={txFolderId} setFolderId={setTxFolderId} />

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('economy_amount_currency_label', 'Amount ({currency})').replace('{currency}', currency)}</label>
                <MoneyInput
                  value={txAmount}
                  onValueChange={(n) => setTxAmount(n)}
                  currency={currency}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('economy_notes_label', 'Notes')}</label>
                <input
                  type="text"
                  value={txNotes}
                  onChange={(e) => setTxNotes(e.target.value)}
                  placeholder={t('economy_tx_notes_ph', 'e.g. Lunch with the team')}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => { setIsTxModalOpen(false); setEditingTx(null); }}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold"
                >
                  {t('dialog_cancel', 'Cancel')}
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold"
                >
                  {t('economy_save_btn', 'Save')}
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
            <h3 className="text-lg font-black text-slate-100">{t('economy_debt_add_title', 'Add Debt')}</h3>

            <form onSubmit={handleCreateDebt} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('economy_debt_title_label', 'Title / Person')}</label>
                <input
                  type="text"
                  required
                  value={debtTitle}
                  onChange={(e) => setDebtTitle(e.target.value)}
                  placeholder={t('economy_debt_title_ph', 'e.g. Laptop loan / Receivable from Budi')}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="p-3 rounded-xl bg-slate-800/60 text-slate-300 text-xs flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{t('economy_debt_hint', 'Personal debt with installments (pay in parts, auto-logged as expense). For IOUs others owe you, use the IOU notes tab.')}</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{t('economy_debt_total_input', 'Total ({currency})').replace('{currency}', currency)}</label>
                  <MoneyInput
                    value={debtTotal}
                    onValueChange={(n) => setDebtTotal(n)}
                    currency={currency}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{t('economy_debt_due_label', 'Due Date')}</label>
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
                  {t('dialog_cancel', 'Cancel')}
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold"
                >
                  {t('economy_save_btn', 'Save')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Investment Modal (parity AddInvestmentDialog PyQt: name + icon + amount + notes) */}
      {isInvestModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-black text-slate-100">{t('investment_add_title', 'Add Investment')}</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('economy_invest_name', 'Investment Name')}</label>
                <input
                  type="text"
                  value={invName}
                  onChange={(e) => setInvName(e.target.value)}
                  placeholder={t('economy_invest_name_ph', 'Example: Mutual Fund, Stocks, Deposit')}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-amber-500"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-slate-300 font-semibold mb-2">{t('dialog_icon', 'Icon')}</label>
                <div className="flex flex-wrap gap-2">
                  {[
                    { label: t('invest_icon_stock', '📈 Stock'), icon: '📈' },
                    { label: t('invest_icon_deposit', '🏦 Deposit'), icon: '🏦' },
                    { label: t('invest_icon_gold', '💰 Gold'), icon: '💰' },
                    { label: t('invest_icon_property', '🏠 Property'), icon: '🏠' },
                    { label: t('invest_icon_crypto', '🚀 Crypto'), icon: '🚀' },
                  ].map((o) => (
                    <button
                      key={o.icon}
                      type="button"
                      onClick={() => setInvIcon(o.icon)}
                      className={`px-3 py-2 rounded-xl border text-xs font-bold transition-all ${invIcon === o.icon ? 'bg-amber-500/20 border-amber-500/50 text-amber-300' : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'}`}
                    >
                      {o.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('economy_invest_amount_label', 'Investment Amount ({symbol})').replace('{symbol}', currencySymbol(currency))}</label>
                <MoneyInput value={invAmt} onValueChange={(n) => setInvAmt(n)} currency={currency} className="w-full" />
              </div>
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('dialog_notes', 'Notes')}</label>
                <input
                  type="text"
                  value={invNotes}
                  onChange={(e) => setInvNotes(e.target.value)}
                  placeholder={t('dialog_notes_placeholder', 'Notes…')}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-amber-500"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-1">
                <button onClick={() => setIsInvestModalOpen(false)} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold">{t('dialog_cancel', 'Cancel')}</button>
                <button
                  onClick={() => {
                    if (!invName.trim()) { showToast('info', t('invest_name_empty', 'Investment name is required'), ''); return; }
                    if (invAmt <= 0) { showToast('info', t('invest_amount_positive', 'Investment amount must be greater than 0'), ''); return; }
                    addInvestment(invName.trim(), invAmt, invIcon, invNotes);
                    setIsInvestModalOpen(false);
                  }}
                  className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold"
                >
                  {t('economy_invest_btn', 'Invest')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Collect Return Modal (parity _collect_return PyQt: input jumlah return manual) */}
      {returnModal.open && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-sm w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-black text-slate-100">{t('economy_invest_return_title', 'Add Investment Return')}</h3>
            <div className="text-xs text-slate-400">{t('economy_invest_return_label', 'Amount to add (in {symbol}): ').replace('{symbol}', currencySymbol(currency))}</div>
            <MoneyInput value={returnAmt} onValueChange={(n) => setReturnAmt(n)} currency={currency} className="w-full" />
            <div className="flex items-center justify-end gap-2">
              <button onClick={() => setReturnModal({ open: false, id: '' })} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold text-xs">{t('dialog_cancel', 'Cancel')}</button>
              <button
                onClick={() => {
                  if (returnAmt <= 0) return;
                  life.addInvestmentReturn(returnModal.id, returnAmt).then((res) => applyLive(res)).catch(() => undefined);
                  setReturnModal({ open: false, id: '' });
                }}
                className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs"
              >
                {t('economy_invest_collect', 'Collect Return')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add / Edit Subscription Modal (parity AddSubscriptionDialog PyQt) */}
      {isSubModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-black text-slate-100">{editingSub ? t('subscription_edit_title', 'Edit Subscription') : t('subscription_add_title', 'Add Subscription')}</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('economy_sub_name_label', 'Service Name')}</label>
                <input
                  type="text"
                  value={subName}
                  onChange={(e) => setSubName(e.target.value)}
                  placeholder={t('sub_name_placeholder', 'Example: Netflix, Spotify, Claude AI')}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-slate-300 font-semibold mb-2">{t('dialog_icon', 'Icon')}</label>
                <div className="flex flex-wrap gap-2">
                  {[
                    { label: t('sub_icon_tv', '📺 TV'), icon: '📺' },
                    { label: t('sub_icon_music', '🎵 Music'), icon: '🎵' },
                    { label: t('sub_icon_ai', '🤖 AI'), icon: '🤖' },
                    { label: t('sub_icon_book', '📚 Book'), icon: '📚' },
                    { label: t('sub_icon_gym', '🏋️ Gym'), icon: '🏋️' },
                    { label: t('sub_icon_general', '📅 General'), icon: '📅' },
                  ].map((o) => (
                    <button
                      key={o.icon}
                      type="button"
                      onClick={() => setSubIcon(o.icon)}
                      className={`px-3 py-2 rounded-xl border text-xs font-bold transition-all ${subIcon === o.icon ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300' : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'}`}
                    >
                      {o.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('economy_sub_cost_label', 'Cost per period ({symbol})').replace('{symbol}', currencySymbol(currency))}</label>
                <MoneyInput value={subAmt} onValueChange={(n) => setSubAmt(n)} currency={currency} className="w-full" />
              </div>
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('economy_sub_due_label', 'Due Date')}</label>
                <input type="date" value={subDue} onChange={(e) => setSubDue(e.target.value)} className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500" />
              </div>
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('economy_sub_period_label', 'Period')}</label>
                <select
                  value={subPeriod}
                  onChange={(e) => setSubPeriod(e.target.value as any)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                >
                  <option value="monthly">{t('sub_period_monthly', 'Monthly')}</option>
                  <option value="yearly">{t('sub_period_yearly', 'Yearly')}</option>
                  <option value="one-time">{t('sub_period_onetime', 'One-time')}</option>
                </select>
              </div>
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={subRecurring && subPeriod !== 'one-time'}
                  disabled={subPeriod === 'one-time'}
                  onChange={(e) => setSubRecurring(e.target.checked)}
                  className="w-4 h-4 rounded text-emerald-500 bg-slate-900 border-slate-700"
                />
                <span className="text-slate-300">{t('economy_sub_autorenew', 'Auto-renew (recurring subscription)')}</span>
              </label>
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('dialog_notes', 'Notes')}</label>
                <input
                  type="text"
                  value={subNotes}
                  onChange={(e) => setSubNotes(e.target.value)}
                  placeholder={t('dialog_notes_placeholder', 'Notes…')}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-1">
                <button onClick={() => setIsSubModalOpen(false)} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold">{t('dialog_cancel', 'Cancel')}</button>
                <button
                  onClick={() => {
                    if (!subName.trim()) { showToast('info', t('msg_name_empty', 'Name cannot be empty!'), ''); return; }
                    if (subAmt <= 0) { showToast('info', t('economy_amount_gt_zero', 'Amount must be greater than 0'), ''); return; }
                    const recurring = subPeriod === 'one-time' ? false : subRecurring;
                    if (editingSub) {
                      life.updateSubscription(editingSub.id, { name: subName.trim(), icon: subIcon, amount: subAmt, dueDate: subDue, period: subPeriod, isRecurring: recurring, notes: subNotes })
                        .then((res) => { applyLive(res); showToast('success', t('subscription_updated', 'Subscription updated'), ''); })
                        .catch(() => undefined);
                    } else {
                      addSubscription(subName.trim(), subAmt, subDue, subPeriod, subNotes, subIcon, recurring);
                    }
                    setEditingSub(null);
                    setIsSubModalOpen(false);
                  }}
                  className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold"
                >
                  {t('dialog_save', 'Save')}
                </button>
              </div>
            </div>
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
      <label className="block text-slate-300 font-semibold mb-1 text-xs"><FolderOpen className="w-3.5 h-3.5 inline mr-1" />{t('economy_folder', 'Folder')}</label>
      <select
        value={folderId || ''}
        onChange={(e) => setFolderId(e.target.value || null)}
        className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500 text-xs"
      >
        <option value="">{t('economy_folder_root', '📂 Root')}</option>
        {folders.map((f: any) => (<option key={f.id} value={f.id}>{f.icon || '📁'} {f.name}</option>))}
      </select>
    </div>
  );
};

/** Pill kecil memindahkan transaksi antar-folder (parity drag-drop PyQt). */
// [P25-fix] TxFolderPill per-item DIHAPUS — PyQt EconomyPage list tidak punya folder
// dropdown per transaksi. Folder hanya dipilih via dialog tambah (TxFolderSelect,
// parity economy_folder_label) atau folder_btn header.
