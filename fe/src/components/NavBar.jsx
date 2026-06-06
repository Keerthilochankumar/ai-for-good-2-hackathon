import React from 'react';
import { Menu, Search } from 'lucide-react';
import { Button } from './Button';
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react';
import { Link, useLocation } from 'react-router-dom';

export function NavBar({ onSearch }) {
  const location = useLocation();
  const isActive = (path) => location.pathname === path ? 'bg-[var(--color-surface-card)] text-[var(--color-primary)]' : 'text-[var(--color-ink)] hover:bg-[var(--color-surface-card)]';

  return (
    <header className="sticky top-0 z-50 w-full bg-[var(--color-canvas)] pb-[1px] shadow-sm">
      <div className="flex h-[64px] items-center justify-between px-4 sm:px-6">
        {/* Left: Logo & Links */}
        <div className="flex items-center gap-6">
          <button className="md:hidden text-[var(--color-ink)] hover:bg-[var(--color-surface-card)] p-2 rounded-full">
            <Menu size={24} />
          </button>
          <Link to="/" className="flex items-center gap-2">
            <div className="bg-[var(--color-primary)] text-white font-bold w-8 h-8 rounded-full flex items-center justify-center text-lg">
              B
            </div>
            <span className="hidden md:inline font-sans font-bold text-[18px] text-[var(--color-primary)] tracking-tight">
              BloodWarriors
            </span>
          </Link>
          <nav className="hidden md:flex items-center gap-2">
            <Link to="/dashboard" className={`font-sans font-semibold text-[14px] px-3 py-2 rounded-full transition-colors ${isActive('/dashboard')}`}>Dashboard</Link>
            <Link to="/donors" className={`font-sans font-semibold text-[14px] px-3 py-2 rounded-full transition-colors ${isActive('/donors')}`}>Donors</Link>
            <Link to="/patients" className={`font-sans font-semibold text-[14px] px-3 py-2 rounded-full transition-colors ${isActive('/patients')}`}>Patients</Link>
            <Link to="/events" className={`font-sans font-semibold text-[14px] px-3 py-2 rounded-full transition-colors ${isActive('/events')}`}>Events</Link>
          </nav>
        </div>

        {/* Center: Search Bar */}
        <div className="flex-1 max-w-2xl px-4 hidden sm:flex">
          <div className="w-full relative group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--color-ash)] group-focus-within:text-[var(--color-ink)]" size={20} />
            <input 
              type="text" 
              placeholder="Search for donors, patients..." 
              className="w-full bg-[var(--color-surface-card)] text-[var(--color-ink)] placeholder:text-[var(--color-ash)] font-sans text-[16px] rounded-full py-[11px] pl-12 pr-4 outline-none focus:bg-[var(--color-canvas)] focus:ring-1 focus:ring-[var(--color-ash)] transition-all"
              onChange={(e) => onSearch && onSearch(e.target.value)}
            />
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2 sm:gap-4">
          <SignedOut>
            <div className="hidden sm:block">
              <SignInButton mode="modal">
                <Button variant="secondary" className="mr-2">Log in</Button>
              </SignInButton>
            </div>
            <SignInButton mode="modal">
              <Button variant="primary">Sign up</Button>
            </SignInButton>
          </SignedOut>
          <SignedIn>
            <Link to="/add-donor" className="hidden sm:block">
              <Button variant="secondary" className="mr-2 cursor-pointer">Add Donor</Button>
            </Link>
            <Link to="/add-patient">
              <Button variant="primary" className="cursor-pointer">Request Blood</Button>
            </Link>
            <UserButton afterSignOutUrl="/" appearance={{ elements: { userButtonAvatarBox: "w-10 h-10" } }} />
          </SignedIn>
        </div>
      </div>
    </header>
  );
}
