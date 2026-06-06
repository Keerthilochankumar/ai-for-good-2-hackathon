import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { createPatient } from '../api';
import { useNavigate } from 'react-router-dom';
import toast, { Toaster } from 'react-hot-toast';

export function AddPatient() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    blood_group: 'A+',
    urgency: 'high',
    hospital: '',
    latitude: '',
    longitude: ''
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await createPatient({
        ...formData,
        latitude: parseFloat(formData.latitude),
        longitude: parseFloat(formData.longitude)
      });
      toast.success('Patient request added! Pipeline will start matching automatically.');
      setTimeout(() => navigate('/patients'), 2000);
    } catch (err) {
      toast.error('Failed to add patient');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-2xl mx-auto space-y-6"
    >
      <Toaster position="top-right" />
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-ink)]">Add Patient Request</h1>
        <p className="text-[var(--color-ash)] mt-1">Register a patient in need of blood. This will trigger the matching pipeline.</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-[var(--color-surface-card)] border border-[var(--color-hairline)] rounded-2xl p-6 shadow-sm space-y-4">
        <div>
          <label className="block text-sm font-semibold text-[var(--color-ink)] mb-1">Patient Name</label>
          <input required type="text" className="w-full px-4 py-2 rounded-xl border border-[var(--color-hairline)] focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-all" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-semibold text-[var(--color-ink)] mb-1">Blood Group</label>
            <select required className="w-full px-4 py-2 rounded-xl border border-[var(--color-hairline)] focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-all" value={formData.blood_group} onChange={e => setFormData({...formData, blood_group: e.target.value})}>
              {['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].map(bg => <option key={bg} value={bg}>{bg}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold text-[var(--color-ink)] mb-1">Urgency</label>
            <select required className="w-full px-4 py-2 rounded-xl border border-[var(--color-hairline)] focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-all" value={formData.urgency} onChange={e => setFormData({...formData, urgency: e.target.value})}>
              {['low', 'medium', 'high', 'critical'].map(u => <option key={u} value={u}>{u.toUpperCase()}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="block text-sm font-semibold text-[var(--color-ink)] mb-1">Hospital Name</label>
          <input required type="text" className="w-full px-4 py-2 rounded-xl border border-[var(--color-hairline)] focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-all" value={formData.hospital} onChange={e => setFormData({...formData, hospital: e.target.value})} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-semibold text-[var(--color-ink)] mb-1">Hospital Latitude</label>
            <input required type="number" step="any" className="w-full px-4 py-2 rounded-xl border border-[var(--color-hairline)] focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-all" value={formData.latitude} onChange={e => setFormData({...formData, latitude: e.target.value})} />
          </div>
          <div>
            <label className="block text-sm font-semibold text-[var(--color-ink)] mb-1">Hospital Longitude</label>
            <input required type="number" step="any" className="w-full px-4 py-2 rounded-xl border border-[var(--color-hairline)] focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-all" value={formData.longitude} onChange={e => setFormData({...formData, longitude: e.target.value})} />
          </div>
        </div>
        
        <button disabled={loading} type="submit" className="w-full bg-[var(--color-primary)] text-white font-bold py-3 px-4 rounded-xl hover:bg-red-700 transition-colors disabled:opacity-50 mt-4">
          {loading ? 'Adding & Matching...' : 'Add Patient & Find Matches'}
        </button>
      </form>
    </motion.div>
  );
}
