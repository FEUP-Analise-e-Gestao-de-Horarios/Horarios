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

export type DropdownPerson = {
  id: string;
  label: string;
};

export type DropdownRoom = {
  id: string;
  typology: string;
};

export const ALL_DOCENTES: DropdownPerson[] = [
  { id: "D001", label: "AA - António José Coelho Dias Arêde" },
  { id: "D002", label: "AAAF - Alexandre Almeida de Abreu Filho" },
  { id: "D003", label: "AAG - Ana Cristina Costa Aguiar" },
  { id: "D004", label: "AAM - Artur Manuel de Oliveira Andrade Moura" },
  { id: "D005", label: "AARH - António Abel Ribeiro Henriques" },
  { id: "D006", label: "AASP - Ana Alexandra da Silva Pereira" },
  { id: "D007", label: "DMat - MJPSR - Maria João Pinto Sampaio Rodrigues" },
];

export const DOCENTES_POR_UC: Record<string, string[]> = {
  "Álgebra Linear": ["D001", "D007"],
  Cálculo: ["D002", "D003"],
  "Fundamentos de Programação": ["D004", "D006"],
  "Sistemas Digitais": ["D005", "D003"],
  Análise: ["D001", "D005"],
  Física: ["D002", "D004"],
};

export const ALL_SALAS: DropdownRoom[] = [
  { id: "B117", typology: "TP" },
  { id: "B222", typology: "TP" },
  { id: "B001", typology: "T" },
  { id: "B002", typology: "T" },
  { id: "LAB01", typology: "PL" },
  { id: "LAB02", typology: "PL" },
  { id: "A201", typology: "Seminário" },
];

export const SALAS_POR_UC: Record<string, string[]> = {
  "Álgebra Linear": ["B117", "B222"],
  Cálculo: ["B001", "B002"],
  "Fundamentos de Programação": ["LAB01", "LAB02"],
  "Sistemas Digitais": ["LAB01", "B117"],
  Análise: ["B002", "A201"],
  Física: ["LAB02", "A201"],
};

export type Conflict = {
  id: string;
  eventNames: string[];
  day: string;
  time: string;
  turma: string;
  conflictReasons: string[];
};

export const ALL_CONFLICTS: Conflict[] = [
  {
    id: "C001",
    eventNames: [
      "Aula SEM (Quinta - 17:30 [Turma: EASSE1])",
      "Aula ESR (Quinta - 15:00 [Turma: 1PDEECO1])",
    ],
    day: "Quinta",
    time: "17:30",
    turma: "EASSE1",
    conflictReasons: ["Sala M225B está ocupada", "Turma EASSE1 está ocupada"],
  },
  {
    id: "C002",
    eventNames: [
      "Aula SEM (Quinta - 17:30 [Turma: EASSE1])",
      "Aula SR (Quinta - 15:00 [Turma: 1PDEECO1])",
    ],
    day: "Quinta",
    time: "17:30",
    turma: "EASSE1",
    conflictReasons: ["Turma EASSE1 está ocupada"],
  },
  {
    id: "C003",
    eventNames: ["Aula LTW (Segunda - 14:00 [Turma: 2LEIC10])", "Período de Indisponibilidade"],
    day: "Segunda",
    time: "14:00",
    turma: "2LEIC10",
    conflictReasons: ["Turma 2LEIC10 está ocupada"],
  },
  {
    id: "C004",
    eventNames: [
      "Aula SCCOM (Segunda - 15:30 [Turma: 1CINF01])",
      "Aula TRI (Segunda - 15:30 [Turma: 1M201])",
    ],
    day: "Segunda",
    time: "15:30",
    turma: "1CINF01",
    conflictReasons: ["Sala B022 está ocupada"],
  },
  {
    id: "C005",
    eventNames: [
      "Aula AM II (Terça - 08:30 [Turma: 1LEIC01])",
      "Aula AM II (Terça - 08:30 [Turma: 1LEIC04])",
    ],
    day: "Terça",
    time: "08:30",
    turma: "1LEIC01",
    conflictReasons: ["Docente AMPA está ocupado"],
  },
  {
    id: "C006",
    eventNames: [
      "Aula AM II (Terça - 08:30 [Turma: 1LEIC01])",
      "Aula FME (Terça - 08:30 [Turma: 2LEEC05])",
    ],
    day: "Terça",
    time: "08:30",
    turma: "1LEIC01",
    conflictReasons: ["Sala B322 está ocupada"],
  },
];
