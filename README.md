# CV-Pal

Consolida todos los CVs y cartas de presentación de Bruno Vargas Tettamanti en una única base
de conocimiento (`data/knowledge-base.md`, editable a mano o por cualquier agente), y la usa
para generar CVs personalizados por oferta de trabajo, respetando su voz. Arquitectura hexagonal:
el motor de IA es intercambiable por variable de entorno — `opencode` hoy, cualquier otro agente
mañana — sin tocar la lógica de negocio. Ver `AGENTS.md` para el detalle de capas.

## Qué hace

1. **Ingesta** — parsea ~50 documentos (PDF/DOCX/ODT) desde `CV_RAW_DIR` (por defecto `/home/br1/cv`).
2. **Knowledge base** — dedupe mecánico + una llamada al agente configurado por sección
   (datos personales, resumen, experiencia, educación, certificaciones, skills, proyectos,
   idiomas, perfil de voz), validado contra modelos tipados y renderizado a
   `data/knowledge-base.md` — la fuente de verdad. `data/cv-knowledge-base.xlsx` es un export
   opcional para revisión en planilla, no autoritativo.
3. **Tailoring** — dada una oferta de trabajo (texto, o archivo `.txt`/`.md`/`.docx`), genera un
   CV en markdown usando únicamente material presente en la base, en el idioma de la oferta.

Pendiente (ver `PROJECT_STATUS.md`): oferta por URL, salida real `.docx`/`.pdf`, carta de
presentación personalizada, sync a Google Sheets, perfiles freelance.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # CV_RAW_DIR, CVPAL_AGENT y overrides de binario/modelo si hace falta
```

## Uso

```bash
cvpal ingest
cvpal kb build
cvpal kb audit
cvpal tailor --job-text "Backend Java, Spring Boot, remoto"
cvpal tailor --job-file oferta.docx --language es
cvpal agents list
cvpal agents check
```

## Documentación

- `AGENTS.md` — convenciones para agentes de IA y arquitectura hexagonal (fuente única de verdad)
- `PROJECT_STATUS.md` — estado actual e historial de branches
- `skills/` — guías especializadas por área (extracción, analytics, voz, generación)
