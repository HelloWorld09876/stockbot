import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Bot, 
  LineChart, 
  Briefcase, 
  Target,
  RefreshCw,
  Plus,
  Trash2,
  AlertCircle
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, Cell 
} from 'recharts';
import './App.css';

const API_BASE = 'http://localhost:8000';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [botData, setBotData] = useState(null);
  const [portfolio, setPortfolio] = useState([]);
  
  // Fetch initial portfolio
  useEffect(() => {
    fetchPortfolio();
  }, []);

  const fetchPortfolio = async () => {
    try {
      const res = await axios.get(`${API_BASE}/db/trades/`);
      setPortfolio(res.data);
    } catch (err) {
      console.error("Failed to fetch portfolio:", err);
    }
  };

  const runBot = async (strategy) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API_BASE}/run-bot`, {
        params: { strategy }
      });
      setBotData(res.data);
      if (res.data.current_portfolio_status) {
        setPortfolio(res.data.current_portfolio_status);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTrade = async (id) => {
    try {
      await axios.delete(`${API_BASE}/db/trades/${id}`);
      fetchPortfolio();
    } catch (err) {
      alert("Failed to delete trade: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <nav className="sidebar">
        <div className="brand">
          <Bot size={28} />
          <span>StockBot MVP</span>
        </div>
        <div className="nav-links">
          <button 
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <LineChart size={20} />
            <span>Advisory Engine</span>
          </button>
          <button 
            className={`nav-item ${activeTab === 'portfolio' ? 'active' : ''}`}
            onClick={() => setActiveTab('portfolio')}
          >
            <Briefcase size={20} />
            <span>Portfolio Manager</span>
          </button>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="main-content animate-fade">
        <div className="section">
          {activeTab === 'dashboard' && (
            <Dashboard 
              onRunBot={runBot} 
              loading={loading} 
              data={botData} 
              error={error} 
            />
          )}
          {activeTab === 'portfolio' && (
            <Portfolio 
              portfolio={portfolio} 
              onRefresh={fetchPortfolio}
              onDelete={handleDeleteTrade}
            />
          )}
        </div>
      </main>
    </div>
  );
}

// -------------------------------------------------------------
// DASHBOARD (Advisory Engine)
// -------------------------------------------------------------
function Dashboard({ onRunBot, loading, data, error }) {
  const [strategy, setStrategy] = useState('golden_cross');

  // Convert allocation object to array for Recharts
  const chartData = data?.recommended_allocation 
    ? Object.entries(data.recommended_allocation)
        .map(([ticker, weight]) => ({ 
          name: ticker.replace('.NS',''), 
          fullName: ticker,
          weight: weight * 100 
        }))
        .sort((a,b) => b.weight - a.weight)
    : [];

  return (
    <div>
      <div className="header">
        <h1>Advisory Engine</h1>
        <p>Run quantitative algorithms to scan the Nifty 50 and compute optimal portfolio allocations.</p>
      </div>

      <div className="panel animate-fade" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
          <div className="input-group" style={{ marginBottom: 0, minWidth: '250px' }}>
            <label>Select Strategy</label>
            <select 
              className="input-field" 
              value={strategy} 
              onChange={e => setStrategy(e.target.value)}
            >
              <option value="golden_cross">Golden Cross (Trend Following)</option>
              <option value="alpha">Nifty Alpha (Momentum)</option>
            </select>
          </div>
          <button 
            className="btn btn-primary" 
            onClick={() => onRunBot(strategy)}
            disabled={loading}
          >
            {loading ? <RefreshCw className="animate-spin" size={18} /> : <Target size={18} />}
            {loading ? "Scanning Markets..." : "Initialize Scan"}
          </button>
        </div>
        
        {error && (
          <div style={{ color: 'var(--danger)', marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
            <AlertCircle size={20} />
            {error}
          </div>
        )}
      </div>

      {loading && (
        <div className="loader-wrapper animate-fade">
          <div className="loader"></div>
        </div>
      )}

      {!loading && data && data.status === 'success' && (
        <div className="animate-fade">
          <div className="grid-2">
            <div className="panel">
              <h2 style={{ marginBottom: '1rem', fontFamily: 'var(--font-sans)', fontSize: '1.2rem', color: 'var(--accent-gold)' }}>
                Signal Highlights
              </h2>
              <p style={{ color: 'var(--text-dim)', marginBottom: '1rem' }}>
                Strategy: <span style={{ color: 'var(--text-main)', textTransform: 'capitalize' }}>{data.strategy_used.replace('_', ' ')}</span>
              </p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {data.filtered_buy_list.map((ticker, idx) => (
                  <div key={idx} className="signal-item">
                    <span className="badge badge-success">BUY</span>
                    <span className="ticker-name">{ticker.replace('.NS', '')}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="panel">
              <h2 style={{ marginBottom: '1rem', fontFamily: 'var(--font-sans)', fontSize: '1.2rem', color: 'var(--accent-gold)' }}>
                Allocation Distribution
              </h2>
              
              <div className="allocation-list" style={{ marginBottom: '1.5rem' }}>
                {chartData.map((item, idx) => (
                  <div key={idx} className="allocation-row">
                    <span className="ticker-name">{item.name}</span>
                    <div className="allocation-bar-bg">
                      <div className="allocation-bar-fill" style={{ width: `${item.weight}%` }}></div>
                    </div>
                    <span className="percentage-text">{item.weight.toFixed(2)}%</span>
                  </div>
                ))}
              </div>
              <div style={{ height: '200px', width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <XAxis dataKey="name" stroke="var(--text-dim)" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="var(--text-dim)" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => `${val}%`} />
                    <RechartsTooltip cursor={{fill: 'var(--bg-hover)'}} contentStyle={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-gold)', borderRadius: '8px' }} formatter={(val) => [`${val.toFixed(2)}%`, 'Weight']} />
                    <Bar dataKey="weight" radius={[4, 4, 0, 0]}>
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={index === 0 ? 'var(--accent-gold)' : 'var(--text-dim)'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {!loading && data && data.status === 'no_signals' && (
        <div className="panel animate-fade" style={{ textAlign: 'center', padding: '3rem' }}>
          <Target size={48} color="var(--warn)" style={{ marginBottom: '1rem', opacity: 0.5 }} />
          <h2>No Trading Signals Triggered</h2>
          <p style={{ color: 'var(--text-dim)', marginTop: '0.5rem' }}>{data.message}</p>
        </div>
      )}
    </div>
  );
}

// -------------------------------------------------------------
// PORTFOLIO MANAGER
// -------------------------------------------------------------
function Portfolio({ portfolio, onRefresh, onDelete }) {
  const [showAdd, setShowAdd] = useState(false);
  
  const [formData, setFormData] = useState({
    ticker: '',
    buy_price: '',
    quantity: '',
    buy_date: new Date().toISOString().split('T')[0],
    strategy_used: 'manual'
  });

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_BASE}/db/trades/`, {
        ...formData,
        buy_price: parseFloat(formData.buy_price),
        quantity: parseInt(formData.quantity, 10)
      });
      setShowAdd(false);
      onRefresh();
      setFormData({...formData, ticker:'', buy_price:'', quantity:''});
    } catch (err) {
      alert("Failed to add trade: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div>
      <div className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1>Portfolio Manager</h1>
          <p>Track your active positions and historical trades.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn" onClick={onRefresh}>
            <RefreshCw size={18} />
          </button>
          <button className="btn btn-primary" onClick={() => setShowAdd(!showAdd)}>
            <Plus size={18} /> Add Trade
          </button>
        </div>
      </div>

      {showAdd && (
        <div className="panel animate-fade" style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontFamily: 'var(--font-sans)', fontSize: '1.2rem', marginBottom: '1.5rem', color: 'var(--accent-gold)' }}>Register New Position</h2>
          <form onSubmit={handleCreate} style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <div className="input-group highlight-input" style={{ flex: 1, minWidth: '150px' }}>
              <label>Ticker (e.g. RELIANCE.NS)</label>
              <input required type="text" className="input-field" value={formData.ticker} onChange={e => setFormData({...formData, ticker: e.target.value})} />
            </div>
            <div className="input-group highlight-input" style={{ flex: 1, minWidth: '100px' }}>
              <label>Buy Price (₹)</label>
              <input required type="number" step="0.05" className="input-field" value={formData.buy_price} onChange={e => setFormData({...formData, buy_price: e.target.value})} />
            </div>
            <div className="input-group highlight-input" style={{ flex: 1, minWidth: '100px' }}>
              <label>Quantity</label>
              <input required type="number" className="input-field" value={formData.quantity} onChange={e => setFormData({...formData, quantity: e.target.value})} />
            </div>
            <div className="input-group" style={{ flex: 1, minWidth: '150px' }}>
              <label>Strategy</label>
              <select className="input-field" value={formData.strategy_used} onChange={e => setFormData({...formData, strategy_used: e.target.value})}>
                <option value="manual">Manual Execution</option>
                <option value="golden_cross">Golden Cross</option>
                <option value="alpha">Nifty Alpha</option>
              </select>
            </div>
            <div className="input-group" style={{ display: 'flex', alignItems: 'flex-end', minWidth: '120px' }}>
              <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>Submit</button>
            </div>
          </form>
        </div>
      )}

      <div className="table-wrapper animate-fade">
        {portfolio.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-dim)' }}>
            No trades registered in the portfolio yet.
          </div>
        ) : (
          <table className="styled-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Price</th>
                <th>Qty</th>
                <th>Total Value</th>
                <th>Strategy</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.map(trade => (
                <tr key={trade.id}>
                  <td style={{ fontWeight: 600, color: 'var(--text-main)' }}>{trade.ticker}</td>
                  <td>₹{trade.buy_price.toLocaleString(undefined, {minimumFractionDigits:2})}</td>
                  <td>{trade.quantity}</td>
                  <td style={{ color: 'var(--accent-gold)' }}>₹{(trade.buy_price * trade.quantity).toLocaleString(undefined, {minimumFractionDigits:2})}</td>
                  <td><span className="badge badge-info">{trade.strategy_used}</span></td>
                  <td>{trade.buy_date}</td>
                  <td>
                    <button className="btn" style={{ padding: '0.4rem 0.6rem', borderColor: 'transparent' }} onClick={() => onDelete(trade.id)}>
                      <Trash2 size={16} color="var(--danger)" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
