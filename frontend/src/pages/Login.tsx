export default function Login() {
  return (
    <div className="min-h-screen bg-[#2b2b2b] flex items-center justify-center font-sans">
      <div className="flex flex-col gap-4 w-70">
        <h1 className="text-white text-3xl font-bold m-0">Sign In</h1>

        <div className="flex flex-col gap-1">
          <input
            type="text"
            placeholder="Username"
            className="px-3 py-2 rounded border-none outline-none"
          />
          <span className="text-gray-300 text-[13px] flex">Nome de utilizador</span>
        </div>

        <div className="flex flex-col gap-1">
          <input
            type="password"
            placeholder="••••••••"
            className="px-3 py-2 rounded border-none outline-none"
          />
          <span className="text-gray-300 text-[13px] flex">Palavra-passe</span>
        </div>

        <a href="#" className="text-blue-400 text-[13px]">
          Esqueci-me da palavra-passe
        </a>

        <button className="bg-yellow-400 text-black font-semibold py-2.5 rounded border-none cursor-pointer text-[15px]">
          Sign in
        </button>
      </div>
    </div>
  );
}
