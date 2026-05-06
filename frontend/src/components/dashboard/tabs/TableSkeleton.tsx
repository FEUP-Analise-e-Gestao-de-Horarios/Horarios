interface TableSkeletonProps {
  cols: number;
  gridTemplateColumns: string;
}

export default function TableSkeleton({ cols, gridTemplateColumns }: TableSkeletonProps) {
  return (
    <div role="rowgroup">
      {Array.from({ length: 25 }).map((_, row) => (
        <div
          key={row}
          role="row"
          className="grid border-b border-[#e5e4e7]"
          style={{ gridTemplateColumns }}
        >
          {Array.from({ length: cols }).map((_, col) => (
            <div key={col} role="cell" className="py-3 px-4">
              <div
                className="h-3.5 rounded bg-[#e5e4e7] animate-pulse"
                style={{ width: `${55 + (((row * cols + col) * 37) % 40)}%` }}
              />
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
