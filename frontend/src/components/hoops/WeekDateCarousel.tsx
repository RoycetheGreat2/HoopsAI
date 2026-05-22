import { useMemo, useState, useRef, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';
import {
  parseYmd,
  localYmd,
  addDaysYmd,
  compareYmd,
  clampYmd,
} from '@/hooks/useApi';
import { TRACKING_SINCE } from '@/config';

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

interface WeekDateCarouselProps {
  selectedDate: string;
  onDateChange: (date: string) => void;
  viewWeekStart: string;
  onViewWeekStartChange: (start: string) => void;
  /** Last selectable day (inclusive), e.g. today + 6 */
  maxSelectableDate: string;
}

function toYmd(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

function firstDayOfMonthYmd(year: number, monthIndex: number): string {
  return `${year}-${String(monthIndex + 1).padStart(2, '0')}-01`;
}

export function WeekDateCarousel({
  selectedDate,
  onDateChange,
  viewWeekStart,
  onViewWeekStartChange,
  maxSelectableDate,
}: WeekDateCarouselProps) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);
  const today = localYmd();

  const anchorDate = parseYmd(
    clampYmd(viewWeekStart, TRACKING_SINCE, maxSelectableDate)
  );
  const pickerYear = anchorDate.getFullYear();
  const pickerMonth = anchorDate.getMonth();

  const weekDates = useMemo(() => {
    const start = parseYmd(viewWeekStart);
    const dates: Date[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      dates.push(d);
    }
    return dates;
  }, [viewWeekStart]);

  const monthLabel = anchorDate.toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  });

  const maxWeekStart = addDaysYmd(maxSelectableDate, -6);
  const canGoPrev = compareYmd(addDaysYmd(viewWeekStart, -7), TRACKING_SINCE) >= 0;
  const canGoNext = compareYmd(addDaysYmd(viewWeekStart, 7), maxWeekStart) <= 0;

  const yearOptions = useMemo(() => {
    const minY = parseYmd(TRACKING_SINCE).getFullYear();
    const maxY = parseYmd(maxSelectableDate).getFullYear();
    const years: number[] = [];
    for (let y = minY; y <= maxY; y++) years.push(y);
    return years;
  }, [maxSelectableDate]);

  const availableMonths = useMemo(() => {
    const min = parseYmd(TRACKING_SINCE);
    const max = parseYmd(maxSelectableDate);
    const months: number[] = [];
    for (let m = 0; m < 12; m++) {
      const probe = new Date(pickerYear, m, 15);
      if (probe < new Date(min.getFullYear(), min.getMonth(), 1)) continue;
      if (probe > new Date(max.getFullYear(), max.getMonth() + 1, 0)) continue;
      months.push(m);
    }
    return months;
  }, [pickerYear, maxSelectableDate]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setPickerOpen(false);
      }
    }
    if (pickerOpen) document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [pickerOpen]);

  function shiftWeek(delta: number) {
    const next = addDaysYmd(viewWeekStart, delta * 7);
    const clamped = clampYmd(next, TRACKING_SINCE, maxWeekStart);
    onViewWeekStartChange(clamped);
    if (compareYmd(selectedDate, clamped) < 0) {
      onDateChange(clampYmd(clamped, TRACKING_SINCE, maxSelectableDate));
    } else if (compareYmd(selectedDate, addDaysYmd(clamped, 6)) > 0) {
      onDateChange(
        clampYmd(addDaysYmd(clamped, 6), TRACKING_SINCE, maxSelectableDate)
      );
    }
  }

  function applyMonthYear(year: number, monthIndex: number) {
    let start = firstDayOfMonthYmd(year, monthIndex);
    if (compareYmd(start, TRACKING_SINCE) < 0) start = TRACKING_SINCE;
    const monthEnd = addDaysYmd(
      firstDayOfMonthYmd(
        monthIndex === 11 ? year + 1 : year,
        monthIndex === 11 ? 0 : monthIndex + 1
      ),
      -1
    );
    if (
      compareYmd(today, start) >= 0 &&
      compareYmd(today, monthEnd) <= 0
    ) {
      start = clampYmd(
        addDaysYmd(today, -((parseYmd(today).getDay() + 7) % 7)),
        TRACKING_SINCE,
        maxWeekStart
      );
    }
    start = clampYmd(start, TRACKING_SINCE, maxWeekStart);
    onViewWeekStartChange(start);
    const pick =
      compareYmd(selectedDate, start) >= 0 &&
      compareYmd(selectedDate, addDaysYmd(start, 6)) <= 0
        ? selectedDate
        : compareYmd(today, start) >= 0 &&
            compareYmd(today, addDaysYmd(start, 6)) <= 0
          ? clampYmd(today, TRACKING_SINCE, maxSelectableDate)
          : clampYmd(start, TRACKING_SINCE, maxSelectableDate);
    onDateChange(pick);
    setPickerOpen(false);
  }

  return (
    <div className="mb-8 rounded-lg border border-border bg-white p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="relative" ref={pickerRef}>
          <button
            type="button"
            onClick={() => setPickerOpen((o) => !o)}
            className="flex min-w-max items-center gap-2 rounded-lg border border-border px-3 py-2 transition-colors hover:bg-muted"
          >
            <Calendar className="h-5 w-5 text-primary" />
            <span className="text-sm font-medium text-foreground">{monthLabel}</span>
          </button>

          {pickerOpen && (
            <div className="absolute left-0 top-full z-50 mt-2 w-64 rounded-lg border border-border bg-white p-4 shadow-lg">
              <label className="mb-1 block text-xs font-medium text-muted-foreground">
                Year
              </label>
              <select
                className="mb-3 w-full rounded-md border border-border px-2 py-1.5 text-sm"
                value={pickerYear}
                onChange={(e) =>
                  applyMonthYear(Number(e.target.value), pickerMonth)
                }
              >
                {yearOptions.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">
                Month
              </label>
              <div className="grid grid-cols-3 gap-2">
                {availableMonths.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => applyMonthYear(pickerYear, m)}
                    className={`rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${
                      m === pickerMonth
                        ? 'bg-primary text-white'
                        : 'bg-muted text-foreground hover:bg-muted/80'
                    }`}
                  >
                    {MONTHS[m].slice(0, 3)}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => shiftWeek(-1)}
            disabled={!canGoPrev}
            className="rounded-lg p-2 transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Previous week"
          >
            <ChevronLeft className="h-5 w-5 text-foreground" />
          </button>

          <div className="flex gap-2 overflow-x-auto pb-1">
            {weekDates.map((date) => {
              const dateStr = toYmd(date);
              const isBeforeMin = compareYmd(dateStr, TRACKING_SINCE) < 0;
              const isAfterMax = compareYmd(dateStr, maxSelectableDate) > 0;
              const isDisabled = isBeforeMin || isAfterMax;
              const isSelected = dateStr === selectedDate;
              const day = date.getDate();
              const weekday = DAY_LABELS[date.getDay()];

              return (
                <button
                  key={dateStr}
                  type="button"
                  disabled={isDisabled}
                  onClick={() => {
                    if (isDisabled) return;
                    onDateChange(dateStr);
                  }}
                  className={`flex min-w-16 flex-col items-center rounded-lg p-3 transition-colors ${
                    isDisabled
                      ? 'cursor-not-allowed opacity-35 bg-muted/50 text-muted-foreground'
                      : isSelected
                        ? 'bg-primary text-white'
                        : 'bg-muted text-foreground hover:bg-muted/80'
                  }`}
                >
                  <span className="text-xs font-medium opacity-80">{weekday}</span>
                  <span className="text-lg font-bold">{day}</span>
                </button>
              );
            })}
          </div>

          <button
            type="button"
            onClick={() => shiftWeek(1)}
            disabled={!canGoNext}
            className="rounded-lg p-2 transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Next week"
          >
            <ChevronRight className="h-5 w-5 text-foreground" />
          </button>
        </div>
      </div>
    </div>
  );
}
