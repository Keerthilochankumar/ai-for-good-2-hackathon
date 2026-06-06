import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, MapPin, User, Droplet, Phone } from 'lucide-react';
import { Button } from './Button';
import Map, { Marker } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';

export function UserDetailsModal({ user, onClose }) {
  if (!user) return null;

  const isDonor = user.type === 'donor';
  const name = isDonor ? user.name : user.patient_name;
  const bloodGroup = isDonor ? user.blood_group : (user.blood_group || user.blood_group_needed);

  return (
    <AnimatePresence>
      {user && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black z-[100]"
            onClick={onClose}
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 right-0 h-full w-full max-w-md bg-[var(--color-surface)] shadow-2xl z-[101] overflow-y-auto"
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-[var(--color-ink)] flex items-center gap-2">
                  <User className="text-[var(--color-primary)]" />
                  {name}
                </h2>
                <button onClick={onClose} className="p-2 hover:bg-[var(--color-surface-card)] rounded-full transition-colors">
                  <X size={24} className="text-[var(--color-ink)]" />
                </button>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-[var(--color-surface-card)] p-4 rounded-xl">
                  <div className="text-[var(--color-ash)] text-sm mb-1 flex items-center gap-1"><Droplet size={14}/> Blood Group</div>
                  <div className="text-xl font-bold text-[var(--color-primary)]">{bloodGroup}</div>
                </div>
                <div className="bg-[var(--color-surface-card)] p-4 rounded-xl">
                  <div className="text-[var(--color-ash)] text-sm mb-1 flex items-center gap-1"><User size={14}/> Type</div>
                  <div className="text-xl font-bold text-[var(--color-ink)] capitalize">{user.type}</div>
                </div>
                {isDonor && (
                  <div className="bg-[var(--color-surface-card)] p-4 rounded-xl col-span-2 flex items-center justify-between">
                    <div>
                      <div className="text-[var(--color-ash)] text-sm mb-1 flex items-center gap-1"><Phone size={14}/> Contact</div>
                      <div className="text-lg font-bold text-[var(--color-ink)]">{user.phone || 'N/A'}</div>
                    </div>
                    <Button variant="primary">Contact Donor</Button>
                  </div>
                )}
                {!isDonor && (
                  <div className="bg-[var(--color-surface-card)] p-4 rounded-xl col-span-2">
                    <div className="text-[var(--color-ash)] text-sm mb-1 flex items-center gap-1"><MapPin size={14}/> Hospital</div>
                    <div className="text-lg font-bold text-[var(--color-ink)]">{user.hospital_name || 'N/A'}</div>
                    <div className="mt-4">
                      <Button variant="primary" className="w-full">Match Donors</Button>
                    </div>
                  </div>
                )}
              </div>

              {/* Mini Map */}
              <div className="mb-6 rounded-xl overflow-hidden h-48 relative border border-[var(--color-border)]">
                <Map
                  initialViewState={{
                    longitude: user.longitude,
                    latitude: user.latitude,
                    zoom: 13
                  }}
                  mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
                  interactive={false}
                >
                  <Marker longitude={user.longitude} latitude={user.latitude}>
                    <div className={`w-5 h-5 rounded-full border-2 border-white shadow-md ${isDonor ? 'bg-black' : 'bg-red-600'}`} />
                  </Marker>
                </Map>
              </div>

            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
