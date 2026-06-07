import React, { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { usePipelineEvents } from '../hooks/usePipelineEvents';
import { Activity, CheckCircle2 } from 'lucide-react';
import { sendTelegramMessage } from '../services/telegram';

export function EventsPage() {
  const { events, isConnected } = usePipelineEvents('ws://dev-be-y3xjsd-eb65f5-18-207-163-209.sslip.io/api/v1/ws/events');
  const processedMatches = useRef(new Set());

  // Monitor for MATCH_FOUND events to trigger Telegram message
  useEffect(() => {
    if (events.length > 0) {
      const latestEvent = events[events.length - 1];

      if (latestEvent.event === 'MATCH_FOUND') {
        const matchId = latestEvent.data.match_id || latestEvent.data.request_id;
        if (matchId && !processedMatches.current.has(matchId)) {
          processedMatches.current.add(matchId);

          const donorId = latestEvent.data.donor_id;
          const msg = `🚨 URGENT: Blood match found! 🚨\n\nA patient needs your help. You have been matched as a potential donor. Please reply YES to accept or NO to decline.`;

          sendTelegramMessage(msg).catch(console.error);
        }
      }
    }
  }, [events]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-ink)]">Pipeline Events</h1>
          <p className="text-[var(--color-ash)] mt-1">Real-time matching pipeline log.</p>
        </div>
        <div className="flex items-center gap-2 bg-[var(--color-surface-card)] px-4 py-2 rounded-full border border-[var(--color-hairline)] shadow-sm">
          <span className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
          <span className="font-sans text-[13px] font-bold tracking-wide text-[var(--color-ink)]">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      <div className="bg-[var(--color-canvas)] border border-[var(--color-hairline)] rounded-2xl h-[600px] overflow-y-auto p-4 flex flex-col gap-4 shadow-sm">
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-[var(--color-ash)]">
            <Activity className="w-12 h-12 mb-4 text-gray-300" />
            <p className="font-sans text-[14px]">Waiting for events...</p>
          </div>
        ) : (
          events.map((ev, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="border border-[var(--color-hairline)] rounded-xl p-4 bg-[var(--color-surface-card)] shadow-sm"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="font-sans text-[12px] font-bold tracking-wide text-white bg-[var(--color-ink)] px-3 py-1 rounded-full">
                  {ev.event}
                </span>
                <span className="text-xs text-[var(--color-ash)]">
                  {new Date().toLocaleTimeString()}
                </span>
              </div>
              <div className="font-sans text-[14px] text-[var(--color-body)] break-words">
                <pre className="whitespace-pre-wrap font-mono text-[12px] bg-white border border-[var(--color-hairline)] rounded-lg p-3 mt-2 overflow-x-auto">
                  {JSON.stringify(ev.data, null, 2)}
                </pre>
              </div>
              {ev.event === 'MATCH_FOUND' && (
                <div className="mt-3 text-[13px] font-bold text-green-600 font-sans flex items-center gap-1">
                  <CheckCircle2 className="w-4 h-4" /> Telegram Notification Dispatched
                </div>
              )}
            </motion.div>
          ))
        )}
      </div>
    </motion.div>
  );
}
