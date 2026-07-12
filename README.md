# CV-Pal

Consolida todos los CVs y cartas de presentación de Bruno Vargas Tettamanti en una única base
de conocimiento (`.xlsx` + Google Sheets), y usa esa base con Claude para generar CVs, cartas de
presentación y perfiles de plataformas freelance 100% personalizados, respetando su voz.

## Qué hace

1. **Ingesta** — parsea ~50 documentos (PDF/DOCX/ODT) desde `/home/br1/cv`.
2. **Analytics** — deduplica, normaliza y traduce todo a inglés (idioma estándar de la base).
3. **Knowledge base** — genera `data/cv-knowledge-base.xlsx` (fuente de verdad) y sincroniza a
   Google Sheets.
4. **Voz** — extrae un style guide de las cartas de presentación existentes.
5. **Generación** — dado el link de una oferta, genera CV + carta personalizados (`.docx`/`.pdf`)
   en la voz de Bruno.
6. **Perfiles freelance** — genera borradores de perfil por plataforma (Upwork, Fiverr,
   Superprof, Himalayas) para revisión manual.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # completar ANTHROPIC_API_KEY y credenciales de Google Sheets
```

## Uso

```bash
cvpal ingest
cvpal build-sheet
cvpal sync
cvpal voice
cvpal tailor <url-de-la-oferta>
cvpal profile upwork
```

## Documentación

- `AGENTS.md` — convenciones para agentes de IA (fuente única de verdad)
- `PROJECT_STATUS.md` — estado actual e historial de branches
- `skills/` — guías especializadas por área (extracción, analytics, voz, generación)
