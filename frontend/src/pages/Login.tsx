export default function Login() {
  return (
    <div className="min-h-svh bg-white flex items-center justify-center font-[system-ui,'Segoe_UI',Roboto,sans-serif] text-[#6b6375] text-lg leading-[145%] tracking-[0.18px] antialiased max-lg:text-base">
      <div className="flex flex-col gap-5 w-80 p-6 rounded-lg shadow-[rgba(0,0,0,0.1)_0_10px_15px_-3px,rgba(0,0,0,0.05)_0_4px_6px_-2px] border border-[#e5e4e7]">
        <h1 className="text-[#08060d] text-2xl font-bold m-0">Sign In</h1>

        <div className="flex flex-col gap-1">
          <label htmlFor="username" className="text-[13px] text-[#6b6375]">
            Nome de utilizador
          </label>
          <input
            id="username"
            type="text"
            placeholder="Username"
            className="px-3 py-2 rounded border border-[#e5e4e7] outline-none bg-[#f4f3ec] text-[#08060d] focus:border-[rgba(140,45,25,0.5)] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)]"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="password" className="text-[13px] text-[#6b6375]">
            Palavra-passe
          </label>
          <input
            id="password"
            type="password"
            placeholder="••••••••"
            className="px-3 py-2 rounded border border-[#e5e4e7] outline-none bg-[#f4f3ec] text-[#08060d] focus:border-[rgba(140,45,25,0.5)] focus:ring-1 focus:ring-[rgba(140,45,25,0.5)]"
          />
        </div>

        <button
          type="button"
          className="text-[#8c2d19] text-[13px] text-left hover:underline cursor-pointer bg-transparent border-none p-0"
        >
          Esqueci-me da palavra-passe
        </button>

        <button className="bg-[#8c2d19] text-white font-semibold py-2.5 rounded border-none cursor-pointer text-[15px] hover:bg-[#722415] transition-colors">
          Sign in
        </button>
      </div>
    </div>
  );
}
