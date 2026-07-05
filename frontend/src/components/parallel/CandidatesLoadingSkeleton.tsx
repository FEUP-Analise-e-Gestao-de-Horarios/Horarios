export default function CandidatesLoadingSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-40 rounded-2xl bg-[#e8e8e8] animate-pulse" />
      ))}
    </div>
  );
}
