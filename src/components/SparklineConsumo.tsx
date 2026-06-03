export function SparklineConsumo({ data, width = 120, height = 32 }: { data: number[]; width?: number; height?: number }) {
  if (!data?.length) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const step = width / (data.length - 1);
  const points = data.map((v, i) => `${i * step},${height - ((v - min) / range) * (height - 4) - 2}`).join(" ");
  const areaPoints = `0,${height} ${points} ${width},${height}`;
  const gradId = `sparkGrad-${Math.random().toString(36).slice(2, 8)}`;
  return (
    <svg width={width} height={height} className="overflow-visible">
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--cyan-elec)" stopOpacity="0.5" />
          <stop offset="100%" stopColor="var(--cyan-elec)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={areaPoints} fill={`url(#${gradId})`} />
      <polyline
        points={points}
        fill="none"
        stroke="var(--cyan-elec)"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ filter: "drop-shadow(0 0 4px var(--cyan-elec))" }}
      />
      {data.map((v, i) => (
        <circle
          key={i}
          cx={i * step}
          cy={height - ((v - min) / range) * (height - 4) - 2}
          r={i === data.length - 1 ? 2.5 : 1.2}
          fill="var(--cyan-elec)"
        />
      ))}
    </svg>
  );
}
