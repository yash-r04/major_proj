import React, { useState, useEffect } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine } from 'recharts';
import { Activity, ShieldCheck, Zap, TrendingUp, UserCheck, LogOut, Sliders, BatteryCharging, UserPlus, Users, RefreshCw, AlertCircle } from 'lucide-react';

// Default registered microgrid prosumers with internal security credentials
const INITIAL_NODES = [
  { id: 'alice', name: 'Alice (Node-1)', pass: 'alice123', role: 'Solar Heavy', solarCap: 5.0, batCap: 10.0, address: '0x71C...3A1' },
  { id: 'bob', name: 'Bob (Node-2)', pass: 'bob123', role: 'Demand Heavy', solarCap: 1.0, batCap: 5.0, address: '0x3B8...9F2' },
  { id: 'david', name: 'David (Node-3)', pass: 'david123', role: 'Battery Arbitrage', solarCap: 3.0, batCap: 15.0, address: '0xF41...6D8' },
];

export default function App() {
  // Registry & Auth State
  const [nodes, setNodes] = useState(INITIAL_NODES);
  const [currentUser, setCurrentUser] = useState(INITIAL_NODES[0]);
  const [selectedNodeId, setSelectedNodeId] = useState('');
  const [passphrase, setPassphrase] = useState('');
  const [authError, setAuthError] = useState('');

  // New Participant Onboarding State
  const [isRegistering, setIsRegistering] = useState(false);
  const [newNode, setNewNode] = useState({ name: '', pass: '', role: 'Solar Heavy', solarCap: '3.5', batCap: '7.0' });

  // Telemetry & Polling State
  const [activeSlot, setActiveSlot] = useState(12);
  const [isPlaying, setIsPlaying] = useState(false);
  const [nodePreferences, setNodePreferences] = useState({});
  const [telemetry, setTelemetry] = useState(null);
  const [ledgerLogs, setLedgerLogs] = useState([]);
  const [live, setLive] = useState(null);
  const [ledgerSim, setLedgerSim] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [isPolling, setIsPolling] = useState(false);

  // Poll backend server (http://127.0.0.1:5000)
  const fetchBackendData = async () => {
    setIsPolling(true);
    try {
      const telRes = await fetch('http://127.0.0.1:5000/api/telemetry/24h');
      if (telRes.ok) {
        const telJson = await telRes.json();
        setTelemetry(telJson);
        setIsConnected(true);
      }

      const ledRes = await fetch('http://127.0.0.1:5000/api/ledger/blocks');
      if (ledRes.ok) {
        const ledJson = await ledRes.json();
        setLedgerLogs(ledJson.logs || []);
        setLedgerSim(!!ledJson.simulated);
      }

      const liveRes = await fetch('http://127.0.0.1:5000/api/live');
      if (liveRes.ok) setLive(await liveRes.json());
    } catch (err) {
      setIsConnected(false);
    } finally {
      setIsPolling(false);
    }
  };

  useEffect(() => {
    fetchBackendData();
    const interval = setInterval(fetchBackendData, 2000);
    return () => clearInterval(interval);
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

  // Onboard New Participant Node
  const handleRegisterNode = (e) => {
    e.preventDefault();
    if (!newNode.name.trim() || !newNode.pass.trim()) return;

    const nodeIdx = nodes.length + 1;
    const createdNode = {
      id: `node_${Date.now()}`,
      name: `${newNode.name.trim()} (Node-${nodeIdx})`,
      pass: newNode.pass.trim(),
      role: newNode.role,
      solarCap: parseFloat(newNode.solarCap) || 0,
      batCap: parseFloat(newNode.batCap) || 0,
      address: `0x${Math.random().toString(16).substring(2, 5).toUpperCase()}...${Math.random().toString(16).substring(2, 5).toUpperCase()}`
    };

    setNodes((prev) => [...prev, createdNode]);
    setNewNode({ name: '', pass: '', role: 'Solar Heavy', solarCap: '3.5', batCap: '7.0' });
    setIsRegistering(false);
  };

  // Authenticate Prosumer Account
  const handleLogin = (e) => {
    e.preventDefault();
    setAuthError('');

    if (!selectedNodeId) {
      setAuthError('Select a participant node.');
      return;
    }

    const found = nodes.find((n) => n.id === selectedNodeId);
    if (!found) {
      setAuthError('Node profile not found.');
      return;
    }

    if (passphrase.trim() !== found.pass) {
      setAuthError('Authentication failed: Invalid credentials or security signature.');
      return;
    }

    setCurrentUser(found);
    setPassphrase('');
  };

  const chartData = telemetry?.data || Array.from({ length: 24 }, (_, i) => {
    const hourStr = `${i.toString().padStart(2, '0')}:00`;
    const solar = i >= 6 && i <= 18 ? Math.max(0, 5.0 * Math.sin((Math.PI * (i - 6)) / 12)) : 0;
    const load = 1.2 + 1.5 * Math.exp(-Math.pow(i - 8, 2) / 4) + 2.0 * Math.exp(-Math.pow(i - 20, 2) / 4);
    const mcp = Math.max(2.50, 5.25 - (solar * 0.45));
    return {
      hour: hourStr,
      solar_pv: parseFloat(solar.toFixed(2)),
      load_demand: parseFloat(load.toFixed(2)),
      mcp: parseFloat(mcp.toFixed(2))
    };
  });

  const currentSlotData = chartData[activeSlot] || chartData[0];
  const liveDevices = Object.values(live?.devices || {});
  const liveMarket = live?.market || {};
  const activeUserPref = nodePreferences[currentUser?.id] || { strategy: 'auto', maxSellPrice: 3.50 };

  // UNAUTHENTICATED GATEWAY
  if (!currentUser) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4 font-sans">
        <div className="bg-slate-900 border border-slate-800 p-8 rounded-xl shadow-xl max-w-md w-full">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-amber-500/10 rounded-full border border-amber-500/20">
              <Zap className="text-amber-400 w-7 h-7" />
            </div>
          </div>
          <h2 className="text-xl font-bold text-center text-white mb-1">ASTRA Gateway</h2>
          <p className="text-xs text-slate-400 text-center mb-6">
            Automated Smart Trading & Routing Agent • Prosumer Portal
          </p>

          {authError && (
            <div className="mb-4 p-2.5 bg-rose-950/60 border border-rose-500/30 text-rose-300 text-xs rounded-lg text-center flex items-center justify-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400" />
              <span>{authError}</span>
            </div>
          )}

          {!isRegistering ? (
            <div className="space-y-4">
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Participant Node</label>
                  <select
                    value={selectedNodeId}
                    onChange={(e) => setSelectedNodeId(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-amber-500"
                  >
                    <option value="" disabled>-- Select Node --</option>
                    {nodes.map((node) => (
                      <option key={node.id} value={node.id}>
                        {node.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Passphrase / Key</label>
                  <input
                    type="password"
                    value={passphrase}
                    onChange={(e) => setPassphrase(e.target.value)}
                    placeholder="Enter node passphrase"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-amber-500"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full bg-amber-500 text-slate-950 font-semibold text-xs py-2.5 rounded-lg hover:bg-amber-400 transition flex items-center justify-center gap-2"
                >
                  <UserCheck className="w-4 h-4" /> Authenticate Node
                </button>
              </form>

              <button
                type="button"
                onClick={() => setIsRegistering(true)}
                className="w-full bg-slate-950 text-slate-300 border border-slate-800 hover:bg-slate-800 font-medium py-2.5 rounded-lg text-xs transition flex items-center justify-center gap-1.5 mt-2"
              >
                <UserPlus className="w-4 h-4 text-amber-400" /> Register New Node
              </button>
            </div>
          ) : (
            <form onSubmit={handleRegisterNode} className="space-y-3 bg-slate-950/60 p-4 rounded-lg border border-slate-800">
              <h3 className="text-xs font-bold text-amber-400 flex items-center gap-2">
                <UserPlus className="w-4 h-4" /> Prosumer Registration
              </h3>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Participant Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Charlie"
                  value={newNode.name}
                  onChange={(e) => setNewNode({ ...newNode, name: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-xs text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Set Passphrase</label>
                <input
                  type="password"
                  required
                  placeholder="Enter passphrase"
                  value={newNode.pass}
                  onChange={(e) => setNewNode({ ...newNode, pass: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-xs text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Operating Profile</label>
                <select
                  value={newNode.role}
                  onChange={(e) => setNewNode({ ...newNode, role: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-xs text-white focus:outline-none focus:border-amber-500"
                >
                  <option value="Solar Heavy">Solar Heavy (Net Exporter)</option>
                  <option value="Demand Heavy">Demand Heavy (Net Consumer)</option>
                  <option value="Battery Arbitrage">Battery Arbitrage Prosumer</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">PV Peak (kW)</label>
                  <input
                    type="number"
                    step="0.5"
                    value={newNode.solarCap}
                    onChange={(e) => setNewNode({ ...newNode, solarCap: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-xs text-white focus:outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Battery (kWh)</label>
                  <input
                    type="number"
                    step="0.5"
                    value={newNode.batCap}
                    onChange={(e) => setNewNode({ ...newNode, batCap: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-xs text-white focus:outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  className="flex-1 bg-amber-500 text-slate-950 font-semibold py-2 rounded text-xs hover:bg-amber-400 transition"
                >
                  Confirm Registration
                </button>
                <button
                  type="button"
                  onClick={() => setIsRegistering(false)}
                  className="px-3 bg-slate-800 text-slate-400 hover:text-white rounded text-xs transition"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="mt-6 pt-4 border-t border-slate-800 text-center text-xs text-slate-500 flex justify-between items-center">
            <span>ASTRA Engine (Port 5000)</span>
            <span className="text-amber-400 font-mono">{nodes.length} Active Nodes</span>
          </div>
        </div>
      </div>
    );
  }

  // AUTHENTICATED DASHBOARD
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6 font-sans">
      
      {/* Header */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 pb-4 border-b border-slate-800 gap-4">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2 text-white">
            <Zap className="text-amber-400" />
            ASTRA — Automated Smart Trading & Routing Agent
          </h1>
          <p className="text-xs text-slate-400">PPO DRL Core • Midpoint Double Auction Market • Web3 Settlement Audit</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700 text-xs">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`}></span>
            <span className="text-slate-300">{isConnected ? 'ASTRA Core Active' : 'Offline'}</span>
            <button onClick={fetchBackendData} className="ml-1 text-slate-400 hover:text-white" title="Refresh Telemetry">
              <RefreshCw className={`w-3.5 h-3.5 ${isPolling ? 'animate-spin text-amber-400' : ''}`} />
            </button>
          </div>

          <div className="flex items-center gap-3 bg-slate-800 px-4 py-2 rounded-lg border border-slate-700">
            <div className="text-xs">
              <span className="block font-bold text-white">{currentUser.name}</span>
              <span className="text-amber-400 font-mono">{currentUser.address}</span>
            </div>
          </div>

          <button
            onClick={() => setCurrentUser(nodes[(nodes.findIndex((n) => n.id === currentUser.id) + 1) % nodes.length])}
            className="p-2 bg-slate-800 hover:bg-rose-900/40 text-slate-400 hover:text-rose-400 rounded-lg border border-slate-700 transition"
            title="Switch node"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Live devices and market */}
      <div className="bg-slate-800/80 p-5 rounded-xl border border-emerald-500/30 shadow-lg mb-8">
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Activity className="text-emerald-400 w-4 h-4" />
            Live devices
          </h2>
          <span className="text-xs text-slate-400">{live ? `Decisions by: ${live.model_loaded ? 'PPO model' : 'rule fallback'}` : 'Waiting for backend...'}</span>
        </div>
        {liveDevices.length === 0 ? (
          <p className="text-xs text-slate-400">No device has reported yet. Power the ESP32 or run agent/sim_devices.py.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  {['Device', 'Profile', 'Slot', 'PV kW', 'Load kW', 'SoC', 'Trade', 'ESS kW', 'Bid', 'Load mA', 'Delivery', 'Penalties', 'Age'].map((h) => (
                    <th key={h} className="py-2 px-2">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {liveDevices.map((d) => (
                  <tr key={d.id} className="border-b border-slate-700/50">
                    <td className="py-2 px-2 font-semibold text-cyan-400">{d.id}{d.id === 'alice' ? ' (ESP32)' : ' (sim)'}</td>
                    <td className="py-2 px-2">{d.profile}</td>
                    <td className="py-2 px-2">{d.slot}</td>
                    <td className="py-2 px-2">{d.pv_kw?.toFixed(2)}</td>
                    <td className="py-2 px-2">{d.load_kw?.toFixed(2)}</td>
                    <td className="py-2 px-2">{Math.round((d.soc ?? 0) * 100)}%</td>
                    <td className={`py-2 px-2 font-medium ${d.e_tra_kw > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{d.e_tra_kw > 0 ? 'Sell' : 'Buy'} {Math.abs(d.e_tra_kw).toFixed(2)}</td>
                    <td className="py-2 px-2">{d.ess_kw?.toFixed(2)}</td>
                    <td className="py-2 px-2 text-amber-300">₹{d.bid_price?.toFixed(2)}</td>
                    <td className="py-2 px-2">{d.measured_ma != null ? d.measured_ma.toFixed(1) : '—'}</td>
                    <td className={`py-2 px-2 ${d.delivery_ok === false ? 'text-rose-400 font-bold' : 'text-emerald-400'}`}>{d.delivery_ok === false ? 'FAILED' : 'OK'}{d.fault ? ' (fault)' : ''}</td>
                    <td className="py-2 px-2">{live?.stats?.[d.id]?.penalties ?? 0}</td>
                    <td className="py-2 px-2 text-slate-400">{Math.max(0, Math.round(live.server_time - d.server_ts))}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {liveMarket.devices && (
          <p className="text-xs text-slate-300 mt-3">
            Market (slot {liveMarket.slot}): {liveMarket.trades?.length
              ? liveMarket.trades.map((t) => `${t.seller_id} → ${t.buyer_id} ${t.volume_kwh} kWh @ ₹${t.price_inr}`).join('  |  ')
              : 'no P2P match, grid fallback'}
            {'  •  '}grid import {liveMarket.grid_import_kwh} kWh (₹{liveMarket.grid_import_cost}), export {liveMarket.grid_export_kwh} kWh
          </p>
        )}
      </div>

      {/* Control Panel */}
      <div className="bg-slate-800/80 p-5 rounded-xl border border-slate-700/80 shadow-lg mb-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4 pb-3 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <Sliders className="text-amber-400 w-4 h-4" />
            <h2 className="text-sm font-bold text-white">ASTRA Policy Parameters: {currentUser.name}</h2>
          </div>
          <span className="text-xs bg-emerald-500/10 text-emerald-400 px-3 py-0.5 rounded border border-emerald-500/20 font-medium">
            Demo mode (no login)
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-700">
            <label className="block text-xs font-semibold text-slate-300 mb-2">Trading Strategy</label>
            <select
              value={activeUserPref.strategy}
              onChange={(e) => setNodePreferences({
                ...nodePreferences,
                [currentUser.id]: { ...activeUserPref, strategy: e.target.value }
              })}
              className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-xs text-white focus:outline-none focus:border-amber-500"
            >
              <option value="auto">Autonomous ASTRA Agent (PPO Optimization)</option>
              <option value="force_sell">Force P2P Export (Producer Mode)</option>
              <option value="force_buy">Force P2P Import (Consumer Mode)</option>
              <option value="battery_hold">Battery Energy Reserve Mode</option>
            </select>
          </div>

          <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-700">
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Target Tariff Limit: <strong className="text-amber-400">₹{activeUserPref.maxSellPrice || 3.50}/kWh</strong>
            </label>
            <input
              type="range"
              min="2.50"
              max="6.00"
              step="0.10"
              value={activeUserPref.maxSellPrice || 3.50}
              onChange={(e) => setNodePreferences({
                ...nodePreferences,
                [currentUser.id]: { ...activeUserPref, maxSellPrice: parseFloat(e.target.value) }
              })}
              className="w-full accent-amber-500 cursor-pointer mb-1"
            />
          </div>

          <div className="bg-slate-900/60 p-4 rounded-lg border border-slate-700 flex flex-col justify-between">
            <div>
              <span className="text-xs font-semibold text-slate-300 block mb-2">Hardware Telemetry</span>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-400">PV Capacity:</span>
                <span className="text-amber-400 font-mono">{currentUser.solarCap} kW</span>
              </div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-400">Battery Reserve:</span>
                <span className="text-cyan-400 font-mono">{currentUser.batCap} kWh</span>
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs text-emerald-400 font-medium">
              <BatteryCharging className="w-4 h-4" /> Reserve Status: Nominal
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        <div className="bg-slate-800/60 p-5 rounded-xl border border-slate-700/60 shadow-lg backdrop-blur">
          <div className="flex justify-between items-center text-slate-400 text-xs mb-2">
            <span>Clearing Price (live)</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {liveMarket.mcp != null ? `₹${liveMarket.mcp.toFixed(2)}` : '—'} <span className="text-xs font-normal text-slate-400">/ kWh</span>
          </div>
        </div>

        <div className="bg-slate-800/60 p-5 rounded-xl border border-slate-700/60 shadow-lg backdrop-blur">
          <div className="flex justify-between items-center text-slate-400 text-xs mb-2">
            <span>P2P Volume (latest slot)</span>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {liveMarket.p2p_kwh ?? "—"} <span className="text-xs font-normal text-slate-400">kWh</span>
          </div>
        </div>

        <div className="bg-slate-800/60 p-5 rounded-xl border border-slate-700/60 shadow-lg backdrop-blur">
          <div className="flex justify-between items-center text-slate-400 text-xs mb-2">
            <span>Grid Import (latest slot)</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">
            {liveMarket.grid_import_kwh ?? "—"} <span className="text-xs font-normal text-slate-400">kWh</span>
          </div>
        </div>

        <div className="bg-slate-800/60 p-5 rounded-xl border border-slate-700/60 shadow-lg backdrop-blur">
          <div className="flex justify-between items-center text-slate-400 text-xs mb-2">
            <span>Active Prosumers</span>
            <Users className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-300">
            {liveDevices.length || nodes.length} Nodes
          </div>
        </div>
      </div>

      {/* Chart and Order Book */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 bg-slate-800/60 p-6 rounded-xl border border-slate-700/60 shadow-lg backdrop-blur">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
            <div>
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Activity className="text-amber-400 w-4 h-4" />
                24-Hour Telemetry (simulated curve)
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-4 mb-4 bg-slate-900/50 p-3 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="flex items-center gap-1.5 px-3 py-1 rounded bg-amber-500 text-slate-950 font-bold hover:bg-amber-400 transition"
            >
              {isPlaying ? 'Pause' : 'Auto Step 24h'}
            </button>
            <span className="text-slate-400">Slot: <strong className="text-amber-400">{currentSlotData.hour}</strong></span>
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
                <XAxis dataKey="hour" stroke="#94A3B8" />
                <YAxis stroke="#94A3B8" />
                <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', color: '#F8FAFC' }} />
                <ReferenceLine 
                  x={currentSlotData.hour} 
                  stroke="#F59E0B" 
                  strokeDasharray="3 3" 
                  strokeWidth={2} 
                />
                <Area type="monotone" dataKey="solar_pv" name="Solar PV Output (kW)" stroke="#F59E0B" fillOpacity={1} fill="url(#colorSolar)" strokeWidth={2} />
                <Area type="monotone" dataKey="load_demand" name="Demand Load (kW)" stroke="#06B6D4" fillOpacity={1} fill="url(#colorLoad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-slate-800/60 p-6 rounded-xl border border-slate-700/60 shadow-lg backdrop-blur">
          <h2 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
            <Activity className="text-cyan-400 w-4 h-4" />
            ASTRA Market Order Book
          </h2>
          <p className="text-xs text-slate-400 mb-4">Slot #{activeSlot} ({currentSlotData.hour})</p>

          <div className="space-y-3 text-xs max-h-80 overflow-y-auto pr-1">
            {nodes.map((node) => {
              const isSelf = currentUser.id === node.id;
              const pref = isSelf ? activeUserPref : (nodePreferences[node.id] || { strategy: 'auto', maxSellPrice: 3.50 });
              
              const isDaytime = activeSlot >= 6 && activeSlot <= 18;
              const currentSolar = isDaytime ? Math.max(0, node.solarCap * Math.sin((Math.PI * (activeSlot - 6)) / 12)).toFixed(1) : '0.0';
              const isSeller = parseFloat(currentSolar) > 1.5 || pref.strategy === 'force_sell';
              const displayPrice = (pref.maxSellPrice || (isSeller ? 3.50 : 3.80)).toFixed(2);

              return (
                <div
                  key={node.id}
                  className={`p-3 rounded-lg border ${
                    isSelf
                      ? isSeller
                        ? 'bg-amber-950/60 border-amber-400'
                        : 'bg-cyan-950/60 border-cyan-400'
                      : 'bg-slate-900/60 border-slate-700'
                  }`}
                >
                  <div className="flex justify-between items-center mb-1">
                    <span className={`font-semibold ${isSeller ? 'text-amber-400' : 'text-cyan-400'}`}>
                      {node.name} {isSelf && '(You)'}
                    </span>
                    <span className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
                      {isSeller ? `ASK: ₹${displayPrice}` : `BID: ₹${displayPrice}`}
                    </span>
                  </div>
                  <span className="text-slate-400">
                    {isSeller ? `Surplus: ${currentSolar} kW` : `Deficit: ${(node.batCap * 0.2).toFixed(1)} kW`}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-slate-800/60 p-6 rounded-xl border border-slate-700/60 shadow-lg backdrop-blur">
        <h2 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
          <ShieldCheck className="text-cyan-400 w-4 h-4" />
          On-Chain Settlement Audit Feed{ledgerSim ? ' (sample data, no chain connected)' : ''}
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
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
              {ledgerLogs.map((tx, idx) => (
                <tr key={tx.hash || idx} className="border-b border-slate-700/50 hover:bg-slate-800/40 transition">
                  <td className="py-3 px-3 font-semibold text-cyan-400">#{tx.block}</td>
                  <td className="py-3 px-3 font-mono text-slate-400">{tx.hash.substring(0, 24)}...</td>
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