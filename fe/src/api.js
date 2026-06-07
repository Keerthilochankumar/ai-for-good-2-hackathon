const API_BASE = import.meta.env.VITE_Backend_Api || import.meta.env.Backend_Api || '';

const getUrl = (path) => {
  let base = API_BASE ? API_BASE.replace(/\/+$/, '') : '';
  let subPath = path.startsWith('/') ? path : `/${path}`;
  const fullPath = base ? `${base}${subPath}` : subPath;
  
  if (fullPath.startsWith('http://') || fullPath.startsWith('https://')) {
    return new URL(fullPath);
  }
  return new URL(fullPath, window.location.origin);
};

export const importDataset = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/admin/import`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Failed to import dataset');
  }
  return response.json();
};

export const getDonors = async (skip = 0, limit = 100, q = '') => {
  const url = getUrl('/donors/');
  url.searchParams.append('skip', skip);
  url.searchParams.append('limit', limit);
  if (q) url.searchParams.append('q', q);

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error('Failed to fetch donors');
  }
  return response.json();
};

export const getPatients = async (skip = 0, limit = 100, q = '') => {
  const url = getUrl('/patients/');
  url.searchParams.append('skip', skip);
  url.searchParams.append('limit', limit);
  if (q) url.searchParams.append('q', q);

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error('Failed to fetch patients');
  }
  return response.json();
};

export const getMatches = async (patientId) => {
  const response = await fetch(`${API_BASE}/patients/${patientId}/matches`);
  if (!response.ok) {
    throw new Error('Failed to fetch matches');
  }
  return response.json();
};

export const createDonor = async (data) => {
  const response = await fetch(`${API_BASE}/donors/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!response.ok) throw new Error('Failed to create donor');
  return response.json();
};

export const createPatient = async (data) => {
  const response = await fetch(`${API_BASE}/patients/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!response.ok) throw new Error('Failed to create patient');
  return response.json();
};

export const triggerMatch = async (patientId) => {
  const response = await fetch(`${API_BASE}/patients/${patientId}/trigger_match`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to trigger match');
  return response.json();
};

export const lockMatch = async (patientId, donorId) => {
  const response = await fetch(`${API_BASE}/patients/${patientId}/lock_match/${donorId}`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to lock match');
  return response.json();
};

export const getStats = async (bloodGroup = 'ALL') => {
  const url = getUrl('/stats');
  if (bloodGroup && bloodGroup !== 'ALL') {
    url.searchParams.append('blood_group', bloodGroup);
  }
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to fetch stats');
  return response.json();
};
