export default function ChangePasswordPage() {
  return (
    <div className="min-h-svh bg-white flex items-center justify-center font-[system-ui,'Segoe_UI',Roboto,sans-serif] text-[#6b6375] text-lg leading-[145%] tracking-[0.18px] antialiased max-lg:text-base">
      <div className="flex flex-col gap-4 w-80">
        <h1 className="text-[#08060d] text-2xl font-bold m-0">Mudar palavra-passe</h1>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="old-password" className="text-[#6b6375] text-sm">
            Palavra-passe antiga:
          </label>
          <input
            id="old-password"
            type="password"
            className="px-3 py-2.5 rounded border border-[#8c2d19] bg-white text-[#08060d] outline-none text-[15px] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)]"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="new-password" className="text-[#6b6375] text-sm">
            Palavra-passe nova:
          </label>
          <input
            id="new-password"
            type="password"
            className="px-3 py-2.5 rounded border border-[#8c2d19] bg-white text-[#08060d] outline-none text-[15px] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)]"
          />
          <ul className="text-[#6b6375] text-[13px] m-0 pl-5 leading-[1.8]">
            <li>A palavra-passe não pode ser muito semelhante às suas informações pessoais.</li>
            <li>A palavra-passe deve ter pelo menos 8 caracteres.</li>
            <li>A palavra-passe não pode ser uma palavra-passe muito comum.</li>
            <li>A palavra-passe não pode ser inteiramente numérica.</li>
          </ul>
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="confirm-password" className="text-[#6b6375] text-sm">
            Confirmação da palavra-passe nova:
          </label>
          <input
            id="confirm-password"
            type="password"
            className="w-full box-border px-3 py-2.5 rounded border border-[#8c2d19] bg-white text-[#08060d] outline-none text-[15px] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)]"
          />
        </div>

        <button className="bg-[#8c2d19] text-white font-semibold py-2.5 rounded border-none cursor-pointer text-[15px] hover:bg-[#722415] transition-colors">
          Guardar mudanças
        </button>
      </div>
    </div>
  );
}
