import { forwardRef, useState, type ReactNode } from "react";

type PasswordFieldProps = {
  id: string;
  label: string;
  placeholder?: string;
  visiblePlaceholder?: string;
  value: string;
  onChange: (value: string) => void;
  onKeyDown?: (e: React.KeyboardEvent) => void;
  error?: string;
  shake?: boolean;
  disabled?: boolean;
  children?: ReactNode;
};

const PasswordField = forwardRef<HTMLInputElement, PasswordFieldProps>(
  (
    {
      id,
      label,
      placeholder = "••••••••",
      visiblePlaceholder = "palavra-passe",
      value,
      onChange,
      onKeyDown,
      error,
      shake,
      disabled,
      children,
    },
    ref,
  ) => {
    const [visible, setVisible] = useState(false);

    return (
      <div className={`flex flex-col gap-1.5 ${shake ? "animate-shake" : ""}`}>
        <label htmlFor={id} className="text-sm text-[#6b6375]">
          {label}
        </label>
        <div className="relative">
          <input
            ref={ref}
            id={id}
            type={visible ? "text" : "password"}
            placeholder={visible ? visiblePlaceholder : placeholder}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={disabled}
            className={`w-full px-3 py-2 pr-10 rounded border outline-none bg-[#f4f3ec] text-[#08060d] focus:border-[rgba(140,45,25,0.5)] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)] placeholder:text-[#c5c1ca] disabled:opacity-50 disabled:cursor-not-allowed ${
              error ? "border-[#8c2d19]" : "border-[#e5e4e7]"
            }`}
          />
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            disabled={disabled}
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-transparent border-none cursor-pointer text-[#9b95a3] hover:text-[#08060d] text-sm p-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {visible ? "Ocultar" : "Mostrar"}
          </button>
        </div>
        {error && <p className="text-[#8c2d19] text-[13px] m-0">{error}</p>}
        {children}
      </div>
    );
  },
);

PasswordField.displayName = "PasswordField";
export default PasswordField;
