# FEUP Schedule Editor

A web application for analyzing and managing FEUP (Faculty of Engineering, University of Porto)schedules. It ingests timetable data from the institution's website, stores it in per-project SQLite databases, and provides an editor for viewing and resolving scheduling conflicts.

## Documentation

| Document                               | Description                                      |
| -------------------------------------- | ------------------------------------------------ |
| [Setup Guide](docs/setup.md)           | How to run the project locally for development   |
| [Deployment Guide](docs/deployment.md) | How to deploy the project to a production server |
| [Structure](docs/structure.md)         | Repository layout and codebase overview          |
| [Glossary](docs/glossary.md)           | Canonical names for domain concepts              |
| [Page Information](docs/page-information.md) | Data extraction requirements for schedule pages |

## Internals

| Document                                                   | Description                                |
| ---------------------------------------------------------- | ------------------------------------------ |
| [Ingestion Pipeline](docs/internals/ingestion-pipeline.md) | How schedule data is scraped and persisted |

## Refactors

| Document                               | Description                              |
| -------------------------------------- | ---------------------------------------- |
| [Frontend](docs/refactors/frontend.md) | Migration from Django templates to React |
