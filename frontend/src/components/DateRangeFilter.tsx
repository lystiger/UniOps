import { useEffect, useMemo, useRef, useState } from "react";
import { isoDate } from "../format";
import { useLocale, useT } from "../i18n";
import type { Locale } from "../i18n/types";
import { DateInput } from "./DateInput";

export interface DateRangeFilterProps {
  fromDate: string;
  toDate: string;
  onChange: (next: { fromDate: string; toDate: string }) => void;
}

interface MonthYear {
  year: number;
  month: number; // 0-indexed: 0 = Jan, 11 = Dec
}

function getMonthName(year: number, month: number, locale: Locale): string {
  const date = new Date(year, month, 15);
  return new Intl.DateTimeFormat(locale === "vi" ? "vi-VN" : "en-US", { month: "long" }).format(date);
}

function getWeekdayNames(locale: Locale): string[] {
  // Monday 2026-08-03 to Sunday 2026-08-09
  const formatter = new Intl.DateTimeFormat(locale === "vi" ? "vi-VN" : "en-US", { weekday: "short" });
  const names: string[] = [];
  for (let d = 3; d <= 9; d++) {
    names.push(formatter.format(new Date(2026, 7, d)));
  }
  return names;
}

function parseDate(iso: string): Date | null {
  if (!iso) return null;
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d);
}

function formatYMD(year: number, month: number, day: number): string {
  const m = String(month + 1).padStart(2, "0");
  const d = String(day).padStart(2, "0");
  return `${year}-${m}-${d}`;
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstWeekday(year: number, month: number): number {
  // 0 = Monday, ..., 6 = Sunday
  const day = new Date(year, month, 1).getDay();
  return (day + 6) % 7;
}

function addMonths(current: MonthYear, delta: number): MonthYear {
  const date = new Date(current.year, current.month + delta, 1);
  return { year: date.getFullYear(), month: date.getMonth() };
}

export function DateRangeFilter({ fromDate, toDate, onChange }: DateRangeFilterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [hoverDate, setHoverDate] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { locale } = useLocale();
  const t = useT();

  // Initialize view month based on existing fromDate, toDate, or default to current month
  const initialDate = parseDate(fromDate) ?? parseDate(toDate) ?? new Date();
  const [viewMonth, setViewMonth] = useState<MonthYear>(() => {
    const month = initialDate.getMonth();
    const year = initialDate.getFullYear();
    if (toDate && !fromDate) {
      return addMonths({ year, month }, -1);
    }
    return { year, month };
  });

  const nextMonth = addMonths(viewMonth, 1);
  const weekdays = useMemo(() => getWeekdayNames(locale), [locale]);

  // Close on outside click or Escape key
  useEffect(() => {
    if (!isOpen) return;

    function handlePointerDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  function handleDayClick(dayStr: string) {
    if (!fromDate || (fromDate && toDate)) {
      // Start a new range
      onChange({ fromDate: dayStr, toDate: "" });
    } else if (fromDate && !toDate) {
      // Complete or reverse range
      if (dayStr < fromDate) {
        onChange({ fromDate: dayStr, toDate: fromDate });
      } else {
        onChange({ fromDate, toDate: dayStr });
      }
    }
  }

  // Quick preset helpers
  function applyPreset(from: string, to: string) {
    onChange({ fromDate: from, toDate: to });
    if (from) {
      const d = parseDate(from);
      if (d) setViewMonth({ year: d.getFullYear(), month: d.getMonth() });
    }
  }

  const today = new Date();
  const todayStr = formatYMD(today.getFullYear(), today.getMonth(), today.getDate());

  function setThisMonth() {
    const year = today.getFullYear();
    const month = today.getMonth();
    const lastDay = getDaysInMonth(year, month);
    applyPreset(formatYMD(year, month, 1), formatYMD(year, month, lastDay));
  }

  function setLastMonth() {
    const prev = addMonths({ year: today.getFullYear(), month: today.getMonth() }, -1);
    const lastDay = getDaysInMonth(prev.year, prev.month);
    applyPreset(formatYMD(prev.year, prev.month, 1), formatYMD(prev.year, prev.month, lastDay));
  }

  function setLast3Months() {
    const start = addMonths({ year: today.getFullYear(), month: today.getMonth() }, -2);
    const currentYear = today.getFullYear();
    const currentMonth = today.getMonth();
    const lastDay = getDaysInMonth(currentYear, currentMonth);
    applyPreset(formatYMD(start.year, start.month, 1), formatYMD(currentYear, currentMonth, lastDay));
  }

  function setLastYear() {
    const prevYear = today.getFullYear() - 1;
    applyPreset(`${prevYear}-01-01`, `${prevYear}-12-31`);
  }

  function clearRange() {
    onChange({ fromDate: "", toDate: "" });
  }

  return (
    <div className="date-range-filter-root" ref={containerRef}>
      <div className="date-range-bar">
        <label className="date-range-input-label">
          <span>{t.dateFilter.from}</span>
          <DateInput
            value={fromDate}
            max={toDate || undefined}
            onChange={(value) => onChange({ fromDate: value, toDate })}
            onFocus={() => setIsOpen(true)}
          />
        </label>

        <label className="date-range-input-label">
          <span>{t.dateFilter.to}</span>
          <DateInput
            value={toDate}
            min={fromDate || undefined}
            onChange={(value) => onChange({ fromDate, toDate: value })}
            onFocus={() => setIsOpen(true)}
          />
        </label>

        <button
          type="button"
          className={`dual-calendar-trigger ${isOpen ? "active" : ""}`}
          onClick={() => setIsOpen((prev) => !prev)}
          aria-expanded={isOpen}
          aria-label={t.dateFilter.triggerAria}
          title={t.dateFilter.triggerAria}
        >
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          <span>{t.dateFilter.calendar}</span>
          {(fromDate || toDate) && (
            <span className="dual-calendar-selected-range">
              ({fromDate ? isoDate(fromDate) : "—"} – {toDate ? isoDate(toDate) : "—"})
            </span>
          )}
          <svg className={`trigger-chevron ${isOpen ? "open" : ""}`} viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
      </div>

      {isOpen && (
        <div className="dual-calendar-popover" role="dialog" aria-label={t.dateFilter.calendarDialogAria}>
          <div className="dual-calendar-layout">
            {/* Quick Period Presets */}
            <aside className="dual-calendar-presets" aria-label={t.dateFilter.presets}>
              <span className="presets-title">{t.dateFilter.presets}</span>
              <button type="button" className="preset-btn" onClick={setThisMonth}>{t.dateFilter.thisMonth}</button>
              <button type="button" className="preset-btn" onClick={setLastMonth}>{t.dateFilter.lastMonth}</button>
              <button type="button" className="preset-btn" onClick={setLast3Months}>{t.dateFilter.last3Months}</button>
              <button type="button" className="preset-btn" onClick={setLastYear}>{t.dateFilter.lastYear}</button>
              <button type="button" className="preset-btn clear" onClick={clearRange}>{t.dateFilter.clear}</button>
            </aside>

            {/* Main Dual Month Grids */}
            <div className="dual-calendar-grids-container">
              {/* Navigation Header */}
              <div className="dual-calendar-nav-header">
                <button
                  type="button"
                  className="cal-nav-btn prev"
                  onClick={() => setViewMonth((vm) => addMonths(vm, -1))}
                  aria-label={t.dateFilter.prevMonthAria}
                >
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <polyline points="15 18 9 12 15 6" />
                  </svg>
                </button>

                <div className="cal-nav-month-labels">
                  <span className="cal-month-title">{getMonthName(viewMonth.year, viewMonth.month, locale)} {viewMonth.year}</span>
                  <span className="cal-month-title">{getMonthName(nextMonth.year, nextMonth.month, locale)} {nextMonth.year}</span>
                </div>

                <button
                  type="button"
                  className="cal-nav-btn next"
                  onClick={() => setViewMonth((vm) => addMonths(vm, 1))}
                  aria-label={t.dateFilter.nextMonthAria}
                >
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </button>
              </div>

              {/* Two Grids Side-by-Side */}
              <div className="dual-calendar-months">
                <MonthGrid
                  monthYear={viewMonth}
                  fromDate={fromDate}
                  toDate={toDate}
                  hoverDate={hoverDate}
                  todayStr={todayStr}
                  locale={locale}
                  weekdays={weekdays}
                  onDayClick={handleDayClick}
                  onDayHover={setHoverDate}
                />
                <MonthGrid
                  monthYear={nextMonth}
                  fromDate={fromDate}
                  toDate={toDate}
                  hoverDate={hoverDate}
                  todayStr={todayStr}
                  locale={locale}
                  weekdays={weekdays}
                  onDayClick={handleDayClick}
                  onDayHover={setHoverDate}
                />
              </div>
            </div>
          </div>

          {/* Footer with status summary and Close action */}
          <div className="dual-calendar-footer">
            <div className="range-summary">
              {fromDate && toDate ? (
                <>
                  <span className="range-badge">{t.dateFilter.selected}</span>
                  <strong>{isoDate(fromDate)}</strong>
                  <span className="range-arrow">→</span>
                  <strong>{isoDate(toDate)}</strong>
                </>
              ) : fromDate ? (
                <>
                  <span className="range-badge pending">{t.dateFilter.pickEndDate}</span>
                  <span>{t.dateFilter.from} <strong>{isoDate(fromDate)}</strong></span>
                </>
              ) : (
                <span className="range-empty-text">{t.dateFilter.promptStart}</span>
              )}
            </div>

            <div className="footer-actions">
              {(fromDate || toDate) && (
                <button type="button" className="ghost-button small" onClick={clearRange}>
                  {t.dateFilter.reset}
                </button>
              )}
              <button
                type="button"
                className="primary-button small"
                onClick={() => setIsOpen(false)}
              >
                {t.dateFilter.done}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MonthGrid({
  monthYear,
  fromDate,
  toDate,
  hoverDate,
  todayStr,
  locale,
  weekdays,
  onDayClick,
  onDayHover,
}: {
  monthYear: MonthYear;
  fromDate: string;
  toDate: string;
  hoverDate: string | null;
  todayStr: string;
  locale: Locale;
  weekdays: string[];
  onDayClick: (dayStr: string) => void;
  onDayHover: (dayStr: string | null) => void;
}) {
  const { year, month } = monthYear;
  const daysInMonth = getDaysInMonth(year, month);
  const firstWeekday = getFirstWeekday(year, month);

  const days: { day: number; dateStr: string }[] = [];
  for (let d = 1; d <= daysInMonth; d++) {
    days.push({ day: d, dateStr: formatYMD(year, month, d) });
  }

  return (
    <div className="month-grid-wrapper" onMouseLeave={() => onDayHover(null)}>
      <div className="month-grid-header">
        {getMonthName(year, month, locale)} {year}
      </div>

      <div className="weekdays-row">
        {weekdays.map((w, idx) => (
          <span key={idx} className="weekday-header">{w}</span>
        ))}
      </div>

      <div className="days-grid">
        {/* Empty cells before day 1 */}
        {Array.from({ length: firstWeekday }).map((_, idx) => (
          <span key={`blank-${idx}`} className="day-cell blank" aria-hidden="true" />
        ))}

        {days.map(({ day, dateStr }) => {
          const isStart = dateStr === fromDate;
          const isEnd = dateStr === toDate;
          const isSingle = isStart && isEnd;
          const inRange =
            fromDate && toDate && dateStr > fromDate && dateStr < toDate;
          const inHover =
            fromDate &&
            !toDate &&
            hoverDate &&
            ((hoverDate > fromDate && dateStr > fromDate && dateStr <= hoverDate) ||
              (hoverDate < fromDate && dateStr < fromDate && dateStr >= hoverDate));
          const isToday = dateStr === todayStr;

          let cellClass = "day-cell";
          if (isSingle) cellClass += " range-single";
          else if (isStart) cellClass += " range-start";
          else if (isEnd) cellClass += " range-end";
          else if (inRange) cellClass += " in-range";
          else if (inHover) cellClass += " in-hover";

          if (isToday) cellClass += " is-today";

          return (
            <button
              key={dateStr}
              type="button"
              className={cellClass}
              onClick={() => onDayClick(dateStr)}
              onMouseEnter={() => onDayHover(dateStr)}
              aria-label={dateStr}
              aria-pressed={isStart || isEnd}
            >
              <span className="day-number">{day}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
