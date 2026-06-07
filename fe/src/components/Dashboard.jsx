import React, { useState, useEffect, useMemo } from 'react';
import { getDonors, getPatients, getStats } from '../api';
import { usePipelineEvents } from '../hooks/usePipelineEvents';
import { MapDashboard } from './MapDashboard';
import { UserDetailsModal } from './UserDetailsModal';
import { Activity, Users, HeartPulse, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';

export function Dashboard() {
  const [donors, setDonors] = useState([]);
  const [patients, setPatients] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [bloodFilter, setBloodFilter] = useState('ALL');
  const [stats, setStats] = useState({ totalDonors: 0, totalPatients: 0, successRate: 0, ratio: 0, bgCounts: {} });

  // Pipeline Events WebSocket
  const { events, isConnected } = usePipelineEvents('ws://dev-be-y3xjsd-eb65f5-18-207-163-209.sslip.io/api/v1/ws/events');

  // Extract active matching state from events
  const { activePatientId, activeMatches } = useMemo(() => {
    let pId = null;
    let m = [];
    if (events.length > 0) {
      const latest = events[events.length - 1];
      if (latest.event === 'MATCH_EVALUATING') {
        pId = latest.data.request_id;
        // Assume event data contains donor ids being evaluated, if not we just use mock
        m = (latest.data.potential_donors || []).map(d => ({ donor_id: d, status: 'evaluating' }));
      } else if (latest.event === 'MATCH_FOUND') {
        pId = latest.data.match_id || latest.data.request_id; // Sometimes it's request_id
        m = [{ donor_id: latest.data.donor_id, status: 'selected' }];
      }
    }
    return { activePatientId: pId, activeMatches: m };
  }, [events]);

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    fetchStats();
  }, [bloodFilter]);

  const fetchUsers = async () => {
    try {
      const [donorsData, patientsData] = await Promise.all([
        getDonors(0, 100),
        getPatients(0, 100)
      ]);
      setDonors(donorsData);
      setPatients(patientsData);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchStats = async () => {
    try {
      const statsData = await getStats(bloodFilter);
      // Only update if bgCounts are not empty to preserve buttons during loading/errors
      setStats(prev => ({
        ...statsData,
        bgCounts: Object.keys(statsData.bgCounts).length > 0 ? statsData.bgCounts : prev.bgCounts
      }));
    } catch (err) {
      console.error(err);
    }
  };

  const filteredDonors = useMemo(() => {
    if (bloodFilter === 'ALL') return donors;
    return donors.filter(d => d.blood_group === bloodFilter);
  }, [donors, bloodFilter]);

  const filteredPatients = useMemo(() => {
    if (bloodFilter === 'ALL') return patients;
    return patients.filter(p => p.blood_group === bloodFilter);
  }, [patients, bloodFilter]);

  const StatCard = ({ title, value, icon: Icon, delay }) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="bg-blue-50/80 backdrop-blur-sm border border-blue-200 p-6 rounded-2xl shadow-sm flex items-center gap-4 hover:shadow-md transition-shadow relative overflow-hidden"
    >
      {/* Decorative gradient blob inside card */}
      <div className="absolute -right-4 -top-4 w-24 h-24 bg-blue-400/10 rounded-full blur-xl pointer-events-none"></div>

      <div className="bg-red-50 p-3 rounded-full shadow-sm relative z-10">
        <Icon className="text-[var(--color-primary)] w-6 h-6" />
      </div>
      <div className="relative z-10">
        <div className="text-blue-800/70 text-sm font-semibold">{title}</div>
        <div className="text-2xl font-bold text-blue-900">{value}</div>
      </div>
    </motion.div>
  );

  return (
    <div className="space-y-6 relative">
      {/* Background Blood Drop Watermark */}
      <div className="fixed inset-0 flex items-center justify-center pointer-events-none z-[-1] overflow-hidden">
        <svg viewBox="0 0 24 24" fill="currentColor" className="text-red-600 opacity-[0.08] w-[120vh] h-[120vh] min-w-[700px] min-h-[700px] -translate-y-32">
          <path d="M12 2C12 2 4 9.9 4 15.4C4 19.8 7.6 23.4 12 23.4C16.4 23.4 20 19.8 20 15.4C20 9.9 12 2 12 2Z" />
        </svg>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard title="Total Donors" value={stats.totalDonors} icon={Users} delay={0.1} />
        <StatCard title="Active Requests" value={stats.totalPatients} icon={Activity} delay={0.2} />
        <StatCard title="Donor:Patient Ratio" value={`${stats.ratio}:1`} icon={HeartPulse} delay={0.3} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map Section */}
        <div className="lg:col-span-2 bg-[var(--color-surface-card)] border border-[var(--color-hairline)] rounded-2xl shadow-sm overflow-hidden flex flex-col h-[500px]">
          <div className="p-4 border-b border-[var(--color-hairline)] flex justify-between items-center bg-white z-10 relative">
            <div>
              <h2 className="text-lg font-bold text-[var(--color-ink)]">Live Distribution Map</h2>
              <p className="text-sm text-[var(--color-ash)]">Geographic tracking and real-time matching.</p>
            </div>
            <div className="flex items-center gap-2 bg-gray-50 px-3 py-1.5 rounded-full border border-gray-100">
              <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
              <span className="text-xs font-semibold text-gray-700">{isConnected ? 'Pipeline Live' : 'Offline'}</span>
            </div>
          </div>
          <div className="flex-1 relative">
            <MapDashboard
              donors={filteredDonors}
              patients={filteredPatients}
              activePatientId={activePatientId}
              activeMatches={activeMatches}
              onUserClick={setSelectedUser}
            />
          </div>
        </div>

        {/* Filter Section */}
        <div className="bg-[var(--color-surface-card)] border border-[var(--color-hairline)] rounded-2xl shadow-sm overflow-hidden flex flex-col h-[500px]">
          <div className="p-4 border-b border-[var(--color-hairline)] bg-white z-10 relative">
            <h2 className="text-lg font-bold text-[var(--color-ink)]">Blood Group Filter</h2>
            <p className="text-sm text-[var(--color-ash)]">Filter donors visible on the map.</p>
          </div>
          <div className="flex-1 bg-gradient-to-b from-gray-50 to-white relative p-6 overflow-y-auto">
            {/* Background Watermark for Filter */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-0 overflow-hidden">
              <svg viewBox="0 0 24 24" fill="currentColor" className="text-red-600 opacity-[0.05] w-[300px] h-[300px]">
                <path d="M12 2C12 2 4 9.9 4 15.4C4 19.8 7.6 23.4 12 23.4C16.4 23.4 20 19.8 20 15.4C20 9.9 12 2 12 2Z" />
              </svg>
            </div>

            <div className="grid grid-cols-2 gap-3 relative z-10">
              <button
                onClick={() => setBloodFilter('ALL')}
                className={`py-3 px-4 rounded-xl font-bold transition-all ${bloodFilter === 'ALL'
                    ? 'bg-[var(--color-ink)] text-white shadow-md'
                    : 'bg-white text-[var(--color-ink)] border border-[var(--color-hairline)] hover:border-gray-300 hover:shadow-sm'
                  }`}
              >
                ALL
              </button>
              {Object.entries(stats.bgCounts).sort((a, b) => b[1] - a[1]).map(([bg, count]) => (
                <button
                  key={bg}
                  onClick={() => setBloodFilter(bg)}
                  className={`py-3 px-4 rounded-xl font-bold transition-all flex justify-between items-center ${bloodFilter === bg
                      ? 'bg-[var(--color-primary)] text-white shadow-md'
                      : 'bg-white text-[var(--color-ink)] border border-[var(--color-hairline)] hover:border-gray-300 hover:shadow-sm'
                    }`}
                >
                  <span>{bg}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${bloodFilter === bg ? 'bg-white/20' : 'bg-gray-100 text-gray-500'}`}>
                    {count}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <UserDetailsModal user={selectedUser} onClose={() => setSelectedUser(null)} />
    </div>
  );
}
