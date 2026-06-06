import React from 'react';

export function Card({ children, className = '', variant = 'default', ...props }) {
  const variants = {
    default: "bg-[var(--color-canvas)]",
    soft: "bg-[var(--color-surface-card)]"
  };
  
  return (
    <div 
      className={`${variants[variant]} p-6 sm:p-8 rounded-[var(--radius-md)] ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, className = '', ...props }) {
  return (
    <div className={`mb-6 ${className}`} {...props}>
      <h3 className="font-sans text-[22px] font-semibold tracking-tight text-[var(--color-ink)] leading-[1.25]">{title}</h3>
      {subtitle && <p className="font-sans text-[16px] text-[var(--color-body)] mt-2 leading-[1.4]">{subtitle}</p>}
    </div>
  );
}

export function CardContent({ children, className = '', ...props }) {
  return (
    <div className={`text-[var(--color-body)] ${className}`} {...props}>
      {children}
    </div>
  );
}
