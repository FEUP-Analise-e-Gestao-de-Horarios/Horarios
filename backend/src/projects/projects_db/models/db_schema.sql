-- This file is only here for reference and documentation,
-- this file is not actually used anywhere

-----------------------------------------------------------
-- Rooms
-----------------------------------------------------------

CREATE TABLE rooms (
    id     UUID PRIMARY KEY,
    name   TEXT UNIQUE NOT NULL,
    type   TEXT,
    size   TEXT,
    seats  TEXT
);

CREATE TABLE room_red_blocks (
    id       UUID PRIMARY KEY,
    hour     INT NOT NULL,
    weekday  TEXT NOT NULL,

    room_id  UUID NOT NULL REFERENCES rooms(id)
);


-----------------------------------------------------------
-- Teachers
-----------------------------------------------------------

CREATE TABLE teachers (
    id       UUID PRIMARY KEY,
    number   INT UNIQUE NOT NULL,
    acronym  TEXT NOT NULL,
    name     TEXT NOT NULL
);

CREATE TABLE teacher_red_blocks (
    id          UUID PRIMARY KEY,
    hour        INT NOT NULL,
    weekday     TEXT NOT NULL,

    teacher_id  UUID NOT NULL REFERENCES teachers(id)
);


-----------------------------------------------------------
-- Subjects
-----------------------------------------------------------

CREATE TABLE degrees (
    id       UUID PRIMARY KEY,
    acronym  TEXT UNIQUE NOT NULL,
    name     TEXT NOT NULL
);

CREATE TABLE years (
    id         UUID PRIMARY KEY,
    number     INT NOT NULL,

    degree_id  UUID NOT NULL REFERENCES degrees(id),

    UNIQUE (degree_id, number)
);

CREATE TABLE subjects (
    id       UUID PRIMARY KEY,
    number   INT UNIQUE NOT NULL,
    code     TEXT UNIQUE NOT NULL,
    acronym  TEXT NOT NULL,
    name     TEXT NOT NULL
);

-- A subject can be taught across several years (shared/optional UCs).
CREATE TABLE subject_years (
    subject_id  UUID NOT NULL REFERENCES subjects(id),
    year_id     UUID NOT NULL REFERENCES years(id),

    PRIMARY KEY (subject_id, year_id)
);


-----------------------------------------------------------
-- Classes
-----------------------------------------------------------

CREATE TABLE classes (
    id       UUID PRIMARY KEY,
    code     TEXT UNIQUE NOT NULL,
    shift    INT NOT NULL,

    year_id  UUID NOT NULL REFERENCES years(id)
);

CREATE TABLE class_red_blocks (
    id        UUID PRIMARY KEY,
    hour      INT NOT NULL,
    weekday   TEXT NOT NULL,

    class_id  UUID NOT NULL REFERENCES classes(id)
);


-----------------------------------------------------------
-- Sessions
-----------------------------------------------------------

CREATE TABLE sessions (
    id                 UUID PRIMARY KEY,
    week               DATE NOT NULL,
    weekday            TEXT NOT NULL,
    start_time         INT NOT NULL,
    duration           INT NOT NULL,
    type               TEXT NOT NULL,
    original_block_id  UUID NOT NULL,

    UNIQUE (week, original_block_id)
);

CREATE TABLE session_rooms (
    session_id  UUID NOT NULL REFERENCES sessions(id),
    room_id     UUID NOT NULL REFERENCES rooms(id),

    PRIMARY KEY (session_id, room_id)
);

CREATE TABLE session_teachers (
    session_id  UUID NOT NULL REFERENCES sessions(id),
    teacher_id  UUID NOT NULL REFERENCES teachers(id),

    PRIMARY KEY (session_id, teacher_id)
);

CREATE TABLE sessions_classes_subject (
    session_id  UUID NOT NULL REFERENCES sessions(id),
    class_id    UUID NOT NULL REFERENCES classes(id),
    subject_id  UUID NOT NULL REFERENCES subjects(id),

    PRIMARY KEY (session_id, class_id, subject_id),
    UNIQUE (session_id, class_id)
);


-----------------------------------------------------------
-- Parallel blocks
-----------------------------------------------------------

CREATE TABLE parallel_block_group_members (
    parallel_block_group_id  UUID NOT NULL,
    original_block_id        UUID NOT NULL,

    PRIMARY KEY (parallel_block_group_id, original_block_id),
    UNIQUE (original_block_id)
);

-- Candidate groups the user has marked as reviewed/confirmed. A subject is
-- confirmed only when every one of its current candidate components is listed
-- here; the candidates endpoint prunes ids that no longer belong to a
-- fully-confirmed subject on every read.
CREATE TABLE parallel_confirmed_candidates (
    candidate_group_id  UUID NOT NULL,

    PRIMARY KEY (candidate_group_id)
);
