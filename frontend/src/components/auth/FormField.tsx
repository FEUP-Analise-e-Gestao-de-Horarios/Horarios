import { forwardRef, type ReactNode } from "react";

type FormFieldProps = {
  id: string;
  label: string;
  type?: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  onKeyDown?: (e: React.KeyboardEvent) => void;
  error?: string;
  shake?: boolean;
  children?: ReactNode;
};

const FormField = forwardRef<HTMLInputElement, FormFieldProps>(
  (
    { id, label, type = "text", placeholder, value, onChange, onKeyDown, error, shake, children },
    ref,
  ) => {
    return (
      <div className={`flex flex-col gap-1.5 ${shake ? "animate-shake" : ""}`}>
        <label htmlFor={id} className="text-sm text-[#6b6375]">
          {label}
        </label>
        <input
          ref={ref}
          id={id}
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          className={`px-3 py-2 rounded border outline-none bg-[#f4f3ec] text-[#08060d] focus:border-[rgba(140,45,25,0.5)] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)] placeholder:text-[#c5c1ca] ${
            error ? "border-[#8c2d19]" : "border-[#e5e4e7]"
          }`}
        />
        {error && <p className="text-[#8c2d19] text-[13px] m-0">{error}</p>}
        {children}
      </div>
    );
  },
);

FormField.displayName = "FormField";
export default FormField;
