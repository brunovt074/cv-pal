# CV-Pal

Herramienta programática y agnóstica de agente para adaptar CVs y cartas de presentación a
ofertas de trabajo. Se consume como servidor MCP por stdio desde tu agente de IA — opencode,
Claude Code — igual que ya consumís engram: le pedís que use cv-pal, lee tu base de conocimiento
real y redacta el CV/carta él mismo, conversando con vos. También existe un CLI (`cvpal ...`) como
vía secundaria. Arquitectura hexagonal: el motor de IA que arma la base de conocimiento es
intercambiable por variable de entorno — `opencode` hoy, cualquier otro agente mañana — sin tocar
la lógica de negocio. Ver `AGENTS.md` para el detalle de capas.

## Qué hace

1. **Ingesta** — parsea documentos (PDF/DOCX/ODT) desde `CV_RAW_DIR`, saltando los archivos que
   no cambiaron desde la última corrida.
2. **Knowledge base** — dedupe mecánico + una llamada al agente configurado por sección
   (datos personales, resumen, experiencia, educación, certificaciones, skills, proyectos,
   idiomas, perfil de voz), validado contra modelos tipados y renderizado a
   `data/knowledge-base.md` — la fuente de verdad. Cada sección solo se recalcula si su contenido
   realmente cambió (checkpointing por fingerprint) — segura de correr seguido, sin costo si nada
   cambió. `data/cv-knowledge-base.xlsx` es un export opcional para revisión en planilla, no
   autoritativo.
3. **Servidor MCP** (`cvpal serve-mcp`) — el agente que ya usás pide una vista liviana de la base
   (sin metadata de trazabilidad, ~44% del tamaño completo) + la propuesta de trabajo, y él mismo
   redacta el CV y, conversando, la carta de presentación — preguntando el tono si no tiene tu voz
   capturada, o confirmándola si ya la tiene. cv-pal nunca hace una llamada a LLM anidada para
   esto; solo `rebuild_knowledge_base` usa el agente configurado.
4. **Render de documentos** — `.docx`/`.pdf` reales generados localmente (`python-docx` +
   `soffice`), sin agente ni API key.
5. **CLI** (`cvpal tailor`) — vía secundaria no conversacional, mismo resultado en un solo paso.

Pendiente (ver `PROJECT_STATUS.md`): oferta por URL, carta de presentación no conversacional para
el CLI, sync a Google Sheets, perfiles freelance.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # CV_RAW_DIR, CVPAL_AGENT y overrides de binario/modelo si hace falta
```

## Uso desde tu agente (vía principal)

```bash
cvpal serve-mcp
```

Configurá tu agente para levantarlo como servidor MCP local — ver `skills/mcp-server/SKILL.md`
para el bloque de config exacto de opencode y Claude Code. Una vez conectado, pedile a tu agente
que use cv-pal para adaptar tu CV a una oferta.

## Uso por CLI (vía secundaria)

```bash
cvpal ingest
cvpal kb build
cvpal kb audit
cvpal tailor --job-text "Backend Java, Spring Boot, remoto" --format pdf
cvpal tailor --job-file oferta.docx --language es --format docx
cvpal agents list
cvpal agents check
```

## Documentación

- `AGENTS.md` — convenciones para agentes de IA y arquitectura hexagonal (fuente única de verdad)
- `PROJECT_STATUS.md` — estado actual e historial de branches
- `skills/` — guías especializadas por área (extracción, analytics, voz, generación, servidor MCP)
