import React from 'react';
import { SignInButton } from '@clerk/clerk-react';
import { Button } from './Button';

export function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/80 to-blue-50/80 p-4 sm:p-6 md:p-8 flex flex-col font-sans">
      <div className="flex-1 bg-white/70 backdrop-blur-xl rounded-[2.5rem] shadow-2xl border-4 border-white relative overflow-hidden flex flex-col">
        {/* Background Blood Drop Watermark */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-0 overflow-hidden">
          <svg viewBox="0 0 24 24" fill="currentColor" className="text-red-600 opacity-[0.05] w-[120vh] h-[120vh] min-w-[700px] min-h-[700px] -translate-y-32">
            <path d="M12 2C12 2 4 9.9 4 15.4C4 19.8 7.6 23.4 12 23.4C16.4 23.4 20 19.8 20 15.4C20 9.9 12 2 12 2Z" />
          </svg>
        </div>

      <main className="flex-1 flex flex-col items-center justify-center text-center px-4 py-20 max-w-4xl mx-auto mt-10 relative z-10">
        <h1 className="font-sans text-[44px] sm:text-[70px] font-semibold tracking-[-1.2px] text-[var(--color-ink)] leading-[1.1] mb-6">
          AI-Powered Blood Donation Matching
        </h1>
        <p className="text-[var(--color-body)] text-[18px] sm:text-[22px] max-w-2xl mb-10 leading-[1.4]">
          Our intelligent pipeline instantly connects critical patients with optimal local donors via Telegram. No waiting. Just saved lives.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 items-center">
          <SignInButton mode="modal" fallbackRedirectUrl="/dashboard">
            <Button variant="primary" className="text-[18px] px-8 py-4 min-h-[56px] rounded-full">
              Enter Dashboard
            </Button>
          </SignInButton>
        </div>



        {/* Masonry / Feature Preview Section */}
        <div className="mt-20 w-full grid grid-cols-2 md:grid-cols-4 gap-4 auto-rows-[200px]">
          {/* Row 1 & 2 */}
          <div className="bg-[var(--color-surface-card)] rounded-[2rem] overflow-hidden shadow-sm hover:-translate-y-1 transition-transform relative group">
             <img src="https://images.unsplash.com/photo-1615461066159-fea0960485d5?q=80&w=600&auto=format&fit=crop" className="object-cover w-full h-full opacity-90 group-hover:scale-110 transition-transform duration-500" alt="Blood donation" />
             <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur-sm px-3 py-1 rounded-full text-xs font-bold text-red-600">Donate</div>
          </div>
          <div className="bg-[var(--color-surface-card)] rounded-[2.5rem] overflow-hidden md:col-span-2 md:row-span-2 shadow-sm hover:-translate-y-1 transition-transform relative group">
            <img src="https://images.unsplash.com/photo-1579684385127-1ef15d508118?q=80&w=800&auto=format&fit=crop" className="object-cover w-full h-full opacity-90 group-hover:scale-110 transition-transform duration-700" alt="Medical care" />
             <div className="absolute top-6 left-6 bg-white/90 backdrop-blur-sm px-4 py-2 rounded-full text-sm font-bold shadow-sm text-blue-600">Save a life</div>
          </div>
          <div className="bg-[var(--color-surface-card)] rounded-[2rem] overflow-hidden shadow-sm hover:-translate-y-1 transition-transform relative group">
            <img src="https://images.unsplash.com/photo-1532938911079-1b06ac7ceec7?q=80&w=600&auto=format&fit=crop" className="object-cover w-full h-full opacity-90 group-hover:scale-110 transition-transform duration-500" alt="Community" />
          </div>
          
          {/* Row 2 filler */}
          <div className="bg-[var(--color-surface-card)] rounded-[2rem] overflow-hidden shadow-sm hover:-translate-y-1 transition-transform relative group">
            <img src="https://images.unsplash.com/photo-1469571486292-0ba58a3f068b?q=80&w=600&auto=format&fit=crop" className="object-cover w-full h-full opacity-90 group-hover:scale-110 transition-transform duration-500" alt="Helping hand" />
          </div>
          <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-[2rem] overflow-hidden flex items-center justify-center p-6 text-white text-center shadow-md hover:-translate-y-1 transition-transform">
            <p className="font-bold text-xl">Every drop counts.</p>
          </div>

          {/* Row 3 - New Images */}
          <div className="bg-[var(--color-surface-card)] rounded-[2rem] overflow-hidden md:col-span-2 shadow-sm hover:-translate-y-1 transition-transform relative group">
            <img src="https://images.unsplash.com/photo-1581056771107-24ca5f033842?q=80&w=800&auto=format&fit=crop" className="object-cover w-full h-full opacity-90 group-hover:scale-110 transition-transform duration-500" alt="Research/AI" />
             <div className="absolute bottom-4 right-4 bg-white/90 backdrop-blur-sm px-3 py-1 rounded-full text-xs font-bold text-gray-800">AI Powered Matching</div>
          </div>
          <div className="bg-[var(--color-surface-card)] rounded-[2rem] overflow-hidden shadow-sm hover:-translate-y-1 transition-transform relative group">
            <img src="https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?q=80&w=600&auto=format&fit=crop" className="object-cover w-full h-full opacity-90 group-hover:scale-110 transition-transform duration-500" alt="Hospital" />
          </div>
          <div className="bg-[var(--color-surface-card)] rounded-[2rem] overflow-hidden shadow-sm hover:-translate-y-1 transition-transform relative group">
            <img src="https://images.unsplash.com/photo-1584515933487-779824d29309?q=80&w=600&auto=format&fit=crop" className="object-cover w-full h-full opacity-90 group-hover:scale-110 transition-transform duration-500" alt="Health" />
          </div>
        </div>
      </main>
      </div>
    </div>
  );
}
