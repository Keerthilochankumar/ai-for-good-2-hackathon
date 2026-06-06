import React from 'react';

export function Button({ 
  children, 
  variant = 'primary', 
  className = '', 
  ...props 
}) {
  const baseStyles = "inline-flex items-center justify-center rounded-[var(--radius-md)] px-[14px] py-[6px] min-h-[40px] text-[14px] font-bold font-sans transition-colors focus:outline-none focus:ring-4 focus:ring-[var(--color-focus-outer)]";
  
  const variants = {
    primary: "bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-pressed)]",
    secondary: "bg-[var(--color-secondary-bg)] text-[var(--color-ink)] hover:bg-[var(--color-secondary-pressed)]",
    tertiary: "bg-transparent text-[var(--color-ink)] hover:bg-[var(--color-surface-card)]",
    icon: "rounded-full p-2 bg-[var(--color-surface-card)] text-[var(--color-ink)] hover:bg-[var(--color-secondary-bg)] min-h-0 min-w-0 w-10 h-10",
  };

  return (
    <button 
      className={`${baseStyles} ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
