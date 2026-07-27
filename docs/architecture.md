# CV-Pal — Arquitectura y funcionamiento

> Nota: este documento quedó en español de una etapa anterior del proyecto y no se tradujo. La
> referencia autoritativa y actualizada para contribuidores es `AGENTS.md` (inglés); `README.md`
> tiene el quickstart. Este archivo es un complemento con más detalle narrativo, no la fuente de
> verdad.

## 1. Visión general

CV-Pal es una herramienta programática y **agent-agnostic** para adaptar CVs y cartas de
presentación a ofertas de trabajo. Consolida CVs/cartas de presentación dispersas, en cualquier
cantidad (PDF, DOCX, ODT, en múltiples stacks e idiomas) en un único **knowledge base**
en inglés (`data/knowledge-base.md`), y luego cualquier agente de IA host (opencode, Claude Code)
lo consume vía MCP para redactar un CV y carta a medida de una oferta — conversacionalmente, en la
voz del autor, solo con material real.

**Decisión central**: el conocimiento es un archivo markdown local (no versionado en git — es dato
personal, ver `CV_DATA_DIR`) — cualquier agente lo lee nativamente, un humano lo edita a mano y lo
diffea. El maintainer del proyecto es el test fixture; el sistema recibe el usuario como
parámetro, sin hardcodearlo.

---

## 2. Arquitectura hexagonal

Estructura en capas, dependencia unidireccional `interfaces → application → domain`.
`infrastructure` implementa los puertos del dominio, y solo `container.py` (composition root)
los conecta — ningún use case o interfaz importa infraestructura directamente.

| Capa | Ubicación | Contenido |
|------|-----------|-----------|
| `domain` | `src/cvpal/domain/` | Modelos pydantic (`documents/`, `knowledge/`, `jobs/`, `generation/`), puertos como `typing.Protocol` (`ports/`), enum `Capability`, jerarquía de errores. Cero imports de infraestructura. |
| `application` | `src/cvpal/application/` | Use cases (`use_cases/`), prompt templates (`prompts/`), servicios puros (`services/` — dedupe, checkpointing, parsing de respuestas, resolución de datos personales, `agent_view.py`, `markdown_sections.py`). Solo depende de `domain`. |
| `infrastructure` | `src/cvpal/infrastructure/` | Adapters: `agents/` (CLI-driven text-completion), `parsers/` (PDF/DOCX/ODT), `persistence/` (markdown/json, checkpoint store), `job_postings/` (text/file/URL sources), `rendering/` (`.docx`/`.pdf` local). |
| `interfaces` | `src/cvpal/interfaces/cli/`, `src/cvpal/interfaces/mcp/` | Dos adaptadores sobre los mismos use cases. Ambos resuelven todo con `container.py`, nunca importan `infrastructure` directamente. |

---

## 3. Pipeline de datos

### 3.1 `cvpal ingest` (sin agente, determinístico)

Recorre todos los archivos en `CV_RAW_DIR` (PDF, DOCX, ODT) y los parsea con:

- **PDF**: `pdfplumber` (con extracción de hipervínculos) + `pdftotext -layout` como fallback
- **DOCX**: `python-docx`
- **ODT**: `odfpy`

**Cache por archivo**: cada `RawDocument` guarda `source_mtime` y `source_size`. En la siguiente
corrida, si coinciden con el archivo en disco, se reusa el documento cacheado — solo los archivos
nuevos o editados pagan el costo de parseo.

Salida: `data/ingested.json` — lista de `RawDocument` con texto plano, metadatos (idioma, tipo de
documento) y warnings de extracción.

**Medido en el corpus real** (48 archivos): segunda corrida sin cambios = 48/48 archivos
saltados, 0.25 s.

### 3.2 `cvpal kb build` (una llamada al agente por sección)

Toma `data/ingested.json`, deduplica el contenido por sección canónica, y para cada una llama al
agente configurado (`CVPAL_AGENT`) con un prompt de extracción que devuelve JSON validado contra
un modelo pydantic del dominio. Un renderer determinístico convierte ese JSON a las tablas
markdown de `data/knowledge-base.md`.

Secciones extraídas (una llamada por sección):

1. `personal_data` — nombre, teléfono, LinkedIn, GitHub, email, dirección
2. `summaries` — variantes del perfil profesional (distintas longitudes/enfoques)
3. `experience` — bullets de experiencia con tech tags, fechas, modalidad, locación
4. `education` + `certifications`
5. `skills` — categorizadas (backend, frontend, databases, devops, etc.) con seniority
6. `projects` — nombre, descripción, rol, stack tecnológico
7. `languages` — idiomas con nivel
8. `voice_profile` — tono, estilo de apertura/cierre, ritmo, frases recurrentes, rasgos por idioma

**Checkpoints content-addressed** (`data/.checkpoints/`, gitignored): cada sección guarda un
fingerprint de su input dedupeado + un `PROMPT_VERSION` constante. Si el fingerprint no cambió,
la sección se saltea con cero llamadas al agente. Antes era existence-based (reusaba el
checkpoint solo porque el archivo existía), lo que obligaba a borrar `.checkpoints` manualmente
ante cualquier cambio.

`KnowledgeBaseBuildReport` retorna `rebuilt_sections` y `skipped_sections` para trazabilidad.

**Medido en el corpus real**: primera corrida = 8 secciones reconstruidas (varios minutos).
Segunda corrida sin cambios = 0 llamadas, 0.26 s.

### 3.3 Resolución determinística de datos personales

El prompt de extracción devuelve **todos** los valores distintos de un campo (ej. tres teléfonos
distintos de CVs de distintas épocas). `application/services/personal_data_resolution.py` aplica
un pase determinístico posterior que marca exactamente uno como `(current)` y el resto como
`(previous)`. Cuál es el valor vigente es un **hecho hardcodeado** (solo el autor lo sabe), nunca
un guess del agente.

---

## 4. Knowledge base

**Estructura**: `data/knowledge-base.md` — fuente de verdad, editable a mano, diff-friendly.
Cada sección es una tabla markdown genérica + un bloque `Notes` libre. Una misma función de
render/parseo funciona para `PersonalDataField`, `ExperienceBullet`, `SkillEntry`, y cualquier
tipo record-based.

### Vistas

| Vista | Fuente | Tamaño (corpus real) | Qué incluye |
|-------|--------|---------------------|-------------|
| Full | `get_knowledge_base` | 58 029 chars (~14.5K tokens) | Todo: `source_files` por hecho, variantes `(previous)` de datos personales, provenance completo. Vista para auditoría humana. |
| Lean | `get_cv_material` / `agent_view.py` | 25 704 chars (~6.4K tokens) | Sin provenance ni variantes `(previous)`. Mantiene todas las variantes de summary, bullets, skills, headlines. **44 % del original, 56 % de reducción**. |

El prompt `cv_pal` completo (lean view + posting real + protocolo) quedó en ~28.8K chars
(~7.2K tokens) end-to-end.

---

## 5. Capa de agentes — provider-agnostic

Todo agente CLI sigue la misma forma: lanzar un binario con un prompt, parsear su stdout.
Esa forma se declara como `CliAgentSpec` (`infrastructure/agents/spec.py`) y se ejecuta con un
único `CliAgentAdapter` genérico.

Agregar un provider nuevo = un spec + un parser en `infrastructure/agents/cli/`, más una línea
en `infrastructure/agents/registry.py`. Cero cambios en use cases.

| Provider | Binario | Estado |
|----------|---------|--------|
| opencode | `opencode` CLI | Default. Modelo `opencode-go/deepseek-v4-pro`. |
| Claude Code | `claude` CLI | Implementado para probar que la abstracción generaliza. |

Selección: `CVPAL_AGENT` (env var, default `opencode`). Override por provider: `<PROVIDER>_BIN`,
`<PROVIDER>_MODEL`.

**Capabilities, no un puerto monolítico**: `domain/capabilities.py:Capability` enum
(`TEXT_COMPLETION`, `JSON_COMPLETION`, `DOCUMENT_RENDER`, `WEB_CONTENT`, `FILE_ATTACH`).
`container.require(*capabilities)` falla al momento del wiring (no mid-pipeline) si el agente
no tiene todo lo necesario.

---

## 6. Servidor MCP — interfaz primaria

### 6.1 ¿Qué es?

`cvpal serve-mcp` levanta un servidor MCP sobre **stdio** con el SDK oficial
(`mcp.server.fastmcp.FastMCP`). Es la misma forma en que opencode/Claude Code ya consumen
engram — cv-pal es una herramienta más en su arsenal.

**Verificado vivo**: registrado y `connected` en `opencode mcp list` y `claude mcp list`.
Dos pruebas end-to-end reales:

- **opencode** (DeepSeek backend) → produjo CV Java/Spring Boot con datos reales (teléfono,
  LinkedIn, GitHub correctos, experiencia real, nada fabricado).
- **Claude Code** → produjo CV PHP/Laravel/fintech seleccionando un subconjunto **distinto**
  y real de experiencia/skills — confirma selección, no templating.

### 6.2 Principio — "el host escribe, cv-pal provee"

cv-pal **nunca** hace una llamada LLM para redactar un CV o carta. La única herramienta que
invoca al agente backend (`CVPAL_AGENT`) es `rebuild_knowledge_base` (extracción batch).
En el hot path de tailoring:

1. cv-pal ensambla material + posting + protocolo en un solo prompt
2. El **modelo del host** redacta y muestra el CV/carta en su propia conversación
3. El usuario itera ("más corto", "enfatizá fintech") gratis, sin round-trip a cv-pal

### 6.3 Superficie expuesta

| Nombre | Tipo | Llama agente | Propósito |
|--------|------|:---:|---|
| `cv_pal` | prompt | no | Ensambla el prompt one-shot (lean KB + posting + protocolo). **Punto de entrada principal.** |
| `get_cv_material` | tool | no | Vista lean como markdown standalone — lo que el host necesita para redactar. |
| `get_knowledge_base` | tool | no | Markdown completo (con provenance), todo o una sección. |
| `update_knowledge_base` | tool | no | Edición iniciada por el host; valida contra heurística de near-total-wipe, hace backup, escribe. |
| `audit_knowledge_base` | tool | no | Campos de datos personales con más de un valor distinto en el corpus. |
| `ingest_corpus` | tool | no | Re-escanea `CV_RAW_DIR`, salta archivos sin cambios. |
| `rebuild_knowledge_base` | tool | **sí** | Regenera la KB desde cero o incremental; cero llamadas si nada cambió (por checkpointing content-addressed). |
| `render_document` | tool | no | Markdown → `.docx`/`.pdf` real con `python-docx` + `soffice --headless`. Sin agente, sin API key. |

### 6.4 El prompt `cv_pal` en detalle

`application/prompts/cv_pal.py:cv_pal_prompt()` arma un único prompt one-shot con tres bloques:

**Reglas**:
- Usar **solo** material del knowledge base. Nunca inventar skills, roles, empresas, fechas,
  certificaciones o proyectos ausentes.
- Seleccionar el subconjunto de experiencia, skills y proyectos **relevante al posting**.
- Escribir en `{language}` (detectado del posting, o pasado por el usuario; default `en`).

**Protocolo** (3 pasos):
1. Redactar el CV a medida e **imprimir el texto completo** en la conversación (markdown plano,
   listo para leer). No solo describirlo — mostrarlo.
2. Preguntar al usuario si también quiere carta de presentación.
3. Si sí → **branch según perfil de voz**:
   - **Sin perfil capturado**: preguntar tono deseado / ofrecer ejemplo de apertura / preguntar
     qué 2-3 aspectos resaltar. Usar la respuesta para escribir.
   - **Con perfil capturado**: resumir la esencia del tono y estilo de apertura en 1-2 oraciones,
     preguntar si es correcto o si quiere ajustarlo. Usar la confirmación (o el perfil tal cual)
     para escribir.

**Knowledge base** + **Job posting**: el lean view markdown y el texto del posting se inyectan
directamente en el prompt.

Esto hace que el tailoring sea **conversacional**, no fire-and-forget — especialmente la carta,
que requiere confirmar o elicitar la voz del autor.

### 6.5 Patrón de implementación

Cada handler en `server.py` sigue el mismo patrón:

```python
# Función privada testeable — recibe el Container explícitamente
def _verb(container: Container, ...) -> str:
    # lógica real, llama use cases / servicios de application/
    ...

# Decorador MCP — thin wrapper, sin lógica
@mcp.tool()
def verb(...) -> str:
    return _verb(_container(), ...)
```

- Las funciones `_verb` son las que se testean directamente (sin protocolo MCP, sin env vars,
  sin proceso real). Ver `tests/interfaces/test_mcp_server.py`.
- Las funciones decoradas **no tienen parámetros extra** — todo lo que aceptan va al schema
  que ve el agente host.
- `interfaces/mcp/server.py` **nunca** importa `infrastructure` directamente. Verificable con:
  ```bash
  grep -rln "cvpal.infrastructure" src/cvpal/interfaces/mcp   # debe estar vacío
  ```

**KB faltante**: cada handler chequea `container.knowledge_repository.exists()` primero. Si no
hay KB, devuelve `_NO_KB_MESSAGE` — un puntero a `cvpal kb build` / `rebuild_knowledge_base`
para que el host se lo muestre al usuario, en vez de crashear.

### 6.6 Configuración del cliente

**opencode** (`~/.config/opencode/opencode.jsonc`):
```jsonc
{
  "mcp": {
    "cvpal": {
      "command": ["/path/to/cv-pal/.venv/bin/cvpal", "serve-mcp"],
      "enabled": true,
      "type": "local"
    }
  }
}
```

**Claude Code**:
```bash
claude mcp add cvpal -- /path/to/cv-pal/.venv/bin/cvpal serve-mcp
```

Ambos apuntan al mismo binario sobre stdio.

### 6.7 Flujo end-to-end típico

```
Usuario: "Armame un CV para esta oferta de Java/Spring Boot" [pega el texto]

  1. El host (opencode/Claude Code) invoca el prompt cv_pal o la tool get_cv_material

  2. cv_pal handler:
     ├── Verifica que data/knowledge-base.md existe
     ├── Verifica que viene exactamente uno de job_posting_text o job_posting_file
     ├── Resuelve la fuente (JobPostingSourcePort)
     ├── Detecta idioma del posting
     ├── Carga KB, proyecta a lean view (render_agent_view)
     └── Arma el prompt one-shot: reglas + protocolo + lean KB + posting

  3. El modelo del host:
     ├── Redacta el CV (solo material real, subconjunto relevante)
     ├── Imprime el markdown completo en la conversación
     ├── Pregunta: "¿Querés también una carta de presentación?"
     └── Si sí → branch de voz → redacta la carta → la imprime

  4. Usuario: "dale, exportalo a PDF"
     └── Host llama render_document(markdown, "pdf", "cv-acme-backend.pdf")
         └── python-docx + soffice --headless → data/outputs/cv-acme-backend.pdf
```

### 6.8 Renderizado de documentos

`infrastructure/rendering/local_document_renderer.py` convierte markdown a archivos reales sin
agente ni API key:

- **Markdown → `.docx`**: `python-docx` directamente (headings, bold, bullets, párrafos).
- **`.docx` → `.pdf`**: `soffice --headless --convert-to pdf` sobre un `.docx` temporal.
  LibreOffice ya estaba instalado en esta máquina todo el tiempo — el proyecto previamente
  asumió que hacía falta Anthropic Agent Skills para esto.

Wiredo en `cvpal tailor --format docx|pdf` (CLI) y en la tool MCP `render_document`.
Los tests generan PDF real con `soffice` (skipeado si no está instalado) y validan con magic
bytes `%PDF`; los `.docx` se reabren con `python-docx` y se validan headings/bullets/bold.

---

## 7. `update_knowledge_base` — edición host-initiated

Permite que el host edite la KB (agregar un proyecto, tweakear un bullet, guardar un perfil de
voz recién elicitado). El flujo:

1. El host edita el markdown y lo pasa como string a `update_knowledge_base(markdown=..., force=False)`
2. `application/use_cases/update_knowledge_base.py` parsea el markdown entrante, compara cantidad
   de registros por sección contra la KB actual.
3. Si la caída supera un umbral de retención, **rechaza** el update (potencial near-total-wipe
   por input corrupto) a menos que `force=True`.
4. Si se acepta, hace **backup** de la KB anterior y escribe la nueva.

El parser de markdown es deliberadamente tolerante (objetivo de diseño: editabilidad humana), lo
que significa que "parsea sin errores" no es un safety check suficiente — input basura igual
parsea, solo que produce una KB casi vacía. De ahí la heurística de conteo de registros.

---

## 8. Resiliencia y performance

| Mecanismo | Capa | Qué logra |
|-----------|------|-----------|
| Cache mtime/size en ingest | `ingest_documents.py` | Solo archivos nuevos/editados pagan parseo. 48/48 saltados = 0.25 s. |
| Checkpoints content-addressed | `build_knowledge_base.py` + `checkpointing.py` | Solo secciones con input cambiado llaman al agente. 0/8 secciones = 0.26 s. |
| Lean agent view | `agent_view.py` | 56 % de reducción de tokens vs la KB completa. El prompt armado cabe en ~7.2K tokens. |
| Per-section agent calls | `build_knowledge_base.py` | Una call pequeña por sección evita que respuestas grandes se trunquen (problema conocido en modos CLI no interactivos). |
| `source_files` capped a 3 | `dedupe.py` | Previene que facts universales (skill en 30+ CVs) inflen el JSON al punto de truncamiento. |
| `PROMPT_VERSION` por módulo | `checkpointing.py` + `prompts/` | Bump manual cuando cambia la semántica del prompt, invalida checkpoints de esa sección. |
| `_NO_KB_MESSAGE` en vez de crash | `server.py` | KB faltante = mensaje guiado al host, no excepción. |

---

## 9. Estado actual y próximos pasos

### Completado y verificado

- Pipeline de ingesta con cache por archivo
- Knowledge base en markdown como fuente de verdad (8 secciones, corpus real de 48 archivos)
- Capa de agentes provider-agnostic (opencode default, Claude Code como prueba de abstracción)
- Servidor MCP como interfaz primaria (7 tools + 1 prompt, verificado vivo en ambos clientes)
- Renderizado local `.docx`/`.pdf` sin agente ni API key
- Checkpointing content-addressed (incremental real: 0 llamadas cuando nada cambió)
- Lean agent view (~56 % de reducción de tokens)
- `update_knowledge_base` con heurística anti-wipe
- Auditoría de datos personales inconsistentes

### Pendiente

1. Verificación interactiva del **prompt** `cv_pal` (no solo el tool `get_cv_material`) —
   el prompt en sí se observó con slash-command explícito en sesión interactiva; queda
   pendiente el end-to-end con el branch conversacional de la carta.
2. `WebContentPort` adapter para ofertas por URL.
3. Fix del artifact de extracción de la URL del certificado UTN (dos links concatenados
   en el PDF fuente).
4. Perfiles freelance (`feature/freelance-profiles`).
5. Web job search (`feature/web-job-search`).
7. Transport HTTP/SSE de MCP (deliberadamente fuera de v1).
8. Standalone cover-letter use case para la CLI.

---

## 10. Comandos de referencia

```bash
source .venv/bin/activate

# Pipeline
cvpal ingest                  # Parsear CVs → data/ingested.json
cvpal kb build                # Construir KB → data/knowledge-base.md
cvpal kb audit                # Auditar datos personales inconsistentes

# Tailoring (CLI)
cvpal tailor --job-text "..." --format pdf
cvpal tailor --job-file posting.docx --language es --format docx

# MCP (interfaz primaria)
cvpal serve-mcp               # Arranca el server MCP sobre stdio

# Agentes
cvpal agents list             # Providers registrados
cvpal agents check            # Round-trip trivial contra el provider activo

# Validación
ruff check src tests && pytest
```
