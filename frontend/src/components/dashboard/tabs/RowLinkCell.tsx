import { Link, type LinkProps } from "react-router-dom";
import type { ReactNode } from "react";

interface RowLinkCellProps {
  to: LinkProps["to"];
  primary?: boolean;
  className?: string;
  children: ReactNode;
}

export default function RowLinkCell({ to, primary, className, children }: RowLinkCellProps) {
  return (
    <td className="p-0">
      <Link
        to={to}
        draggable={false}
        tabIndex={primary ? undefined : -1}
        className={`block py-3 px-4 ${className ?? ""}`}
      >
        {children}
      </Link>
    </td>
  );
}
