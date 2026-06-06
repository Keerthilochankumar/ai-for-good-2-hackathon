import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Skeleton from 'react-loading-skeleton';
import 'react-loading-skeleton/dist/skeleton.css';
import { DataTable, TableCell } from './DataTable';
import { getDonors } from '../api';

export function DonorsPage() {
  const [donors, setDonors] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDonors(0, 100).then(data => {
      setDonors(data);
      setLoading(false);
    }).catch(console.error);
  }, []);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-ink)]">Donors Directory</h1>
          <p className="text-[var(--color-ash)] mt-1">Manage and view all registered donors.</p>
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
            headers={['Name', 'Blood Group', 'Phone', 'Available', 'Status']}
            rows={donors}
            renderRow={(donor) => (
              <tr key={donor.id} className="border-b border-[var(--color-hairline)] hover:bg-[var(--color-surface-soft)] transition-colors">
                <TableCell className="font-semibold">{donor.name}</TableCell>
                <TableCell>
                  <span className="bg-[var(--color-primary)] text-white text-xs px-2 py-1 rounded-[var(--radius-md)] font-bold">{donor.blood_group}</span>
                </TableCell>
                <TableCell>{donor.phone}</TableCell>
                <TableCell>{donor.is_available ? 'Yes' : 'No'}</TableCell>
                <TableCell>{donor.account_status || 'ACTIVE'}</TableCell>
              </tr>
            )}
          />
        )}
      </div>
    </motion.div>
  );
}
