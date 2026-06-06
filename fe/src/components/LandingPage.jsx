import React from 'react';
import { SignInButton } from '@clerk/clerk-react';
import { Button } from './Button';

export function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--color-surface-soft)] flex flex-col font-sans">
      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 py-20 max-w-4xl mx-auto mt-10">
        <h1 className="font-sans text-[44px] sm:text-[70px] font-semibold tracking-[-1.2px] text-[var(--color-ink)] leading-[1.1] mb-6">
          Saving lives and making everyone help each other.
        </h1>
        <p className="text-[var(--color-body)] text-[18px] sm:text-[22px] max-w-2xl mb-10 leading-[1.4]">
          "The measure of a life is not its duration, but its donation." — Join Blood Warriors to become the hero someone desperately needs.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 items-center">
          <SignInButton mode="modal" fallbackRedirectUrl="/dashboard">
            <Button variant="primary" className="text-[18px] px-8 py-4 min-h-[56px] rounded-full">
              Get Started
            </Button>
          </SignInButton>
        </div>

        {/* Masonry / Feature Preview Section */}
        <div className="mt-20 w-full grid grid-cols-2 md:grid-cols-4 gap-4 auto-rows-[200px]">
          <div className="bg-[var(--color-surface-card)] rounded-[var(--radius-md)] overflow-hidden shadow-sm hover:-translate-y-1 transition-transform relative">
             <img src="https://images.unsplash.com/photo-1615461066159-fea0960485d5?q=80&w=600&auto=format&fit=crop" className="object-cover w-full h-full opacity-90" alt="Blood donation" />
             <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur-sm px-3 py-1 rounded-full text-xs font-bold">Donate</div>
          </div>
          <div className="bg-[var(--color-surface-card)] rounded-[var(--radius-lg)] overflow-hidden md:col-span-2 md:row-span-2 shadow-sm hover:-translate-y-1 transition-transform relative">
            <img src="https://images.unsplash.com/photo-1579684385127-1ef15d508118?q=80&w=800&auto=format&fit=crop" className="object-cover w-full h-full opacity-90" alt="Medical care" />
             <div className="absolute top-6 left-6 bg-white/90 backdrop-blur-sm px-4 py-2 rounded-full text-sm font-bold shadow-sm">Save a life</div>
          </div>
          <div className="bg-[var(--color-surface-card)] rounded-[var(--radius-md)] overflow-hidden shadow-sm hover:-translate-y-1 transition-transform relative">
            <img src="https://images.unsplash.com/photo-1532938911079-1b06ac7ceec7?q=80&w=600&auto=format&fit=crop" className="object-cover w-full h-full opacity-90" alt="Community" />
          </div>
          <div className="bg-[var(--color-surface-card)] rounded-[var(--radius-md)] overflow-hidden shadow-sm hover:-translate-y-1 transition-transform relative">
            <img src="https://images.unsplash.com/photo-1469571486292-0ba58a3f068b?q=80&w=600&auto=format&fit=crop" className="object-cover w-full h-full opacity-90" alt="Helping hand" />
          </div>
          <div className="bg-[var(--color-primary)] rounded-[var(--radius-md)] overflow-hidden flex items-center justify-center p-6 text-white text-center shadow-sm hover:-translate-y-1 transition-transform">
            <p className="font-bold text-lg">Every drop counts.</p>
          </div>
        </div>
      </main>
    </div>
  );
}
