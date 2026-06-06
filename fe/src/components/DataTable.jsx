import React from 'react';

export function DataTable({ headers, rows, renderRow, className = '', ...props }) {
  return (
    <div className={`w-full overflow-x-auto border border-hairline bg-canvas ${className}`} {...props}>
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-canvas-soft border-b border-hairline">
            {headers.map((h, i) => (
              <th 
                key={i} 
                className="px-4 py-3 font-sans text-[12px] font-bold uppercase tracking-wider text-ink whitespace-nowrap"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-hairline">
          {rows.length === 0 ? (
            <tr>
              <td colSpan={headers.length} className="px-4 py-6 text-center text-body font-sans text-[14px]">
                No data available
              </td>
            </tr>
          ) : (
            rows.map((row, i) => renderRow(row, i))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function TableCell({ children, className = '', ...props }) {
  return (
    <td className={`px-4 py-3 font-sans text-[14px] text-ink whitespace-nowrap ${className}`} {...props}>
      {children}
    </td>
  );
}
