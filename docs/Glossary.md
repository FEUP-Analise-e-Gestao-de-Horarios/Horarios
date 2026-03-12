# Glossary

This document defines the canonical English names for domain concepts used throughout the codebase. When in doubt, prefer these terms over ad-hoc translations of Portuguese originals.

## Domain Concepts

| English (use this) | Portuguese original          | Definition                                                                                                         |
| ------------------ | ---------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Degree**         | Curso                        | A degree program, e.g. LEI, MIEI. The top-level grouping of sections.                                              |
| **Subject**        | UC (Unidade Curricular)      | An individual unit of study (module) that students attend sessions of.                                             |
| **Section**        | Turma                        | A scheduled student group within a degree and year, e.g. `1LEI1T`. Not to be confused with a subject or a session. |
| **Session**        | Aula                         | A single scheduled class event. Can be of various types: lecture (Teórica), lab (PL), seminar (S), etc.            |
| **Room**           | Sala                         | A physical space where sessions take place.                                                                        |
| **Teacher**        | Docente                      | A faculty member who teaches sessions.                                                                             |
| **Red Block**      | Bloco vermelho / td_vermelha | A time slot marked as unavailable for a teacher, section, or room.                                                 |

## Page Types

The scraper deals with three kinds of schedule pages:

| Page         | URL owner   | Contains                                                                         |
| ------------ | ----------- | -------------------------------------------------------------------------------- |
| Teacher page | One teacher | Weekly sessions taught by that teacher + unavailable slots                       |
| Section page | One section | Weekly sessions attended by that section + unavailable slots, grouped by subject |
| Room page    | One room    | Weekly sessions held in that room + unavailable slots                            |

## Naming Conventions

- Use the English terms above in all Python identifiers, docstrings, and comments.
- Avoid using `Lesson` (ambiguous), `Class` (conflicts with Python keyword semantics), `Course` (replaced by Subject), or `Curso`/`Turma`/`Aula`/`Docente` in code.
- File and module names follow the page they parse: `teacher_page.py`, `section_page.py`, `room_page.py`.
