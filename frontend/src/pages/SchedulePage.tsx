import { useState } from "react";
import { useNavigate } from "react-router-dom";

const CURSOS = {
  "Licenciaturas": ["L.AERO", "L.BIO", "L.EA", "L.EC", "L.EEC", "L.EGI", "L.EIC", "L.EM", "L.EMAT", "L.EMG", "L.EQ", "L.EF", "CINF"],
  "Mestrados": ["M.BIO", "M.EA", "M.EC", "M.EEC", "M.EGI", "M.EIC", "M.EM", "M.EMAT", "M.EMG", "M.EQ", "M.IA"],
  "Pós-Graduações": ["CTEFP", "CTGDI", "CTLGD", "CTTNP"],
  "Outros": ["DEMSSO", "EASSE", "LATEX"],
};

const ANOS = ["1", "2", "3"];

const UCS_POR_CURSO: Record<string, string[]> = {
  "CINF": ["Álgebra Linear", "Cálculo", "Fundamentos de Programação", "Sistemas Digitais"],
  "L.AERO": ["Análise", "Física", "Programação", "Redes"],
  "L.EIC": ["Análise", "Física", "Programação", "Redes"],
};

const TURMAS_POR_UC: Record<string, string[]> = {
  "Álgebra Linear": ["1CINF01", "1CINF02", "1CINF03"],
  "Cálculo": ["1CINF01", "1CINF02"],
  "Fundamentos de Programação": ["1CINF01", "1CINF02", "1CINF03"],
  "Sistemas Digitais": ["1CINF01", "1CINF02"],
  "Análise": ["1LAERO01", "1LAERO02"],
  "Física": ["1LAERO01", "1LAERO02"],
};

export default function SchedulePage() {
  const navigate = useNavigate();

  const [curso, setCurso] = useState("");
  const [anos, setAnos] = useState<string[]>([]);
  const [ucs, setUcs] = useState<string[]>([]);
  const [turmas, setTurmas] = useState<string[]>([]);
  const [semanas, setSemanas] = useState<string[]>([]);

  const [showCursoDropdown, setShowCursoDropdown] = useState(false);
  const [showAnoDropdown, setShowAnoDropdown] = useState(false);
  const [showUcDropdown, setShowUcDropdown] = useState(false);
  const [showTurmaDropdown, setShowTurmaDropdown] = useState(false);
  const [showSemanaDropdown, setShowSemanaDropdown] = useState(false);

  const canShowSchedule = curso !== "" && anos.length > 0;
  const ucOptions = UCS_POR_CURSO[curso] ?? [];
  const turmaOptions = ucs.length > 0
    ? ucs.flatMap(uc => TURMAS_POR_UC[uc] ?? []).filter((v, i, a) => a.indexOf(v) === i)
    : Object.values(TURMAS_POR_UC).flat().filter((v, i, a) => a.indexOf(v) === i);

  const toggleItem = (list: string[], setList: (v: string[]) => void, item: string) => {
    setList(list.includes(item) ? list.filter(x => x !== item) : [...list, item]);
  };

  const toggleAll = (list: string[], setList: (v: string[]) => void, options: string[]) => {
    setList(list.length === options.length ? [] : [...options]);
  };

  const closeAll = () => {
    setShowCursoDropdown(false);
    setShowAnoDropdown(false);
    setShowUcDropdown(false);
    setShowTurmaDropdown(false);
    setShowSemanaDropdown(false);
  };

  const MultiDropdown = ({
    label, options, selected, setSelected, show, setShow, required, disabled,
  }: {
    label: string; options: string[]; selected: string[]; setSelected: (v: string[]) => void;
    show: boolean; setShow: (v: boolean) => void; required?: boolean; disabled?: boolean;
  }) => (
    <div style={{ position: "relative" }} onClick={e => e.stopPropagation()}>
      <button
        onClick={() => { if (!disabled) { closeAll(); setShow(!show); } }}
        style={{
          backgroundColor: "#1e2028",
          color: disabled ? "#6b7280" : required && selected.length === 0 ? "#f87171" : "white",          border: `1px solid ${required && selected.length === 0 ? "var(--accent)" : "#4b5563"}`,
          borderRadius: 4,
          padding: "8px 14px",
          fontSize: 14,
          cursor: disabled ? "not-allowed" : "pointer",
          whiteSpace: "nowrap",
          minWidth: "unset",
          textAlign: "left",
        }}
      >
        {selected.length > 0
          ? (selected.length === 1 ? selected[0] : `${selected.length} selecionados`)
          : label}{" "}
      </button>
      {show && !disabled && (
        <div style={{
          position: "absolute",
          top: "calc(100% + 4px)",
          left: 0,
          backgroundColor: "#1e2028",
          border: "1px solid #4b5563",
          borderRadius: 4,
          zIndex: 200,
          minWidth: 180,
          maxHeight: 260,
          overflowY: "auto",
          boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
        }}>
          <div
            onClick={() => toggleAll(selected, setSelected, options)}
            style={{
              padding: "8px 12px",
              fontSize: 13,
              cursor: "pointer",
              color: "#fbbf24",
              borderBottom: "1px solid #4b5563",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.05)")}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
          >
            <span>{selected.length === options.length ? "☑" : "☐"}</span>
            Selecionar todos
          </div>
          {options.map(opt => (
            <div
              key={opt}
              onClick={() => toggleItem(selected, setSelected, opt)}
              style={{
                padding: "8px 12px",
                fontSize: 13,
                cursor: "pointer",
                color: selected.includes(opt) ? "#fbbf24" : "white",
                backgroundColor: selected.includes(opt) ? "rgba(251,191,36,0.1)" : "transparent",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.05)")}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = selected.includes(opt) ? "rgba(251,191,36,0.1)" : "transparent")}
            >
              <span>{selected.includes(opt) ? "☑" : "☐"}</span>
              {opt}
            </div>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div
      style={{ minHeight: "100vh", backgroundColor: "#f0eeeb", fontFamily: "var(--sans)" }}
      onClick={closeAll}
    >
      {/* Navbar */}
      <header style={{
        padding: "12px 24px",
        backgroundColor: "#1e2028",
        display: "flex",
        alignItems: "center",
        gap: 8,
        width: "100%",
        boxSizing: "border-box",
        flexWrap: "wrap",
      }}>
        <button onClick={() => navigate("/react-dashboard")} style={btnYellow}>Início</button>
        <button style={btnOutlineDanger}>⚠ Ver Conflitos</button>
        <button style={btnOutlineLight}>Exportar</button>
        <button style={btnOutlineLight}>Editar Aulas em Paralelo</button>

        <div style={{ width: 1, height: 24, backgroundColor: "#4b5563", margin: "0 4px" }} />

        {/* Curso */}
        <div style={{ position: "relative" }} onClick={e => e.stopPropagation()}>
        <button
            onClick={() => { closeAll(); setShowCursoDropdown(!showCursoDropdown); }}
            style={{
            backgroundColor: "#1e2028",
            color: curso === "" ? "#f87171" : "white",
            border: `1px solid ${curso === "" ? "var(--accent)" : "#4b5563"}`,
            borderRadius: 4,
            padding: "8px 14px",
            fontSize: 14,
            cursor: "pointer",
            whiteSpace: "nowrap",
            textAlign: "left",
            }}
        >
            {curso === "" ? "Curso" : curso}
        </button>
        {showCursoDropdown && (
            <div style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            backgroundColor: "#1e2028",
            border: "1px solid #4b5563",
            borderRadius: 4,
            zIndex: 200,
            minWidth: 180,
            maxHeight: 260,
            overflowY: "auto",
            boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
            }}>
            {Object.entries(CURSOS).map(([group, items]) => (
                <div key={group}>
                <div style={{ padding: "6px 12px", fontSize: 11, color: "#9ca3af", textTransform: "uppercase", letterSpacing: 1, borderBottom: "1px solid #4b5563" }}>
                    {group}
                </div>
                {items.map(c => (
                    <div
                    key={c}
                    onClick={() => { setCurso(c); setAnos([]); setUcs([]); setTurmas([]); setShowCursoDropdown(false); }}
                    style={{
                        padding: "8px 12px",
                        fontSize: 13,
                        cursor: "pointer",
                        color: curso === c ? "#fbbf24" : "white",
                        backgroundColor: curso === c ? "rgba(251,191,36,0.1)" : "transparent",
                        display: "flex", alignItems: "center", gap: 8,
                    }}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = "rgba(255,255,255,0.05)")}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = curso === c ? "rgba(251,191,36,0.1)" : "transparent")}
                    >
                    {c}
                    </div>
                ))}
                </div>
            ))}
            </div>
        )}
        </div>

        {/* Ano */}
        <MultiDropdown
          label="Ano"
          options={ANOS}
          selected={anos}
          setSelected={setAnos}
          show={showAnoDropdown}
          setShow={setShowAnoDropdown}
          required={true}
        />

        <div style={{ width: 1, height: 24, backgroundColor: "#4b5563", margin: "0 4px" }} />

        {/* UC */}
        <MultiDropdown
          label="Unidade Curricular"
          options={ucOptions}
          selected={ucs}
          setSelected={setUcs}
          show={showUcDropdown}
          setShow={setShowUcDropdown}
          disabled={!canShowSchedule}
        />

        {/* Turmas */}
        <MultiDropdown
          label="Turma"
          options={turmaOptions}
          selected={turmas}
          setSelected={setTurmas}
          show={showTurmaDropdown}
          setShow={setShowTurmaDropdown}
          disabled={!canShowSchedule}
        />

        {/* Semanas */}
        <MultiDropdown
          label="Semanas"
          options={["S1", "S2", "S3", "S4", "S5"]}
          selected={semanas}
          setSelected={setSemanas}
          show={showSemanaDropdown}
          setShow={setShowSemanaDropdown}
          disabled={!canShowSchedule}
        />

        <button style={btnOutlineLight}>Distribuição</button>
        <button style={{ ...btnOutlineLight, marginLeft: "auto" }}>▶</button>
      </header>

      {/* Content */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "calc(100vh - 60px)",
        color: "#6b7280",
        fontSize: 18,
      }}>
        {canShowSchedule ? "Grelha de horário (a fazer)" : "Seleciona Curso e Ano para ver o horário"}
      </div>
    </div>
  );
}

const btnYellow: React.CSSProperties = {
  backgroundColor: "var(--accent)",
  color: "white",
  fontWeight: 600,
  padding: "8px 14px",
  borderRadius: 4,
  border: "none",
  cursor: "pointer",
  fontSize: 14,
  whiteSpace: "nowrap",
};

const btnOutlineDanger: React.CSSProperties = {
  backgroundColor: "transparent",
  color: "#f87171",
  fontWeight: 600,
  padding: "8px 14px",
  borderRadius: 4,
  border: "1px solid #f87171",
  cursor: "pointer",
  fontSize: 14,
  whiteSpace: "nowrap",
};

const btnOutlineLight: React.CSSProperties = {
  backgroundColor: "transparent",
  color: "white",
  fontWeight: 600,
  padding: "8px 14px",
  borderRadius: 4,
  border: "1px solid #4b5563",
  cursor: "pointer",
  fontSize: 14,
  whiteSpace: "nowrap",
};