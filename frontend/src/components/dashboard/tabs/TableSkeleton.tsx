interface TableSkeletonProps {
  cols: number;
}

export default function TableSkeleton({ cols }: TableSkeletonProps) {
  return (
    <>
      {Array.from({ length: 25 }).map((_, row) => (
        <tr key={row} className="border-b border-[#e5e4e7]">
          {Array.from({ length: cols }).map((_, col) => (
            <td key={col} className="py-3 px-4">
              <div
                className="h-3.5 rounded bg-[#e5e4e7] animate-pulse"
                style={{ width: `${55 + (((row * cols + col) * 37) % 40)}%` }}
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
