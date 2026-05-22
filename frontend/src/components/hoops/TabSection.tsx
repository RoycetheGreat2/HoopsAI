
import { useState } from 'react';

interface TabSectionProps {
  children: React.ReactNode;
}

export function TabSection({ children }: TabSectionProps) {
  const [activeTab, setActiveTab] = useState<'matches' | 'statistics'>('matches');

  return (
    <div>
      <div className="mb-6 border-b border-border flex gap-8">
        <button
          onClick={() => setActiveTab('matches')}
          className={`pb-4 font-medium transition-colors relative ${
            activeTab === 'matches'
              ? 'text-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Match Predictions
          {activeTab === 'matches' && (
            <div className="absolute bottom-0 left-0 right-0 h-1 bg-primary" />
          )}
        </button>
        <button
          onClick={() => setActiveTab('statistics')}
          className={`pb-4 font-medium transition-colors relative ${
            activeTab === 'statistics'
              ? 'text-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Statistics
          {activeTab === 'statistics' && (
            <div className="absolute bottom-0 left-0 right-0 h-1 bg-primary" />
          )}
        </button>
      </div>

      <div>
        {activeTab === 'matches' && (
          <div className="animate-fade-in">
            {/* Match content will go here */}
          </div>
        )}
        {activeTab === 'statistics' && (
          <div className="animate-fade-in">
            {/* Statistics content will go here */}
          </div>
        )}
      </div>
    </div>
  );
}
