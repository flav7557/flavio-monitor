import { TIMEFRAMES, type Timeframe } from "@/config/markets";

export function TimeframeSelector({
  value,
  onChange,
}: {
  value: Timeframe;
  onChange: (timeframe: Timeframe) => void;
}) {
  return (
    <div className="timeframes" aria-label="Période du graphique">
      {TIMEFRAMES.map((timeframe) => (
        <button
          key={timeframe}
          type="button"
          className={timeframe === value ? "is-active" : undefined}
          onClick={() => onChange(timeframe)}
          aria-pressed={timeframe === value}
        >
          {timeframe}
        </button>
      ))}
    </div>
  );
}
