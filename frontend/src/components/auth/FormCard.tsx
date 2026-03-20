import type { ReactNode } from "react";

export default function FormCard({
  children,
  onSubmit,
}: {
  children: ReactNode;
  onSubmit?: (e: React.SyntheticEvent) => void;
}) {
  const className =
    "flex flex-col gap-5 w-96 p-8 rounded-lg shadow-[rgba(0,0,0,0.1)_0_10px_15px_-3px,rgba(0,0,0,0.05)_0_4px_6px_-2px] border border-[#e5e4e7]";

  if (onSubmit) {
    return (
      <form onSubmit={onSubmit} className={className}>
        {children}
      </form>
    );
  }

  return <div className={className}>{children}</div>;
}
