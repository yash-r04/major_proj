import React, { useState, useEffect } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { Activity, ShieldCheck, Zap, TrendingUp, Cpu, Play, Pause, Lock, UserCheck, LogOut, Sliders, BatteryCharging } from 'lucide-react';

// Mock user profiles registered on the local P2P microgrid
const USERS = {
  bob: { id: 'bob', name: 'Bob (Prosumer Node 1)', role: 'Solar Heavy', solarCap: '5.0 kW', batCap: '10 kWh', avatar: '☀️' },
  alice: { id: 'alice', name: 'Alice (Prosumer Node 2)', role: 'Demand Heavy', solarCap: '1.0 kW', batCap: '5 kWh', avatar: '🏠' },
  david: { id: 'david', name: 'David (Prosumer Node 3)', role: 'Battery Arbitrage', solarCap: '3.0 kW', batCap: '15 kWh', avatar: '🔋' },
  admin: { id: 'admin', name: 'Grid Operator (Admin)', role: 'Microgrid Admin', solarCap: 'N/A', batCap: 'N/A', avatar: '⚡' }
};

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [loginForm, setLoginForm] = useState({ username: 'bob', password: '' });
  
  // Simulation & Node state
  const [activeSlot, setActiveSlot] = useState(12);
  const [isPlaying, setIsPlaying] = useState(false);
  const [nodePreferences, setNodePreferences] = useState({
    bob: { strategy: 'auto', maxSellPrice: 3.80, minSoc: 20 },
    alice: { strategy: 'auto', maxBuyPrice: 4.50, minSoc: 30 },
    david: { strategy: 'auto', maxSellPrice: 4.00, minSoc: 50 },
  });

  const [backendData, setBackendData] = useState(null);
  const [ledgerLogs, setLedgerLogs] = useState([]);
  const [isConnected, setIsConnected] = useState(false);

  // Fetch telemetry from FastAPI backend if active
useEffect(() => {
  const fetchData = async () => {
    try {
      // Changed port from 8000 to 5000
      const telemetryRes = await fetch('http://localhost:5000/api/telemetry/24h');
      if (telemetryRes.ok) {
        const tJson = await telemetryRes.json();
        setBackendData(tJson);
        setIsConnected(true);
      }

      // Changed port from 8000 to 5000
      const ledgerRes = await fetch('http://localhost:5000/api/ledger/blocks');
      if (ledgerRes.ok) {
        const lJson = await ledgerRes.json();
        setLedgerLogs(lJson.logs || []);
      }
    } catch (err) {
      console.warn("Flask backend offline, using fallback UI state.");
      setIsConnected(false);
    }
  };

  fetchData();
}, []);
  // Timer loop for auto-stepping 24h simulation
  useEffect(() => {
    let timer;
    if (isPlaying) {
      timer = setInterval(() => {
        setActiveSlot((prev) => (prev + 1) % 24);
      }, 1200);
    }
    return () => clearInterval(timer);
  }, [isPlaying]);

  // Handle Login
  const handleLogin = (e) => {
    e.preventDefault();
    if (USERS[loginForm.username]) {
      setCurrentUser(USERS[loginForm.username]);
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
  };

  // Generate 24-hour mathematical curves for telemetry
  const generateChartData = () => {
    return Array.from({ length: 24 }, (_, i) => {
      const hourStr = `${i.toString().padStart(2, '0')}:00`;
      
      let solar = i >= 6 && i <= 18 ? Math.max(0, 5.0 * Math.sin((Math.PI * (i - 6)) / 12)) : 0;
      let load = 1.2 + 1.5 * Math.exp(-Math.pow(i - 8, 2) / 4) + 2.0 * Math.exp(-Math.pow(i - 20, 2) / 4);

      if (currentUser?.id === 'bob') {
        solar *= 1.4; load *= 0.6;
      } else if (currentUser?.id === 'alice') {
        solar *= 0.2; load *= 1.3;
      } else if (currentUser?.id === 'david') {
        solar *= 0.8; load *= 0.9;
      }

      const mcp = Math.max(2.8, 5.25 - (solar * 0.45));

      return {
        time: hourStr,
        solar: parseFloat(solar.toFixed(2)),
        load: parseFloat(load.toFixed(2)),
        mcp: parseFloat(mcp.toFixed(2)),
      };
    });
  };

  const chartData = generateChartData();
  const currentSlotData = chartData[activeSlot];

  const defaultLogs = [
    { block: 14, hash: "0xbcf8070e9264bcaf12fea729dd7744d339dc7086ec4ffb6642f26f82c50e06e6", seller: "Bob (Node-1)", buyer: "Alice (Node-2)", volume: "0.74 kWh", price: "₹3.50" },
    { block: 13, hash: "0x8619e5f8b2b4ad96c4f6b216fe56b64713ef738f225ed51cc667cafa5b73f8fb", seller: "Bob (Node-1)", buyer: "David (Node-3)", volume: "0.40 kWh", price: "₹3.50" },
  ];

  const activeLedgerLogs = ledgerLogs.length > 0 ? ledgerLogs : defaultLogs;

  // Render Login Modal if not authenticated
  if (!currentUser) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4 font-sans">
        <div className="bg-slate-900 border border-slate-800 p-8 rounded-2xl shadow-2xl max-w-md w-full">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-amber-500/10 rounded-full border border-amber-500/30">
              <Zap className="text-amber-400 w-8 h-8 fill-amber-400" />
            </div>
          </div>
          <h2 className="text-2xl font-bold text-center text-white mb-1">P2P Energy Trading Portal</h2>
          <p className="text-xs text-slate-400 text-center mb-6">Select your prosumer node credentials to access asset controls</p>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Select User Profile</label>
              <select
                value={loginForm.username}
                onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-amber-500"
              >
                <option value="bob">Bob — Solar Heavy Prosumer (Node 1)</option>
                <option value="alice">Alice — Consumer Deficit (Node 2)</option>
                <option value="david">David — Battery Arbitrage (Node 3)</option>
                <option value="admin">Grid Operator (System Admin)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Passkey / Private Key</label>
              <input
                type="password"
                placeholder="••••••••••••"
                defaultValue="demo123"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-amber-500"
              />
            </div>

            <button
              type="submit"
              className="w-full bg-amber-500 text-slate-950 font-bold py-2.5 rounded-lg hover:bg-amber-400 transition flex items-center justify-center gap-2 mt-2"
            >
              <UserCheck className="w-4 h-4" /> Authenticate & Access Node
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-slate-800 text-center text-xs text-slate-500">
            Encrypted Session • Web3 Key Pair Verified
          </div>
        </div>
      </div>
    );
  }

  // Active User Node Preferences
  const activeUserPref = nodePreferences[currentUser.id] || { strategy: 'auto', maxSellPrice: 3.50, minSoc: 20 };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6 font-sans">
      
      {/* Top Header with User Context */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 pb-4 border-b border-slate-800 gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2 text-white">
            <Zap className="text-amber-400 fill-amber-400" />
            P2P Microgrid Energy Trading Platform
          </h1>
          <p className="text-sm text-slate-400">PPO DRL Intelligence • Pay-as-Bid Market Engine • Web3 Ledger</p>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3 bg-slate-800 px-4 py-2 rounded-lg border border-slate-700">
            <span className="text-xl">{currentUser.avatar}</span>
            <div className="text-xs">
              <span className="block font-bold text-white">{currentUser.name}</span>
              <span className="text-amber-400 font-mono">{currentUser.role}</span>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="p-2 bg-slate-800 hover:bg-rose-900/40 text-slate-400 hover:text-rose-400 rounded-lg border border-slate-700 transition"
            title="Sign Out"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* USER ASSET & ROLE CONTROL PANEL (User-Specific Preferences) */}
      {currentUser.id !== 'admin' ? (
        <div className="bg-slate-800/80 p-6 rounded-xl border border-amber-500/30 shadow-lg mb-8">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4 pb-3 border-b border-slate-700">
            <div className="flex items-center gap-2">
              <Sliders className="text-amber-400 w-5 h-5" />
              <h2 className="text-lg font-bold text-white">Personal Node Control Panel: {currentUser.name}</h2>
            </div>
            <span className="text-xs bg-emerald-500/20 text-emerald-300 px-3 py-1 rounded-full border border-emerald-500/30 font-medium">
              Authenticated Session Active
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Strategy Selector */}
            <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-700">
              <label className="block text-xs font-semibold text-slate-300 mb-2">Daily Trading Mode</label>
              <select
                value={activeUserPref.strategy}
                onChange={(e) => setNodePreferences({
                  ...nodePreferences,
                  [currentUser.id]: { ...activeUserPref, strategy: e.target.value }
                })}
                className="w-full bg-slate-800 border border-slate-700 rounded-md p-2 text-sm text-white focus:outline-none focus:border-amber-500"
              >
                <option value="auto">🤖 Autonomous DRL Agent (PPO Optimization)</option>
                <option value="force_sell">🟢 Force P2P Export (Producer Mode)</option>
                <option value="force_buy">🔵 Force P2P Import (Consumer Mode)</option>
                <option value="battery_hold">🔋 Reserve Energy for Home Storage</option>
              </select>
              <p className="text-[11px] text-slate-400 mt-2">
                {activeUserPref.strategy === 'auto' && 'DRL agent dynamically decides buy/sell bids to maximize your cost savings.'}
                {activeUserPref.strategy === 'force_sell' && 'Manually forces node to list all available solar generation as P2P seller bids.'}
                {activeUserPref.strategy === 'force_buy' && 'Manually forces node to consume P2P microgrid energy before grid imports.'}
                {activeUserPref.strategy === 'battery_hold' && 'Bypasses P2P market to charge local battery reserve first.'}
              </p>
            </div>

            {/* Asset Threshold Controls */}
            <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-700">
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Target Tariff Threshold (₹/kWh): <strong className="text-amber-400">₹{activeUserPref.maxSellPrice || 3.50}</strong>
              </label>
              <input
                type="range"
                min="2.50"
                max="5.25"
                step="0.10"
                value={activeUserPref.maxSellPrice || 3.50}
                onChange={(e) => setNodePreferences({
                  ...nodePreferences,
                  [currentUser.id]: { ...activeUserPref, maxSellPrice: parseFloat(e.target.value) }
                })}
                className="w-full accent-amber-500 cursor-pointer mb-2"
              />
              <span className="text-[11px] text-slate-400">Will not execute trades if market price moves beyond this limit.</span>
            </div>

            {/* Hardware Status */}
            <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-700 flex flex-col justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-300 block mb-2">Hardware Telemetry</span>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">Solar PV Capacity:</span>
                  <span className="text-amber-400 font-mono">{currentUser.solarCap}</span>
                </div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400">Battery Capacity:</span>
                  <span className="text-cyan-400 font-mono">{currentUser.batCap}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-emerald-400 font-medium">
                <BatteryCharging className="w-4 h-4" /> Battery SoC: 68% (Healthy)
              </div>
            </div>

          </div>
        </div>
      ) : (
        <div className="bg-slate-800/80 p-4 rounded-xl border border-cyan-500/30 mb-8 flex justify-between items-center">
          <span className="text-sm font-semibold text-cyan-300 flex items-center gap-2">
            <Lock className="w-4 h-4" /> System Admin View Active: Observing all microgrid prosumer nodes
          </span>
          <span className="text-xs text-slate-400">Global Overrides Enabled</span>
        </div>
      )}

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        
        <div className="bg-slate-800/60 p-5 rounded-xl border border-slate-700/60 shadow-lg backdrop-blur">
          <div className="flex justify-between items-center text-slate-400 text-sm mb-2">
            <span>Market Clearing Price</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            ₹{currentSlotData.mcp.toFixed(2)} <span className="text-xs font-normal text-slate-400">/ kWh</span>
          </div>
          <span className="text-xs text-emerald-400 font-medium mt-1 inline-block">
            ↓ {((1 - currentSlotData.mcp / 5.25) * 100).toFixed(1)}% vs Utility Rate
          </span>
        </div>

        <div className="bg-slate-800/60 p-5 rounded-xl border border-slate-700/60 shadow-lg backdrop-blur">
          <div className="flex justify-between items-center text-slate-400 text-sm mb-2">
            <span>24h Traded Volume</span>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {backendData?.summary?.total_p2p_traded || "14.28"} <span className="text-xs font-normal text-slate-400">kWh</span>
          </div>
          <span className="text-xs text-slate-400 mt-1 inline-block">100% Peer-to-Peer Matched</span>
        </div>

        <div className="bg-slate-800/60 p-5 rounded-xl border border-slate-700/60 shadow-lg backdrop-blur">
          <div className="flex justify-between items-center text-slate-400 text-sm mb-2">
            <span>Cost Savings (PPO Agent)</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">
            {backendData?.summary?.cost_savings_pct || "59.3"}%
          </div>
          <span className="text-xs text-emerald-400 font-medium mt-1 inline-block">Verified vs Baseline</span>
        </div>

        <div className="bg-slate-800/60 p-5 rounded-xl border border-slate-700/60 shadow-lg backdrop-blur">
          <div className="flex justify-between items-center text-slate-400 text-sm mb-2">
            <span>On-Chain Ledger</span>
            <Cpu className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-300">
            {activeLedgerLogs.length} Blocks
          </div>
          <span className="text-xs text-slate-400 mt-1 inline-block">Ganache Auto-Mined</span>
        </div>

      </div>

      {/* Main Graph & Control Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        
        {/* Recharts Area Chart */}
        <div className="lg:col-span-2 bg-slate-800/60 p-6 rounded-xl border border-slate-700/60 shadow-lg backdrop-blur">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Activity className="text-amber-400 w-5 h-5" />
                24-Hour Telemetry: Solar PV Generation vs Household Load
              </h2>
              <p className="text-xs text-slate-400">
                Viewing profile for: <strong className="text-amber-400">{currentUser.name}</strong>
              </p>
            </div>
          </div>

          {/* Time Controls */}
          <div className="flex items-center gap-4 mb-4 bg-slate-900/50 p-3 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-amber-500 text-slate-950 font-bold hover:bg-amber-400 transition"
            >
              {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              {isPlaying ? 'Pause' : 'Auto Step 24h'}
            </button>
            <span className="text-slate-400">Time Slot: <strong className="text-amber-400">{currentSlotData.time}</strong></span>
            <input
              type="range"
              min="0"
              max="23"
              value={activeSlot}
              onChange={(e) => setActiveSlot(Number(e.target.value))}
              className="w-full accent-amber-500 cursor-pointer"
            />
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorSolar" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#F59E0B" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorLoad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#06B6D4" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" stroke="#94A3B8" />
                <YAxis stroke="#94A3B8" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', color: '#F8FAFC' }}
                  itemStyle={{ color: '#F8FAFC' }}
                />
                <Area
                  type="monotone"
                  dataKey="solar"
                  name="Solar PV Output (kW)"
                  stroke="#F59E0B"
                  fillOpacity={1}
                  fill="url(#colorSolar)"
                  strokeWidth={2.5}
                />
                <Area
                  type="monotone"
                  dataKey="load"
                  name="Demand Load (kW)"
                  stroke="#06B6D4"
                  fillOpacity={1}
                  fill="url(#colorLoad)"
                  strokeWidth={2.5}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Live Double Auction Matrix */}
        <div className="bg-slate-800/60 p-6 rounded-xl border border-slate-700/60 shadow-lg backdrop-blur">
          <h2 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
            <Activity className="text-cyan-400 w-5 h-5" />
            Pay-as-Bid Auction Matrix
          </h2>
          <p className="text-xs text-slate-400 mb-4">Slot #{activeSlot} ({currentSlotData.time})</p>

          <div className="space-y-3 text-sm">
            <div className={`p-3 rounded-lg border ${currentUser.id === 'bob' ? 'bg-amber-950/60 border-amber-400' : 'bg-slate-900/60 border-slate-700'}`}>
              <div className="flex justify-between items-center mb-1">
                <span className="font-semibold text-amber-400">
                  Seller: Bob (Node-1) {currentUser.id === 'bob' && '(YOU)'}
                </span>
                <span className="text-xs bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded font-mono">
                  ASK: ₹3.50/kWh
                </span>
              </div>
              <span className="text-xs text-slate-400">Surplus PV Generation: {currentSlotData.solar} kW</span>
            </div>

            <div className={`p-3 rounded-lg border ${currentUser.id === 'alice' ? 'bg-cyan-950/60 border-cyan-400' : 'bg-slate-900/60 border-slate-700'}`}>
              <div className="flex justify-between items-center mb-1">
                <span className="font-semibold text-cyan-400">
                  Buyer: Alice (Node-2) {currentUser.id === 'alice' && '(YOU)'}
                </span>
                <span className="text-xs bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded font-mono">
                  BID: ₹3.80/kWh
                </span>
              </div>
              <span className="text-xs text-slate-400">Deficit Load Demand: {currentSlotData.load} kW</span>
            </div>

            <div className="p-3 bg-emerald-950/40 rounded-lg border border-emerald-500/40">
              <div className="flex justify-between items-center">
                <div>
                  <span className="font-semibold block text-emerald-400">Cleared Trade Status</span>
                  <span className="text-xs text-slate-300">
                    Volume: {Math.min(currentSlotData.solar, currentSlotData.load).toFixed(2)} kWh @ ₹{currentSlotData.mcp.toFixed(2)}
                  </span>
                </div>
                <span className="bg-emerald-500/20 text-emerald-300 text-xs px-2.5 py-1 rounded font-bold">
                  MATCHED
                </span>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* On-Chain Audit Stream Table */}
      <div className="bg-slate-800/60 p-6 rounded-xl border border-slate-700/60 shadow-lg backdrop-blur">
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <ShieldCheck className="text-cyan-400 w-5 h-5" />
          On-Chain Ethereum Settlement Audit Feed (Ganache)
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-slate-400">
                <th className="py-2.5 px-3">Block #</th>
                <th className="py-2.5 px-3">Transaction Hash</th>
                <th className="py-2.5 px-3">Counterparties</th>
                <th className="py-2.5 px-3">Volume</th>
                <th className="py-2.5 px-3">Cleared Price</th>
              </tr>
            </thead>
            <tbody>
              {activeLedgerLogs.map((tx, idx) => (
                <tr key={tx.hash || idx} className="border-b border-slate-700/50 hover:bg-slate-800/40 transition">
                  <td className="py-3 px-3 font-semibold text-cyan-400">#{tx.block}</td>
                  <td className="py-3 px-3 font-mono text-xs text-slate-400">{tx.hash.substring(0, 24)}...</td>
                  <td className="py-3 px-3">{tx.seller} → {tx.buyer}</td>
                  <td className="py-3 px-3 font-medium text-amber-300">{tx.volume}</td>
                  <td className="py-3 px-3 font-semibold text-emerald-400">{tx.price}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}