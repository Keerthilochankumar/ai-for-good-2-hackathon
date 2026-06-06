import React, { useState, useMemo, useEffect, useRef } from 'react';
import Map, { Marker, NavigationControl, Source, Layer } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';

export function MapDashboard({ donors, patients = [], activePatientId = null, activeMatches = [], onUserClick }) {
  const mapRef = useRef();
  const [viewState, setViewState] = useState({
    longitude: 77.5946,
    latitude: 12.9716,
    zoom: 10
  });

  // Fit bounds dynamically
  useEffect(() => {
    if (!mapRef.current) return;
    const allCoords = [
      ...(donors || []).map(d => [d.longitude, d.latitude]),
      ...(patients || []).map(p => [p.longitude, p.latitude])
    ].filter(c => c[0] && c[1]);

    if (allCoords.length > 0) {
      const bounds = allCoords.reduce((acc, coord) => [
        [Math.min(acc[0][0], coord[0]), Math.min(acc[0][1], coord[1])],
        [Math.max(acc[1][0], coord[0]), Math.max(acc[1][1], coord[1])]
      ], [[allCoords[0][0], allCoords[0][1]], [allCoords[0][0], allCoords[0][1]]]);
      
      if (bounds[0][0] !== bounds[1][0] && bounds[0][1] !== bounds[1][1]) {
        mapRef.current.fitBounds(bounds, { padding: 50, duration: 1000 });
      } else {
        setViewState(prev => ({ ...prev, longitude: bounds[0][0], latitude: bounds[0][1], zoom: 12 }));
      }
    }
  }, [donors, patients]);

  const matchLines = useMemo(() => {
    if (!activePatientId || activeMatches.length === 0) return null;
    const patient = patients.find(p => p.id === activePatientId);
    if (!patient) return null;

    const features = activeMatches.map(match => {
      const donor = donors.find(d => d.id === match.donor_id);
      if (!donor) return null;
      return {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [patient.longitude, patient.latitude],
            [donor.longitude, donor.latitude]
          ]
        },
        properties: {
          status: match.status || 'evaluating'
        }
      };
    }).filter(Boolean);

    return { type: 'FeatureCollection', features };
  }, [activePatientId, activeMatches, donors, patients]);

  const donorMarkers = useMemo(() => {
    return (donors || []).filter(d => d.longitude != null && d.latitude != null).map((donor, index) => {
      const isSelected = activeMatches.some(m => m.donor_id === donor.id && m.status === 'selected');
      const isEvaluating = activeMatches.some(m => m.donor_id === donor.id && m.status === 'evaluating');
      
      let pinClass = "w-4 h-4 bg-black rounded-full border-2 border-white shadow-md transform transition-all duration-300 group-hover:scale-125";
      if (isSelected) pinClass = "w-6 h-6 bg-green-500 rounded-full border-4 border-white shadow-[0_0_15px_rgba(34,197,94,0.8)] animate-pulse z-10 relative";
      else if (isEvaluating) pinClass = "w-4 h-4 bg-yellow-400 rounded-full border-2 border-white shadow-[0_0_10px_rgba(250,204,21,0.6)] animate-bounce z-10 relative";

      return (
        <Marker key={`donor-${donor.id || index}`} longitude={donor.longitude} latitude={donor.latitude} anchor="bottom">
          <div className="group relative cursor-pointer flex flex-col items-center" onClick={() => onUserClick && onUserClick({ type: 'donor', ...donor })}>
            <div className="absolute bottom-full mb-2 hidden group-hover:block w-max bg-black text-white text-xs font-sans font-bold px-2 py-1 rounded-md shadow-lg z-50">
              {donor.name} ({donor.blood_group})
            </div>
            <div className={pinClass} />
          </div>
        </Marker>
      );
    });
  }, [donors, activeMatches, onUserClick]);

  const patientMarkers = useMemo(() => {
    return (patients || []).filter(p => p.longitude != null && p.latitude != null).map((patient, index) => {
      const isActive = patient.id === activePatientId;
      return (
        <Marker key={`patient-${patient.id || index}`} longitude={patient.longitude} latitude={patient.latitude} anchor="bottom">
          <div className="group relative cursor-pointer flex flex-col items-center" onClick={() => onUserClick && onUserClick({ type: 'patient', ...patient })}>
            <div className="absolute bottom-full mb-2 hidden group-hover:block w-max bg-red-600 text-white text-xs font-sans font-bold px-2 py-1 rounded-md shadow-lg z-50">
              {patient.patient_name} - {patient.hospital_name} ({patient.blood_group || patient.blood_group_needed})
            </div>
            <div className={`w-5 h-5 bg-red-600 rounded-full border-2 border-white shadow-md transform transition-all duration-300 group-hover:scale-125 ${isActive ? 'ring-4 ring-red-400 animate-pulse scale-125 z-20 relative' : ''}`} />
          </div>
        </Marker>
      );
    });
  }, [patients, activePatientId, onUserClick]);

  return (
    <Map
      ref={mapRef}
      {...viewState}
      onMove={evt => setViewState(evt.viewState)}
      mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
      style={{ width: '100%', height: '100%' }}
    >
      <NavigationControl position="top-right" />
      {matchLines && (
        <Source id="match-lines" type="geojson" data={matchLines}>
          <Layer 
            id="lines-evaluating"
            type="line"
            filter={['==', 'status', 'evaluating']}
            paint={{
              'line-color': '#facc15',
              'line-width': 2,
              'line-dasharray': [2, 2],
              'line-opacity': 0.6
            }}
          />
          <Layer 
            id="lines-selected"
            type="line"
            filter={['==', 'status', 'selected']}
            paint={{
              'line-color': '#22c55e',
              'line-width': 4,
              'line-opacity': 0.9
            }}
          />
        </Source>
      )}
      {donorMarkers}
      {patientMarkers}
    </Map>
  );
}
