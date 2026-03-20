interface NewProjectCardProps {
  onClick: () => void;
}

export default function NewProjectCard({ onClick }: NewProjectCardProps) {
  return (
    <button
      type="button"
      className="w-[220px] h-[220px] bg-white border border-[#e5e4e7] rounded-lg flex flex-col items-center justify-center cursor-pointer shadow-[0_2px_8px_rgba(0,0,0,0.08)] overflow-hidden hover:shadow-[0_4px_12px_rgba(0,0,0,0.12)] transition-shadow"
      onClick={onClick}
    >
      <span className="text-[90px] text-[#8c2d19] leading-none">+</span>
      <span className="text-[#08060d] font-medium mt-2">Novo Projeto</span>
    </button>
  );
}
