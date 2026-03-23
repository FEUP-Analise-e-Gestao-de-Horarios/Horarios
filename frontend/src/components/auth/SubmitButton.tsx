export default function SubmitButton({
  loading,
  label,
  loadingLabel,
  disabled,
}: {
  loading: boolean;
  label: string;
  loadingLabel: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="submit"
      disabled={loading || disabled}
      className="bg-[#8c2d19] text-white font-semibold py-2.5 rounded border-none cursor-pointer text-[15px] hover:bg-[#722415] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {loading ? loadingLabel : label}
    </button>
  );
}
