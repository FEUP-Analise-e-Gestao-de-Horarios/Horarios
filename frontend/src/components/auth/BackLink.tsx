import { Link } from "react-router-dom";

export default function BackLink({ to, children }: { to: string; children: string }) {
  return (
    <Link
      to={to}
      className="text-[#9b95a3] text-sm text-center no-underline hover:text-[#08060d] transition-colors flex items-center justify-center gap-1.5"
    >
      <span aria-hidden="true">&larr;</span> {children}
    </Link>
  );
}
