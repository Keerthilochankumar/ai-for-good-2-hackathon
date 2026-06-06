import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Skeleton from 'react-loading-skeleton';
import 'react-loading-skeleton/dist/skeleton.css';
import { DataTable, TableCell } from './DataTable';
import { getPatients, getMatches, triggerMatch, lockMatch } from '../api';
import { usePipelineEvents } from '../hooks/usePipelineEvents';
import { Loader2, Heart, MapPin, X, User, Phone, CheckCircle2, Play } from 'lucide-react';
import toast from 'react-hot-toast';

export function PatientsPage() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [patientMatches, setPatientMatches] = useState([]);
  const [loadingMatches, setLoadingMatches] = useState(false);
  const [lockingDonorId, setLockingDonorId] = useState(null);

  const { events } = usePipelineEvents();

  const activePatientId = useMemo(() => {
    if (events.length > 0) {
      const latest = events[events.length - 1];
      if (latest.event === 'MATCH_EVALUATING' || latest.event === 'MATCH_FOUND') {
        return latest.data.request_id || latest.data.match_id;
      }
    }
    return null;
  }, [events]);

  useEffect(() => {
    fetchPatients();
  }, []);

  const fetchPatients = async () => {
    try {
      const data = await getPatients(0, 100);
      data.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
      setPatients(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRowClick = async (patient) => {
    setSelectedPatient(patient);
    setLoadingMatches(true);
    try {
      const matches = await getMatches(patient.id);
      setPatientMatches(matches);
    } catch (err) {
      console.error('Failed to fetch matches', err);
    } finally {
      setLoadingMatches(false);
    }
  };

  const handleTriggerMatch = async (e, patient) => {
    e.stopPropagation();
    try {
      toast.success("Pipeline started for " + patient.patient_name);
      await triggerMatch(patient.id);
      setSelectedPatient(patient);
      setLoadingMatches(true);
      // It might take time to find matches, so we could just show loading or open the modal.
      // The websocket will update the pipeline status.
      // Just poll or wait for MATCH_FOUND event. But for now, we'll open the modal.
      setTimeout(async () => {
        const matches = await getMatches(patient.id);
        setPatientMatches(matches);
        setLoadingMatches(false);
      }, 5000); // Wait 5s for demo before fetching
    } catch(err) {
      toast.error("Failed to start pipeline");
      setLoadingMatches(false);
    }
  };

  const handleLockMatch = async (donorId) => {
    setLockingDonorId(donorId);
    try {
      await lockMatch(selectedPatient.id, donorId);
      toast.success("Donor locked and matched successfully!");
      await fetchPatients(); // refresh patient list
      setSelectedPatient(null);
    } catch (err) {
      toast.error("Failed to lock donor.");
    } finally {
      setLockingDonorId(null);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6 relative"
    >
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-ink)]">Active Requests</h1>
          <p className="text-[var(--color-ash)] mt-1">Manage blood requests and trigger matches manually.</p>
        </div>
      </div>

      <div className="bg-[var(--color-surface-card)] rounded-2xl overflow-hidden border border-[var(--color-hairline)] shadow-sm">
        {loading ? (
          <div className="p-6 space-y-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} height={40} className="rounded-xl" />
            ))}
          </div>
        ) : (
          <DataTable 
            headers={['Name', 'Blood Group', 'Urgency', 'Hospital', 'Status', 'Actions']}
            rows={patients}
            renderRow={(patient) => {
              const isPipelineActive = patient.id === activePatientId;
              return (
                <tr 
                  key={patient.id} 
                  onClick={() => handleRowClick(patient)}
                  className="border-b border-[var(--color-hairline)] hover:bg-[var(--color-surface-soft)] cursor-pointer transition-colors"
                >
                  <TableCell className="font-semibold">{patient.patient_name}</TableCell>
                  <TableCell>
                    <span className="bg-[var(--color-primary)] text-white text-xs px-2 py-1 rounded-[var(--radius-md)] font-bold">{patient.blood_group}</span>
                  </TableCell>
                  <TableCell>{patient.urgency}</TableCell>
                  <TableCell>{patient.hospital_name}</TableCell>
                  <TableCell>
                    {isPipelineActive ? (
                      <span className="flex items-center gap-2 px-2 py-1 text-xs font-bold rounded-full bg-blue-100 text-blue-700 w-max">
                        <Loader2 size={12} className="animate-spin" /> Matching...
                      </span>
                    ) : (
                      <span className={`px-2 py-1 text-xs font-bold rounded-full w-max ${patient.status === 'FULFILLED' ? 'bg-green-100 text-green-700' : (patient.status === 'MATCHING' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-700')}`}>
                        {patient.status}
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    {patient.status === 'OPEN' && !isPipelineActive && (
                       <button 
                        onClick={(e) => handleTriggerMatch(e, patient)}
                        className="flex items-center gap-1 bg-[var(--color-ink)] hover:bg-gray-800 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-md hover:shadow-lg"
                       >
                         <Play size={12} fill="currentColor" /> Find Match
                       </button>
                    )}
                  </TableCell>
                </tr>
              );
            }}
          />
        )}
      </div>

      {/* Matches Modal */}
      <AnimatePresence>
        {selectedPatient && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black z-[100]"
              onClick={() => setSelectedPatient(null)}
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed top-0 right-0 h-full w-full max-w-lg bg-[var(--color-surface)] shadow-2xl z-[101] overflow-y-auto"
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-2xl font-bold text-[var(--color-ink)] flex items-center gap-2">
                    <Heart className="text-[var(--color-primary)]" />
                    Available Donors
                  </h2>
                  <button onClick={() => setSelectedPatient(null)} className="p-2 hover:bg-[var(--color-surface-card)] rounded-full transition-colors">
                    <X size={24} className="text-[var(--color-ink)]" />
                  </button>
                </div>
                <p className="text-[var(--color-ash)] text-sm mb-6 pb-4 border-b border-[var(--color-hairline)]">
                  Showing matches for <strong className="text-[var(--color-ink)]">{selectedPatient.patient_name}</strong> at {selectedPatient.hospital_name}.
                </p>

                {loadingMatches || (selectedPatient.id === activePatientId && patientMatches.length === 0) ? (
                  <div className="flex flex-col justify-center items-center h-48 space-y-4">
                    <Loader2 size={40} className="animate-spin text-[var(--color-primary)]" />
                    <p className="text-[var(--color-ash)] font-medium">Running Optimization Pipeline...</p>
                  </div>
                ) : patientMatches.length > 0 ? (
                  <div className="space-y-4">
                    {patientMatches.map((match, idx) => (
                      <motion.div 
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        key={idx} 
                        className="bg-white border border-[var(--color-hairline)] shadow-sm hover:shadow-md transition-shadow p-5 rounded-2xl relative overflow-hidden"
                      >
                        <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-green-50 to-transparent rounded-bl-full z-0" />
                        
                        <div className="flex justify-between items-start mb-3 relative z-10">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center text-gray-500">
                              <User size={20} />
                            </div>
                            <div>
                              <h3 className="font-bold text-[var(--color-ink)] text-lg">{match.donor_name}</h3>
                              <div className="flex items-center gap-1 text-sm text-[var(--color-ash)]">
                                <MapPin size={14} className="text-gray-400" /> {match.distance_km} km away
                              </div>
                            </div>
                          </div>
                          <span className="bg-[var(--color-primary)] text-white px-3 py-1 rounded-full font-bold shadow-sm flex items-center gap-1">
                            <DropletIcon size={14} fill="currentColor" /> {match.blood_group}
                          </span>
                        </div>
                        
                        {match.llm_reasoning && (
                          <div className="text-sm bg-blue-50/50 border border-blue-100 text-blue-800 p-3 rounded-xl mt-3 mb-4 leading-relaxed relative z-10">
                            <strong>AI Match Reason:</strong> {match.llm_reasoning}
                          </div>
                        )}
                        
                        {selectedPatient.status !== 'FULFILLED' ? (
                          <button 
                            onClick={() => handleLockMatch(match.donor_id)}
                            disabled={lockingDonorId === match.donor_id}
                            className="w-full relative z-10 flex items-center justify-center gap-2 bg-green-500 hover:bg-green-600 active:bg-green-700 text-white font-bold py-3 px-4 rounded-xl transition-all shadow-[0_4px_14px_0_rgba(34,197,94,0.39)] hover:shadow-[0_6px_20px_rgba(34,197,94,0.23)] disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {lockingDonorId === match.donor_id ? (
                              <Loader2 size={18} className="animate-spin" />
                            ) : (
                              <>
                                <Phone size={18} /> Contact & Lock Donor
                              </>
                            )}
                          </button>
                        ) : (
                          <div className="w-full relative z-10 flex items-center justify-center gap-2 bg-gray-100 text-gray-500 font-bold py-3 px-4 rounded-xl">
                            <CheckCircle2 size={18} /> Patient Fulfilled
                          </div>
                        )}
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center bg-gray-50 rounded-2xl p-10 border border-dashed border-gray-200">
                    <Heart className="text-gray-300 mx-auto mb-3" size={40} />
                    <p className="text-gray-500 font-medium">No donors matched yet.</p>
                    <p className="text-gray-400 text-sm mt-1">Try triggering a match if the request is OPEN.</p>
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function DropletIcon(props) {
  return (
    <svg 
      {...props} 
      xmlns="http://www.w3.org/2000/svg" 
      viewBox="0 0 24 24" 
      fill="currentColor" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round"
    >
      <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
    </svg>
  );
}
