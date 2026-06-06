import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { createPatient, triggerMatch } from '../api';
import toast, { Toaster } from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';

export function TestPage() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleTestEvent = async () => {
    setLoading(true);
    try {
      // Create a mock critical patient request to test
      const patient = await createPatient({
        name: `Test Patient ${Math.floor(Math.random()*1000)}`,
        blood_group: 'O-',
        urgency: 'CRITICAL',
        hospital: 'Test Hospital',
        latitude: 12.9716 + (Math.random() - 0.5) * 0.1,
        longitude: 77.5946 + (Math.random() - 0.5) * 0.1,
        gender: 'M',
        expected_next_transfusion_date: new Date(Date.now() + 86400000).toISOString()
      });
      
      // Trigger the new single match flow
      toast.success('Patient created, triggering match...');
      await triggerMatch(patient.id);
      
      toast.success('Pipeline Triggered! Redirecting to Dashboard to view matching...');
      setTimeout(() => navigate('/dashboard'), 2000);
    } catch (err) {
      toast.error('Failed to trigger test event');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-2xl mx-auto space-y-6 text-center"
    >
      <Toaster position="top-right" />
      <div>
        <h1 className="text-3xl font-bold text-[var(--color-ink)]">Pipeline Testing</h1>
        <p className="text-[var(--color-ash)] mt-2">Trigger a mock patient request to test the matching pipeline and Telegram integration.</p>
      </div>

      <div className="bg-[var(--color-surface-card)] border border-[var(--color-hairline)] rounded-2xl p-10 shadow-sm flex flex-col items-center gap-6">
        <p className="text-[var(--color-body)]">Clicking the button below will create a mock critical patient request in Bangalore (around 12.97, 77.59) for O- blood. This will automatically trigger the ILP matching service, dispatch WebSocket events to the frontend, and eventually trigger a Telegram notification when a match is found.</p>
        
        <button 
          onClick={handleTestEvent}
          disabled={loading}
          className="bg-purple-600 text-white font-bold py-4 px-8 rounded-xl hover:bg-purple-700 transition-colors disabled:opacity-50 text-lg shadow-md hover:shadow-lg"
        >
          {loading ? 'Triggering Pipeline...' : 'Trigger Match Pipeline'}
        </button>
      </div>
    </motion.div>
  );
}
