import React, { useState, useEffect, useRef, useCallback } from 'react'
import { createClient } from '@supabase/supabase-js'
import { 
  Database, RefreshCw, Check, ChevronRight, ChevronDown, Plus, 
  Wifi, WifiOff, Clock, Settings, Timer, Zap, Hand
} from 'lucide-react'

const SUPABASE_URL='https://eldrdyjuqubqkoeyzwep.supabase.co'
const SUPABASE_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVsZHJkeWp1cXVicWtvZXl6d2VwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMyMjMxNzMsImV4cCI6MjA3ODc5OTE3M30.nh3uU7xp0SbzresOjj5YTaFlKzPWB2srzW-sdPXDKaQ'
const API_URL = 'http://127.0.0.1:8000'

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

function App() {
  const [bomTree, setBomTree] = useState([])
  const [sage100Articles, setSage100Articles] = useState([])
  const [syncHistory, setSyncHistory] = useState([])
  const [assemblies, setAssemblies] = useState([])
  
  const [syncStatus, setSyncStatus] = useState('idle')
  const [syncResult, setSyncResult] = useState(null)
  const [syncLog, setSyncLog] = useState([])
  const [realtimeConnected, setRealtimeConnected] = useState(false)
  const [expandedNodes, setExpandedNodes] = useState(new Set())
  const [activeTab, setActiveTab] = useState('tree')
  const [showSettings, setShowSettings] = useState(false)
  
  // Sync Mode Configuration
  const [syncMode, setSyncMode] = useState('scheduler') // 'live', 'scheduler', 'manual'
  const [schedulerInterval, setSchedulerInterval] = useState(60) // seconds
  const [nextSyncIn, setNextSyncIn] = useState(0)
  
  // Form
  const [newComponent, setNewComponent] = useState({
    assembly_id: '', part_number: '', description: '',
    quantity: 1, unit_price: 0, supplier: ''
  })

  const logRef = useRef(null)
  const schedulerRef = useRef(null)
  const countdownRef = useRef(null)

  // ================================================================
  // LOGGING
  // ================================================================
  const addLog = useCallback((message, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString()
    setSyncLog(prev => [...prev.slice(-100), { timestamp, message, type }])
  }, [])

  // ================================================================
  // API CALLS
  // ================================================================
  const fetchBomTree = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/bom/tree`)
      if (!res.ok) throw new Error('Backend not reachable')
      const data = await res.json()
      setBomTree(data.tree || [])
      return data.tree || []
    } catch (err) {
      addLog(`ERROR: ${err.message}`, 'error')
      return []
    }
  }, [addLog])

  const fetchSage100 = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/sage100/articles`)
      if (!res.ok) return []
      const data = await res.json()
      setSage100Articles(data.articles || [])
      return data.articles || []
    } catch (err) {
      console.error(err)
      return []
    }
  }, [])

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/sync/history`)
      if (!res.ok) return
      const data = await res.json()
      setSyncHistory(data.history || [])
    } catch (err) {
      console.error(err)
    }
  }, [])

  const fetchAssemblies = useCallback(async () => {
    try {
      const { data } = await supabase
        .from('bom_assemblies')
        .select('id, part_number, description, bom_level')
        .order('bom_level')
      setAssemblies(data || [])
    } catch (err) {
      console.error(err)
    }
  }, [])

  // ================================================================
  // MAIN SYNC FUNCTION
  // ================================================================
  const runSync = useCallback(async (source = 'manual') => {
    if (syncStatus === 'syncing') {
      addLog('Sync already in progress...', 'warning')
      return
    }

    setSyncStatus('syncing')
    addLog('', 'info')
    addLog('         ╔════════════════════════════════════════════════════╗', 'info')
    addLog(`         ║  ETL SYNC (Triggered by: ${source.toUpperCase()})  ║` ,'info')
    addLog('         ╚════════════════════════════════════════════════════╝', 'info')

    try {
      const res = await fetch(`${API_URL}/api/sync`, { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      
      const result = await res.json()
      setSyncResult(result)

      addLog(`EXTRACT: ${result.total_parts} parts from S1000D`, 'info')
      addLog(`TRANSFORM: Validation complete`, 'info')
      addLog(`LOAD: ${result.inserted} inserted, ${result.updated} updated`, 'success')
      
      if (result.errors > 0) {
        addLog(`ERRORS: ${result.errors} failed`, 'error')
      }
      
      addLog(`TIME: ${result.duration_seconds.toFixed(3)}s`, 'info')
      addLog('════════════════════════════════════════════', 'info')

      setSyncStatus('success')
      
      // Refresh UI data
      await fetchBomTree()
      await fetchSage100()
      await fetchHistory()
      
      setTimeout(() => setSyncStatus('idle'), 2000)

    } catch (err) {
      addLog(`SYNC FAILED: ${err.message}`, 'error')
      setSyncStatus('error')
      setTimeout(() => setSyncStatus('idle'), 3000)
    }
  }, [syncStatus, addLog, fetchBomTree, fetchSage100, fetchHistory])

  // ================================================================
  // SCHEDULER MODE - Run sync based on selected seconds
  // ================================================================
  useEffect(() => {
    // Clear existing scheduler
    if (schedulerRef.current) {
      clearInterval(schedulerRef.current)
      schedulerRef.current = null
    }
    if (countdownRef.current) {
      clearInterval(countdownRef.current)
      countdownRef.current = null
    }

    if (syncMode === 'scheduler') {
      addLog(`SCHEDULER: Will sync every ${schedulerInterval} seconds`, 'info')
      setNextSyncIn(schedulerInterval)

      // Countdown timer
      countdownRef.current = setInterval(() => {
        setNextSyncIn(prev => {
          if (prev <= 1) return schedulerInterval
          return prev - 1
        })
      }, 1000)

      // Actual sync timer
      schedulerRef.current = setInterval(() => {
        addLog('SCHEDULER: Time to sync!', 'warning')
        runSync('scheduler')
        setNextSyncIn(schedulerInterval)
      }, schedulerInterval * 1000)
    }

    return () => {
      if (schedulerRef.current) clearInterval(schedulerRef.current)
      if (countdownRef.current) clearInterval(countdownRef.current)
    }
  }, [syncMode, schedulerInterval, runSync, addLog])

  // ================================================================
  // LIVE MODE - Supabase Realtime
  // ================================================================
  useEffect(() => {
    addLog('Connecting to Supabase Realtime...', 'info')

    const channel = supabase
      .channel('db-changes')
      .on('postgres_changes', 
        { event: '*', schema: 'public', table: 'bom_assemblies' },
        (payload) => {
          addLog(`REALTIME: ${payload.eventType} on bom_assemblies`, 'warning')
          if (syncMode === 'live') {
            addLog('LIVE MODE: Triggering immediate sync...', 'warning')
            runSync('realtime')
          } else {
            addLog(`Change detected (Mode: ${syncMode} - will sync on schedule/manual)`, 'info')
          }
          fetchBomTree()
          fetchAssemblies()
        }
      )
      .on('postgres_changes',
        { event: '*', schema: 'public', table: 'bom_components' },
        (payload) => {
          addLog(`REALTIME: ${payload.eventType} on bom_components`, 'warning')
          if (syncMode === 'live') {
            addLog('LIVE MODE: Triggering immediate sync...', 'warning')
            runSync('realtime')
          } else {
            addLog(`Change detected (Mode: ${syncMode} - will sync on schedule/manual)`, 'info')
          }
          fetchBomTree()
        }
      )
      .subscribe((status) => {
        console.log('Supabase Realtime status:', status)
        if (status === 'SUBSCRIBED') {
          setRealtimeConnected(true)
          addLog('✓ REALTIME: Connected to Supabase', 'success')
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
          setRealtimeConnected(false)
          addLog('✗ REALTIME: Connection failed', 'error')
        }
      })

    return () => {
      supabase.removeChannel(channel)
    }
  }, [syncMode, runSync, addLog, fetchBomTree, fetchAssemblies])

  // ================================================================
  // INITIAL LOAD - Sync on app start
  // ================================================================
  useEffect(() => {
    addLog('AVILUS BOM-ERP Sync System Starting...', 'info')
    addLog(`Mode: ${syncMode.toUpperCase()}`, 'info')
    
    // Load initial data
    const init = async () => {
      addLog('Loading initial data...', 'info')
      await fetchAssemblies()
      await fetchHistory()
      
      // Always sync on startup to ensure Sage100 is up-to-date
      addLog('Running initial sync to ensure ERP is current...', 'info')
      await runSync('startup')
    }
    
    init()
  }, []) // Only run once on mount

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [syncLog])

  // ================================================================
  // ADD COMPONENT to the SUpabase BOM
  // ================================================================
  const handleAddComponent = async () => {
    if (!newComponent.assembly_id || !newComponent.part_number || !newComponent.description) {
      addLog('ERROR: Fill all required fields (Assembly, Part#, Description)', 'error')
      return
    }

    addLog(`Adding component: ${newComponent.part_number}...`, 'info')

    try {
      const { error } = await supabase.from('bom_components').insert([{
        id: `COMP-${Date.now()}`,
        assembly_id: newComponent.assembly_id,
        part_number: newComponent.part_number,
        description: newComponent.description,
        quantity: newComponent.quantity,
        unit_price: newComponent.unit_price,
        supplier: newComponent.supplier
      }])

      if (error) throw error

      addLog(`✓ Added: ${newComponent.part_number}`, 'success')
      setNewComponent({
        assembly_id: '', part_number: '', description: '',
        quantity: 1, unit_price: 0, supplier: ''
      })

      // Realtime will trigger sync if in live mode
      // Otherwise, wait for scheduler or manual sync

    } catch (err) {
      addLog(`✗ Failed: ${err.message}`, 'error')
    }
  }

  // ================================================================
  // TREE RENDERING
  // ================================================================
  const toggleNode = (id) => {
    setExpandedNodes(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const expandAll = () => {
    const ids = new Set()
    const collect = (nodes) => nodes.forEach(n => {
      if (n.children?.length) { ids.add(n.id); collect(n.children) }
    })
    collect(bomTree)
    setExpandedNodes(ids)
  }

  const renderNode = (node, depth = 0) => (
    <div key={node.id}>
      <div
        className={`flex items-center py-2 px-3 border-b hover:bg-gray-50 cursor-pointer
          ${node.is_assembly ? 'bg-blue-50/50' : ''}`}
        style={{ paddingLeft: `${depth * 20 + 10}px` }}
        onClick={() => node.children?.length && toggleNode(node.id)}
      >
        <div className="w-5">
          {node.children?.length > 0 && (
            expandedNodes.has(node.id) ? <ChevronDown size={16} /> : <ChevronRight size={16} />
          )}
        </div>
        <div className={`w-3 h-3 rounded-full mr-2 ${node.is_assembly ? 'bg-blue-500' : 'bg-green-500'}`} />
        <div className="flex-1">
          <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded mr-2">{node.part_number}</span>
          <span className="text-sm text-gray-700">{node.description}</span>
        </div>
        <span className="text-xs text-gray-500 mr-2">L{node.bom_level}</span>
        {!node.is_assembly && <span className="text-xs font-semibold text-green-700">€{node.unit_price?.toFixed(2)}</span>}
      </div>
      {node.children?.length > 0 && expandedNodes.has(node.id) && node.children.map(c => renderNode(c, depth + 1))}
    </div>
  )

  // ================================================================
  // RENDER UI
  // ================================================================
  return (
    <div className="min-h-screen bg-gray-100">
      {/* HEADER */}
      <div className="bg-white shadow p-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold">AVILUS Drone BOM-ERP Synchronization</h1>
              <div className="flex items-center gap-4 mt-1">
                <span className="text-sm text-gray-600">
                  Mode: <strong className="text-blue-600">{syncMode.toUpperCase()}</strong>
                </span>
                {syncMode === 'scheduler' && (
                  <span className="text-sm bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
                    Next sync in: {nextSyncIn}s
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Realtime Status */}
              <div className={`flex items-center gap-1 px-2 py-1 rounded text-sm
                ${realtimeConnected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {realtimeConnected ? <Wifi size={16} /> : <WifiOff size={16} />}
                {realtimeConnected ? 'Connected' : 'Disconnected'}
              </div>

              {/* Sync Status */}
              {syncStatus === 'syncing' && (
                <div className="flex items-center bg-blue-100 text-blue-700 px-3 py-1 rounded">
                  <RefreshCw className="animate-spin mr-1" size={16} /> Syncing...
                </div>
              )}
              {syncStatus === 'success' && (
                <div className="flex items-center bg-green-100 text-green-700 px-3 py-1 rounded">
                  <Check className="mr-1" size={16} /> Done
                </div>
              )}

              {/* Settings */}
              <button onClick={() => setShowSettings(!showSettings)} className="p-2 bg-gray-100 rounded hover:bg-gray-200">
                <Settings size={18} />
              </button>

              {/* Manual Sync */}
              <button
                onClick={() => runSync('manual')}
                disabled={syncStatus === 'syncing'}
                className="flex items-center gap-1 bg-blue-600 text-white px-4 py-2 rounded font-medium hover:bg-blue-700 disabled:bg-gray-400"
              >
                <RefreshCw size={16} /> Sync Now
              </button>
            </div>
          </div>

          {/* SETTINGS PANEL */}
          {showSettings && (
            <div className="mt-4 p-4 bg-gray-50 rounded border">
              <h3 className="font-semibold mb-3">Sync Configuration</h3>
              <div className="grid grid-cols-3 gap-6">
                {/* Mode Selection */}
                <div>
                  <label className="block text-sm font-medium mb-2">Sync Mode</label>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="syncMode"
                        value="live"
                        checked={syncMode === 'live'}
                        onChange={e => setSyncMode(e.target.value)}
                      />
                      <Zap size={16} className="text-yellow-500" />
                      <span>Live (Instant on change)</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="syncMode"
                        value="scheduler"
                        checked={syncMode === 'scheduler'}
                        onChange={e => setSyncMode(e.target.value)}
                      />
                      <Timer size={16} className="text-blue-500" />
                      <span>Scheduler (Every X seconds)</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="syncMode"
                        value="manual"
                        checked={syncMode === 'manual'}
                        onChange={e => setSyncMode(e.target.value)}
                      />
                      <Hand size={16} className="text-gray-500" />
                      <span>Manual Only</span>
                    </label>
                  </div>
                </div>

                {/* Scheduler Interval */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Scheduler Interval: {schedulerInterval} seconds
                  </label>
                  <input
                    type="range"
                    min="10"
                    max="300"
                    step="10"
                    value={schedulerInterval}
                    onChange={e => setSchedulerInterval(parseInt(e.target.value))}
                    disabled={syncMode !== 'scheduler'}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>10s</span>
                    <span>1min</span>
                    <span>5min</span>
                  </div>
                </div>

                {/* Info */}
                <div className="text-sm text-gray-600">
                  <p className="font-medium mb-1">Mode Explanation:</p>
                  <ul className="space-y-1 text-xs">
                    <li><strong>Live:</strong> Syncs immediately when data changes (use for production)</li>
                    <li><strong>Scheduler:</strong> Syncs at regular intervals (use for development)</li>
                    <li><strong>Manual:</strong> Only syncs when you click button</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* STATS */}
      {syncResult && (
        <div className="bg-white border-b p-3">
          <div className="max-w-7xl mx-auto grid grid-cols-5 gap-4 text-center">
            <div><div className="font-bold">{syncResult.total_parts}</div><div className="text-xs text-gray-600">Total</div></div>
            <div><div className="font-bold text-green-600">{syncResult.inserted}</div><div className="text-xs text-gray-600">Inserted</div></div>
            <div><div className="font-bold text-blue-600">{syncResult.updated}</div><div className="text-xs text-gray-600">Updated</div></div>
            <div><div className="font-bold text-red-600">{syncResult.errors}</div><div className="text-xs text-gray-600">Errors</div></div>
            <div><div className="font-bold">{syncResult.duration_seconds?.toFixed(2)}s</div><div className="text-xs text-gray-600">Duration</div></div>
          </div>
        </div>
      )}

      {/* MAIN */}
      <div className="max-w-7xl mx-auto p-4 grid grid-cols-3 gap-4">
        {/* S1000D */}
        <div className="bg-white rounded shadow">
          <div className="p-3 border-b flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Database className="text-blue-600" size={18} />
              <h2 className="font-semibold text-sm">S1000D BOM (Supabase)</h2>
            </div>
            <button onClick={expandAll} className="text-xs text-blue-600">Expand</button>
          </div>
          
          <div className="flex border-b text-sm">
            <button
              onClick={() => setActiveTab('tree')}
              className={`px-3 py-2 ${activeTab === 'tree' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-600'}`}
            >Tree</button>
            <button
              onClick={() => setActiveTab('add')}
              className={`px-3 py-2 ${activeTab === 'add' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-600'}`}
            >+ Add</button>
          </div>

          <div className="h-[400px] overflow-auto">
            {activeTab === 'tree' ? (
              bomTree.length === 0 ? (
                <div className="p-4 text-center text-gray-500 text-sm">Loading...</div>
              ) : bomTree.map(root => renderNode(root))
            ) : (
              <div className="p-3 space-y-2">
                <select
                  value={newComponent.assembly_id}
                  onChange={e => setNewComponent({...newComponent, assembly_id: e.target.value})}
                  className="w-full border rounded p-2 text-sm"
                >
                  <option value="">Select Parent Assembly *</option>
                  {assemblies.map(a => (
                    <option key={a.id} value={a.id}>{'  '.repeat(a.bom_level)}{a.part_number}</option>
                  ))}
                </select>
                <input
                  placeholder="Part Number *"
                  value={newComponent.part_number}
                  onChange={e => setNewComponent({...newComponent, part_number: e.target.value})}
                  className="w-full border rounded p-2 text-sm"
                />
                <input
                  placeholder="Description *"
                  value={newComponent.description}
                  onChange={e => setNewComponent({...newComponent, description: e.target.value})}
                  className="w-full border rounded p-2 text-sm"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="number"
                    placeholder="Qty"
                    value={newComponent.quantity}
                    onChange={e => setNewComponent({...newComponent, quantity: parseInt(e.target.value) || 1})}
                    className="w-full border rounded p-2 text-sm"
                  />
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Price €"
                    value={newComponent.unit_price}
                    onChange={e => setNewComponent({...newComponent, unit_price: parseFloat(e.target.value) || 0})}
                    className="w-full border rounded p-2 text-sm"
                  />
                </div>
                <input
                  placeholder="Supplier"
                  value={newComponent.supplier}
                  onChange={e => setNewComponent({...newComponent, supplier: e.target.value})}
                  className="w-full border rounded p-2 text-sm"
                />
                <button
                  onClick={handleAddComponent}
                  className="w-full bg-green-600 text-white py-2 rounded text-sm font-medium hover:bg-green-700"
                >
                  <Plus size={16} className="inline mr-1" /> Add Component
                </button>
              </div>
            )}
          </div>
        </div>

        {/* LOG */}
        <div className="bg-white rounded shadow">
          <div className="p-3 border-b flex items-center gap-2">
            <RefreshCw className="text-purple-600" size={18} />
            <h2 className="font-semibold text-sm">ETL Pipeline Log</h2>
          </div>
          <div ref={logRef} className="h-[450px] overflow-auto p-2 bg-gray-900 text-xs font-mono">
            {syncLog.map((log, i) => (
              <div key={i} className="py-0.5">
                <span className="text-gray-500">[{log.timestamp}]</span>{' '}
                <span className={
                  log.type === 'success' ? 'text-green-400' :
                  log.type === 'error' ? 'text-red-400' :
                  log.type === 'warning' ? 'text-yellow-400' : 'text-gray-300'
                }>{log.message}</span>
              </div>
            ))}
          </div>
        </div>

        {/* SAGE 100 */}
        <div className="bg-white rounded shadow">
          <div className="p-3 border-b flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Database className="text-green-600" size={18} />
              <h2 className="font-semibold text-sm">Sage 100 ERP (SQLite)</h2>
            </div>
            <span className="text-xs text-gray-500">{sage100Articles.length} articles</span>
          </div>
          <div className="h-[450px] overflow-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="p-2 text-left">Part #</th>
                  <th className="p-2 text-left">Description</th>
                  <th className="p-2 text-right">Price</th>
                  <th className="p-2 text-center">Lv</th>
                </tr>
              </thead>
              <tbody>
                {sage100Articles.map((a, i) => (
                  <tr key={i} className="border-t">
                    <td className="p-2 font-mono">{a.article_number}</td>
                    <td className="p-2 truncate max-w-[100px]">{a.description}</td>
                    <td className="p-2 text-right">€{a.unit_price?.toFixed(2)}</td>
                    <td className="p-2 text-center">{a.bom_level}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* HISTORY */}
      <div className="max-w-7xl mx-auto px-4 pb-4">
        <div className="bg-white rounded shadow">
          <div className="p-3 border-b flex items-center gap-2">
            <Clock className="text-indigo-600" size={18} />
            <h2 className="font-semibold text-sm">Sync History</h2>
          </div>
          <div className="p-3 overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-gray-50">
                <tr>
                  <th className="p-2 text-left">Time</th>
                  <th className="p-2 text-center">Parts</th>
                  <th className="p-2 text-center">Inserted</th>
                  <th className="p-2 text-center">Updated</th>
                  <th className="p-2 text-center">Errors</th>
                  <th className="p-2 text-center">Duration</th>
                </tr>
              </thead>
              <tbody>
                {syncHistory.slice(0, 10).map((h, i) => (
                  <tr key={i} className="border-t">
                    <td className="p-2">{new Date(h.sync_timestamp).toLocaleString()}</td>
                    <td className="p-2 text-center">{h.total_parts}</td>
                    <td className="p-2 text-center text-green-600">{h.inserted}</td>
                    <td className="p-2 text-center text-blue-600">{h.updated}</td>
                    <td className="p-2 text-center text-red-600">{h.errors}</td>
                    <td className="p-2 text-center">{h.duration_seconds?.toFixed(2)}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App