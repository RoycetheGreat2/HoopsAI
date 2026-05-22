
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useState } from 'react';

interface DateCarouselProps {
  selectedDate: string;
  onDateChange: (date: string) => void;
}

export function DateCarousel({ selectedDate, onDateChange }: DateCarouselProps) {
  const dates = [
    { id: '1', label: 'Dec 18', date: '2024-12-18' },
    { id: '2', label: 'Dec 19', date: '2024-12-19' },
    { id: '3', label: 'Dec 20', date: '2024-12-20' },
    { id: '4', label: 'Dec 21', date: '2024-12-21' },
    { id: '5', label: 'Dec 22', date: '2024-12-22' },
    { id: '6', label: 'Dec 23', date: '2024-12-23' },
    { id: '7', label: 'Dec 24', date: '2024-12-24' },
  ];

  const [scrollPosition, setScrollPosition] = useState(0);

  const scroll = (direction: 'left' | 'right') => {
    const container = document.getElementById('date-scroll');
    if (container) {
      const scrollAmount = 300;
      const newPosition = direction === 'left' 
        ? Math.max(0, scrollPosition - scrollAmount)
        : scrollPosition + scrollAmount;
      container.scrollLeft = newPosition;
      setScrollPosition(newPosition);
    }
  };

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-foreground">Match Predictions</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => scroll('left')}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5 text-foreground" />
          </button>
          <button
            onClick={() => scroll('right')}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
          >
            <ChevronRight className="w-5 h-5 text-foreground" />
          </button>
        </div>
      </div>

      <div
        id="date-scroll"
        className="flex gap-3 overflow-x-auto pb-2 scroll-smooth"
        style={{ scrollBehavior: 'smooth' }}
      >
        {dates.map((dateItem) => (
          <button
            key={dateItem.id}
            onClick={() => onDateChange(dateItem.date)}
            className={`flex-shrink-0 px-6 py-3 rounded-lg font-medium transition-colors whitespace-nowrap ${
              selectedDate === dateItem.date
                ? 'bg-primary text-white'
                : 'bg-white border border-border text-foreground hover:bg-muted'
            }`}
          >
            {dateItem.label}
          </button>
        ))}
      </div>
    </div>
  );
}
