import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { SignedIn, SignedOut } from '@clerk/clerk-react';
import { Toaster } from 'react-hot-toast';

import { LandingPage } from './components/LandingPage';
import { Dashboard } from './components/Dashboard';
import { NavBar } from './components/NavBar';
import { DonorsPage } from './components/DonorsPage';
import { PatientsPage } from './components/PatientsPage';
import { EventsPage } from './components/EventsPage';
import { AddDonor } from './components/AddDonor';
import { AddPatient } from './components/AddPatient';
import { TestPage } from './components/TestPage';
import { PipelineEventsProvider } from './hooks/usePipelineEvents';

function Layout({ children }) {
  return (
    <div className="min-h-screen bg-[var(--color-canvas)] text-[var(--color-ink)] font-sans">
      <NavBar />
      <main className="mx-auto w-full max-w-[1400px] px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
      <Toaster position="bottom-right" />
    </div>
  );
}

function App() {
  return (
    <PipelineEventsProvider>
      <Routes>
        <Route 
          path="/" 
          element={
            <>
              <SignedOut><LandingPage /></SignedOut>
              <SignedIn><Navigate to="/dashboard" replace /></SignedIn>
            </>
          } 
        />
        
        {/* Protected Routes */}
        <Route path="/dashboard" element={<SignedIn><Layout><Dashboard /></Layout></SignedIn>} />
        <Route path="/donors" element={<SignedIn><Layout><DonorsPage /></Layout></SignedIn>} />
        <Route path="/patients" element={<SignedIn><Layout><PatientsPage /></Layout></SignedIn>} />
        <Route path="/events" element={<SignedIn><Layout><EventsPage /></Layout></SignedIn>} />
        <Route path="/add-donor" element={<SignedIn><Layout><AddDonor /></Layout></SignedIn>} />
        <Route path="/add-patient" element={<SignedIn><Layout><AddPatient /></Layout></SignedIn>} />
        <Route path="/test" element={<SignedIn><Layout><TestPage /></Layout></SignedIn>} />
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </PipelineEventsProvider>
  );
}

export default App;
