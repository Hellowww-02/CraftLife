import React, { useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { apiGet } from '../../api/client';
import { Wallet, Plus, Trash2, TrendingUp, TrendingDown, CreditCard, DollarSign, CheckCircle } from 'lucide-react';

let RATES: Record<string, number> = { IDR: 1, USD: 17800, EUR: 20700 };

function fmtMoney(amountIdr: number, currency: string) {
  const rate = RATES[currency] || 1;
  const v = currency === 'IDR' ? amountIdr : amountIdr / rate;
  const n = currency === 'IDR' ? Math.round(v).toLocaleString() : v.toFixed(2);
  return `${currency} ${n}`;
}

export const EconomyView: React.FC = () => {
  const {
    transactions, addTransaction, deleteTransaction, debts, addDebt, payDebtInstallment, deleteDebt,
    savings, addSaving, addToSaving, withdrawFromSaving, deleteSaving,
    investments, addInvestment, collectInvestmentReturn, withdrawInvestment,
    subscriptions, addSubscription, renewSubscription, deleteSubscription,
    debtNotes, addDebtNote, settleDebtNote, deleteDebtNote,
    lang, user,
  } = useGame();
  const currency = user.currency || 'IDR';
  useEffect(() => {
    apiGet<any>('/api/catalog/currency').then((d) => {
      if (d?.rates) RATES = d.rates;
    }).catch(() => undefined);
  }, []);

  const [activeTab, setActiveTab] = useState<'transactions' | 'debts' | 'savings' | 'invest' | 'subs' | 'notes'>('transactions');
  const [svName, setSvName] = useState('');
  const [svTarget, setSvTarget] = useState(1000000);
  const [invName, setInvName] = useState('');
  const [invAmt, setInvAmt] = useState(100000);
  const [subName, setSubName] = useState('');
  const [subAmt, setSubAmt] = useState(50000);
  const [subDue, setSubDue] = useState(new Date().toISOString().split('T')[0]);
  const [dnName, setDnName] = useState('');
  const [dnAmt, setDnAmt] = useState(50000);
  const [isTxModalOpen, setIsTxModalOpen] = useState(false);
  const [isDebtModalOpen, setIsDebtModalOpen] = useState(false);

  // Transaction Form
  const [txType, setTxType] = useState<'income' | 'expense'>('expense');
  const [txCategory, setTxCategory] = useState('Food & Groceries');
  const [txAmount, setTxAmount] = useState<number>(50000);
  const [txNotes, setTxNotes] = useState('');

  // Debt Form
  const [debtTitle, setDebtTitle] = useState('');
  const [debtType, setDebtType] = useState<'payable' | 'receivable'>('payable');
  const [debtTotal, setDebtTotal] = useState<number>(200000);
  const [debtDueDate, setDebtDueDate] = useState(new Date().toISOString().split('T')[0]);
  const [debtFormNotes, setDebtFormNotes] = useState('');

  // Installment input for pay
  const [payAmountInput, setPayAmountInput] = useState<Record<string, number>>({});
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | 'income' | 'expense'>('all');

  const totalIncome = transactions.filter((t) => t.type === 'income').reduce((acc, t) => acc + t.amount, 0);
  const totalExpense = transactions.filter((t) => t.type === 'expense').reduce((acc, t) => acc + t.amount, 0);
  const netBalance = totalIncome - totalExpense;

  const totalPayableRemaining = debts.filter((d) => d.type === 'payable' && !d.isPaid).reduce((acc, d) => acc + d.remainingAmount, 0);
  const totalReceivableRemaining = debts.filter((d) => d.type === 'receivable' && !d.isPaid).reduce((acc, d) => acc + d.remainingAmount, 0);

  const handleCreateTx = (e: React.FormEvent) => {
    e.preventDefault();
    if (txAmount <= 0) return;
    addTransaction(txType, txCategory, txAmount, txNotes);
    setIsTxModalOpen(false);
    setTxNotes('');
  };

  const handleCreateDebt = (e: React.FormEvent) => {
    e.preventDefault();
    if (!debtTitle.trim() || debtTotal <= 0) return;
    addDebt(debtTitle, debtType, debtTotal, debtDueDate, debtFormNotes);
    setIsDebtModalOpen(false);
    setDebtTitle('');
    setDebtFormNotes('');
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
            {lang === 'id' ? 'Hutang/Piutang' : 'Debts'} ({debts.length})
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
            <Plus className="w-4 h-4" /> {lang === 'id' ? 'Catat Hutang / Piutang' : 'New Debt / Receivable'}
          </button>
        ) : null}
      </div>

      {/* TRANSACTIONS VIEW */}
      {activeTab === 'transactions' && (
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {transactions.map((tx) => (
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

                <div className="flex items-center gap-3 shrink-0">
                  <div className={`font-black text-xs ${tx.type === 'income' ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {tx.type === 'income' ? '+' : '-'}{fmtMoney(tx.amount, currency)}
                  </div>
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

          {transactions.length === 0 && (
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
                      <span>Total: Rp {debt.totalAmount.toLocaleString()}</span>
                    </div>
                    {debt.notes && <p className="text-xs text-slate-400">{debt.notes}</p>}
                  </div>

                  {/* Payment Progress & Action */}
                  <div className="flex items-center gap-3 shrink-0">
                    <div className="text-right">
                      <div className="text-xs text-slate-400 font-medium">{lang === 'id' ? 'Sisa Tagihan' : 'Remaining'}</div>
                      <div className="text-sm font-extrabold text-amber-400">
                        Rp {debt.remainingAmount.toLocaleString()}
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
                <div className="text-xs text-slate-400">Rp {s.currentAmount.toLocaleString()} / {s.targetAmount.toLocaleString()}</div>
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
              <div className="font-bold text-sm">{i.icon} {i.name} · Rp {i.amount.toLocaleString()}</div>
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
          <div className="flex gap-2 flex-wrap">
            <input value={subName} onChange={(e) => setSubName(e.target.value)} placeholder={lang === 'id' ? 'Langganan' : 'Subscription'} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs flex-1 min-w-[8rem]" />
            <input type="number" value={subAmt} onChange={(e) => setSubAmt(Number(e.target.value))} className="w-28 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs" />
            <input type="date" value={subDue} onChange={(e) => setSubDue(e.target.value)} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs" />
            <button onClick={() => { if (subName.trim()) { addSubscription(subName.trim(), subAmt, subDue); setSubName(''); } }} className="px-3 py-2 rounded-xl bg-emerald-500 text-slate-950 font-bold text-xs">+</button>
          </div>
          {subscriptions.map((s) => (
            <div key={s.id} className="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div className="text-sm font-bold">{s.icon} {s.name} · Rp {s.amount.toLocaleString()} · {s.dueDate}</div>
              <div className="flex gap-2">
                <button onClick={() => renewSubscription(s.id)} className="px-2 py-1 rounded-lg bg-sky-500/20 text-sky-300 text-xs font-bold">{lang === 'id' ? 'Perpanjang' : 'Renew'}</button>
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
              <div className="text-sm font-bold">{n.personName} · Rp {n.amount.toLocaleString()} · {n.status}</div>
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
            <h3 className="text-lg font-black text-slate-100">{lang === 'id' ? 'Catat Transaksi Keuangan' : 'Log Transaction'}</h3>

            <form onSubmit={handleCreateTx} className="space-y-3 text-xs">
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
                <select
                  value={txCategory}
                  onChange={(e) => setTxCategory(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                >
                  <option value="Food & Groceries">Food & Groceries</option>
                  <option value="Transport & Gas">Transport & Gas</option>
                  <option value="Salary / Project">Salary / Project</option>
                  <option value="Entertainment & Hobbies">Entertainment & Hobbies</option>
                  <option value="Health & Fitness">Health & Fitness</option>
                  <option value="Investments & Savings">Investments & Savings</option>
                  <option value="Bills & Utilities">Bills & Utilities</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Nominal (Rupiah)' : 'Amount (IDR)'}</label>
                <input
                  type="number"
                  min="1000"
                  step="1000"
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
                  onClick={() => setIsTxModalOpen(false)}
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
            <h3 className="text-lg font-black text-slate-100">{lang === 'id' ? 'Tambah Hutang / Piutang' : 'New Debt / Credit Entry'}</h3>

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

              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setDebtType('payable')}
                  className={`py-2 rounded-xl font-bold border transition-colors ${
                    debtType === 'payable'
                      ? 'bg-rose-500/20 text-rose-300 border-rose-500/50'
                      : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}
                >
                  {lang === 'id' ? 'Hutang Saya (Bayar)' : 'I Owe (Payable)'}
                </button>
                <button
                  type="button"
                  onClick={() => setDebtType('receivable')}
                  className={`py-2 rounded-xl font-bold border transition-colors ${
                    debtType === 'receivable'
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50'
                      : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}
                >
                  {lang === 'id' ? 'Piutang (Tagih)' : 'Owed to Me (Receivable)'}
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Total Jumlah (Rp)' : 'Total (IDR)'}</label>
                  <input
                    type="number"
                    min="1000"
                    step="10000"
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
