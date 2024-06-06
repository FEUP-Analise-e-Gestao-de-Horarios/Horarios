DROP TABLE IF EXISTS aulasSimultaneas;
DROP TABLE IF EXISTS salaBloco;
DROP TABLE IF EXISTS turno;
DROP TABLE IF EXISTS turmaUC;
DROP TABLE IF EXISTS blocoUC;
DROP TABLE IF EXISTS blocoTurma;
DROP TABLE IF EXISTS blocoDocente;
DROP TABLE IF EXISTS aulaTurmas;
DROP TABLE IF EXISTS aulaDocente;
DROP TABLE IF EXISTS aulaSala;
DROP TABLE IF EXISTS aulaUC;
DROP TABLE IF EXISTS aula;
DROP TABLE IF EXISTS turmas;
DROP TABLE IF EXISTS curso;
DROP TABLE IF EXISTS salas;
DROP TABLE IF EXISTS blocosVermelhos;
DROP TABLE IF EXISTS uc;
DROP TABLE IF EXISTS docentes;

CREATE TABLE docentes(
    numeroMecanografico INTEGER PRIMARY KEY,
    nome TEXT,
    abreviacao TEXT 
);

CREATE TABLE uc(
    codigo TEXT PRIMARY KEY,
    idCurso TEXT REFERENCES curso(designacao),
    nome TEXT,
    codOcorrencia INTEGER,
    sigla TEXT
);

CREATE TABLE blocosVermelhos(
    id INTEGER NOT NULL PRIMARY KEY,
    hora DATE,
    diaSemana TEXT 
);
CREATE TABLE salas(
    numero TEXT PRIMARY KEY,
    tipo TEXT,
    capacidade TEXT,
    tamanhoComp TEXT -- Size
);
CREATE TABLE curso( 
    designacao TEXT PRIMARY KEY, 
    abreviacao TEXT
);
CREATE TABLE turmas(
    idCurso TEXT REFERENCES curso(designacao),
    ano INTEGER,
    codigo TEXT PRIMARY KEY -- Primary key (1CINF01)
);
CREATE TABLE aula(
    id INTEGER NOT NULL PRIMARY KEY,
    horaInicial INTEGER, -- Integer
    duracao INTEGER,
    diaSemana TEXT,
    teorico BOOLEAN,
    semanaInicial DATE,
    semanaFinal DATE
);

CREATE TABLE aulaUC(
    idAula INTEGER REFERENCES aula(id) ON UPDATE CASCADE ON DELETE CASCADE,
    idUC TEXT REFERENCES uc(codigo) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (idAula, idUC)
);

CREATE TABLE aulaSala(
    idAula INTEGER REFERENCES aula(id) ON UPDATE CASCADE ON DELETE CASCADE,
    idSala TEXT REFERENCES salas(numero) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (idAula, idSala)
);

CREATE TABLE aulaDocente (
    idAula INTEGER REFERENCES aula(id) ON UPDATE CASCADE ON DELETE CASCADE,
    idDocente TEXT REFERENCES docentes(numeroMecanografico) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (idAula, idDocente)
);

CREATE TABLE aulaTurmas (
    idAula INTEGER REFERENCES aula(id) ON UPDATE CASCADE ON DELETE CASCADE,
    idTurma TEXT REFERENCES turmas(codigo) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (idAula, idTurma)
);

CREATE TABLE blocoDocente (
    idBloco INTEGER REFERENCES blocosVermelhos(id) ON UPDATE CASCADE ON DELETE CASCADE,
    idDocente INTEGER REFERENCES docentes(numeroMecanografico) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (idBloco, idDocente)
);

CREATE TABLE blocoTurma (
    idBloco INTEGER REFERENCES blocosVermelhos(id) ON UPDATE CASCADE ON DELETE CASCADE,
    idTurma TEXT REFERENCES turmas(codigo) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (idBloco, idTurma)
);

CREATE TABLE blocoUC (
    idBloco INTEGER REFERENCES blocosVermelhos(id) ON UPDATE CASCADE ON DELETE CASCADE,
    idUC  TEXT REFERENCES uc(codigo) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (idBloco, idUC)
);

CREATE TABLE turmaUC (
    idTurma INTEGER REFERENCES turmas(codigo) ON UPDATE CASCADE ON DELETE CASCADE,
    idUC INTEGER REFERENCES uc(codigo) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (idTurma, idUC)
);

CREATE TABLE turno (
    numero INTEGER,
    idTurma TEXT REFERENCES turmas(codigo) ON UPDATE CASCADE ON DELETE CASCADE,
    idUC TEXT REFERENCES uc(codigo) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY(idTurma, idUC)
);

CREATE TABLE salaBloco (
    idSala TEXT REFERENCES salas(numero) ON UPDATE CASCADE ON DELETE CASCADE,
    idBloco INTEGER REFERENCES blocosVermelhos(id) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (idSala, idBloco)
);

CREATE TABLE aulasSimultaneas(
    aula1 INTEGER REFERENCES aula(id) ON UPDATE CASCADE ON DELETE CASCADE,
    aula2 INTEGER REFERENCES aula(id) ON UPDATE CASCADE ON DELETE CASCADE,
    curso1 TEXT REFERENCES curso(designacao) ON UPDATE CASCADE ON DELETE CASCADE,
    curso2 TEXT REFERENCES curso(designacao) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (aula1, aula2)
);

CREATE TABLE turmasSimultaneas(
    aula1 INTEGER REFERENCES aula(id) ON UPDATE CASCADE ON DELETE CASCADE,
    aula2 INTEGER REFERENCES aula(id) ON UPDATE CASCADE ON DELETE CASCADE,
    turma1 TEXT REFERENCES turmas(codigo) ON UPDATE CASCADE ON DELETE CASCADE,
    turma2 TEXT REFERENCES turmas(codigo) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (aula1, aula2)
)
