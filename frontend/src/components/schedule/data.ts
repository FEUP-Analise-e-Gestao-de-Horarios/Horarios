export const CURSOS: Record<string, string[]> = {
  Licenciaturas: [
    "L.AERO",
    "L.BIO",
    "L.EA",
    "L.EC",
    "L.EEC",
    "L.EGI",
    "L.EIC",
    "L.EM",
    "L.EMAT",
    "L.EMG",
    "L.EQ",
    "L.EF",
    "CINF",
  ],
  Mestrados: [
    "M.BIO",
    "M.EA",
    "M.EC",
    "M.EEC",
    "M.EGI",
    "M.EIC",
    "M.EM",
    "M.EMAT",
    "M.EMG",
    "M.EQ",
    "M.IA",
  ],
  "Pós-Graduações": ["CTEFP", "CTGDI", "CTLGD", "CTTNP"],
  Outros: ["DEMSSO", "EASSE", "LATEX"],
};

export const ANOS = ["1", "2", "3"];

export const UCS_POR_CURSO: Record<string, string[]> = {
  CINF: ["Álgebra Linear", "Cálculo", "Fundamentos de Programação", "Sistemas Digitais"],
  "L.AERO": ["Análise", "Física", "Programação", "Redes"],
  "L.EIC": ["Análise", "Física", "Programação", "Redes"],
};

export const TURMAS_POR_UC: Record<string, string[]> = {
  "Álgebra Linear": ["1CINF01", "1CINF02", "1CINF03"],
  Cálculo: ["1CINF01", "1CINF02"],
  "Fundamentos de Programação": ["1CINF01", "1CINF02", "1CINF03"],
  "Sistemas Digitais": ["1CINF01", "1CINF02"],
  Análise: ["1LAERO01", "1LAERO02"],
  Física: ["1LAERO01", "1LAERO02"],
};
