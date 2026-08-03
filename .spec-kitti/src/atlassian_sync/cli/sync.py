#!/usr/bin/env python3
"""
Spec-Kitti Sync - Sincroniza épica de Jira + documentación de Confluence
Script principal para el comando /spec-kitti.sync
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
import logging

from ..atlassian.config import AtlassianConfig
from ..atlassian.jira import JiraClient
from ..atlassian.confluence import ConfluenceClient
from ..utils.helpers import sanitize_filename, split_issues_by_type
from ..utils.logger import setup_logger

logger = logging.getLogger(__name__)


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Sincroniza épica de Jira y/o documentación de Confluence y genera spec.md',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Solo Jira (épica + historias)
  %(prog)s --mode jira --epic-key PROJ-123

  # Solo Confluence (sin Jira)
  %(prog)s --mode confluence --confluence-parent "API Documentation"

  # Jira + Confluence (comportamiento por defecto)
  %(prog)s --mode both --epic-key PROJ-123 --confluence-parent "API Documentation"

  # Desde archivo .env
  %(prog)s --env-file .env --mode jira --epic-key PROJ-123

  # Con todas las opciones
  %(prog)s --mode both --epic-key PROJ-123 --confluence-parent "API Docs" --output ./specs/my-feature

Configuración desde variables de entorno:
  export JIRA_EMAIL="tu@email.com"
  export JIRA_API_TOKEN="ATATxxxxxxxxxx"
  export JIRA_BASE_URL="https://empresa.atlassian.net"
  export CONFLUENCE_BASE_URL="https://otra-empresa.atlassian.net"  # opcional — si Confluence está en otro dominio
  export CONFLUENCE_SPACE_KEY="TECH"  # requerido para modo confluence/both
        """
    )

    # Modo de sincronización
    parser.add_argument(
        '--mode',
        choices=['jira', 'confluence', 'both'],
        default='both',
        help='Qué fuentes sincronizar: "jira" (épica + historias), "confluence" (solo docs) o "both" (ambas). Default: both'
    )

    # Argumentos de Jira (requeridos en modo jira/both)
    parser.add_argument(
        '--epic-key',
        help='Key de la épica a importar (ej: PROJ-123) — requerido en modo jira/both'
    )

    # Argumentos de Confluence
    parser.add_argument(
        '--confluence-parent',
        help='Título de la página padre en Confluence (ej: "API Documentation")'
    )

    parser.add_argument(
        '--issue-keys',
        help='Lista de issue keys separados por coma (ej: "PROJ-1,PROJ-2") - usar si la búsqueda automática falla'
    )

    parser.add_argument(
        '--env-file',
        type=Path,
        default=Path('.env'),
        help='Archivo .env con credenciales (default: .env en directorio actual)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        help='Directorio de salida (default: .spec-kitti/)'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Nivel de logging (default: INFO)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Salida en formato JSON para integración con scripts'
    )

    args = parser.parse_args()

    # Validación temprana de argumentos mutuamente dependientes
    if args.mode in ('jira', 'both') and not args.epic_key:
        parser.error(f"--epic-key es requerido cuando --mode es '{args.mode}'")
    
    try:
        # Configurar logging
        setup_logger(args.log_level)

        sync_mode = args.mode

        if not args.json:
            print(f"\n{'='*70}")
            print("🔄 Spec-Kitti Sync - Atlassian Integration")
            mode_label = {"jira": "Solo Jira", "confluence": "Solo Confluence", "both": "Jira + Confluence"}
            print(f"   Modo: {mode_label[sync_mode]}")
            print(f"{'='*70}\n")

        # Cargar configuración
        if args.env_file.exists():
            config = AtlassianConfig.from_dotenv(
                args.env_file,
                args.epic_key,
                args.confluence_parent,
                sync_mode=sync_mode,
            )
            if not args.json:
                print(f"✅ Configuración cargada desde {args.env_file}")
        else:
            config = AtlassianConfig.from_env(
                args.epic_key,
                args.confluence_parent,
                sync_mode=sync_mode,
            )
            if not args.json:
                print("✅ Configuración cargada desde variables de entorno")

        if args.output:
            config.output_dir = str(args.output)

        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Crear clientes según el modo — cada uno usa su propio base_url
        jira_client = JiraClient(config.jira_base_url, config.email, config.api_token) if sync_mode in ("jira", "both") else None
        confluence_client = None
        if sync_mode in ("confluence", "both") and config.confluence_space_key:
            confluence_client = ConfluenceClient(config.effective_confluence_base_url, config.email, config.api_token)

        # ========== PASO 1, 2 & 3: Jira (épica + historias + subtareas) ==========
        epic = None
        epic_summary = "confluence-only"
        stories: list = []
        subtasks_by_parent: dict = {}

        if sync_mode in ("jira", "both"):
            # Modo both: 5 pasos (épica, historias, subtareas, confluence, consolidar)
            # Modo jira: 4 pasos (épica, historias, subtareas, consolidar)
            total_steps = 5 if sync_mode == "both" else 4
            if not args.json:
                print(f"\n📥 Paso 1/{total_steps}: Descargando épica {config.epic_key}...")

            epic = jira_client.get_issue_by_key(config.epic_key)
            epic_summary = epic['fields']['summary']

            if not args.json:
                print(f"   ✅ Épica: {epic_summary}")

            logger.info(f"Épica descargada: {config.epic_key}")

            if not args.json:
                print(f"\n📥 Paso 2/{total_steps}: Descargando historias/tareas de la épica...")

            if args.issue_keys:
                issue_keys = [k.strip() for k in args.issue_keys.split(',')]
                if not args.json:
                    print(f"   📋 Descargando {len(issue_keys)} issues especificados manualmente...")

                for issue_key in issue_keys:
                    try:
                        issue = jira_client.get_issue_by_key(issue_key)
                        stories.append(issue)
                        if not args.json:
                            print(f"   ✅ {issue_key}: {issue['fields']['summary']}")
                    except Exception as e:
                        if not args.json:
                            print(f"   ⚠️  {issue_key}: Error - {e}")
                        logger.warning(f"No se pudo descargar {issue_key}: {e}")
            else:
                stories = jira_client.get_issues_by_epic(config.epic_key)

            # Desglose por tipo según el modelo: épica → tareas / épica → historias → subtareas
            split = split_issues_by_type(stories)
            n_stories, n_tasks, n_other = len(split['stories']), len(split['tasks']), len(split['other'])

            if not args.json:
                print(f"   ✅ {len(stories)} hijos directos: {n_stories} historias, {n_tasks} tareas"
                      + (f", {n_other} otros" if n_other else ""))

            logger.info(
                f"Hijos de la épica: total={len(stories)} | "
                f"historias={n_stories} | tareas={n_tasks} | otros={n_other}"
            )

            # ── Paso 3: descargar subtareas de las historias ──────────────────
            # Modelo del proyecto:
            #   - Las TAREAS son hijos directos de la épica y NO tienen subtareas.
            #   - Las HISTORIAS son hijos directos de la épica y SÍ tienen subtareas.
            # Aún así llamamos get_subtasks_for_issues con TODOS los hijos: si una
            # tarea no tiene subtareas simplemente no se agrega al dict resultado.
            if not args.json:
                print(f"\n📥 Paso 3/{total_steps}: Descargando subtareas de las historias...")

            if stories:
                subtasks_by_parent = jira_client.get_subtasks_for_issues(stories)
                total_subtasks = sum(len(v) for v in subtasks_by_parent.values())

                # Conteo: cuántas historias/tareas tuvieron subtareas
                story_keys = {s['key'] for s in split['stories']}
                task_keys = {t['key'] for t in split['tasks']}
                stories_with_subs = sum(1 for k in subtasks_by_parent if k in story_keys)
                tasks_with_subs = sum(1 for k in subtasks_by_parent if k in task_keys)

                if not args.json:
                    if total_subtasks:
                        print(f"   ✅ {total_subtasks} subtareas descargadas")
                        print(f"      • {stories_with_subs}/{n_stories} historias tienen subtareas")
                        if tasks_with_subs:
                            print(f"      • ⚠️  {tasks_with_subs} tareas tienen subtareas (no esperado en el modelo)")
                    else:
                        print(f"   ℹ️  No se encontraron subtareas en los hijos de la épica")

                logger.info(
                    f"Subtareas: total={total_subtasks} | "
                    f"historias_con_subtareas={stories_with_subs}/{n_stories} | "
                    f"tareas_con_subtareas={tasks_with_subs}/{n_tasks}"
                )
            else:
                if not args.json:
                    print(f"   ⏭️  Saltando subtareas (no hay hijos de la épica)")

            # Guardar datos crudos de Jira
            jira_data_dir = output_dir / "jira_raw"
            jira_data_dir.mkdir(exist_ok=True)

            with open(jira_data_dir / f"{config.epic_key}_epic.json", 'w', encoding='utf-8') as f:
                json.dump(epic, f, indent=2, ensure_ascii=False)

            with open(jira_data_dir / f"{config.epic_key}_stories.json", 'w', encoding='utf-8') as f:
                json.dump(stories, f, indent=2, ensure_ascii=False)

            if subtasks_by_parent:
                with open(jira_data_dir / f"{config.epic_key}_subtasks.json", 'w', encoding='utf-8') as f:
                    json.dump(subtasks_by_parent, f, indent=2, ensure_ascii=False)

        else:
            if not args.json:
                print(f"\n⏭️  Pasos 1-3: Saltando Jira (modo={sync_mode})")

        # ========== PASO 4 (o 1 en modo confluence): Descargar Confluence ==========
        confluence_pages = []

        if sync_mode in ("confluence", "both"):
            step_num = 4 if sync_mode == "both" else 1
            total_steps = 5 if sync_mode == "both" else 2
            if not args.json:
                print(f"\n📥 Paso {step_num}/{total_steps}: Descargando documentación de Confluence...")
                print(f"   Space: {config.confluence_space_key}")
                if config.confluence_parent_page:
                    print(f"   Página padre: {config.confluence_parent_page}")
                else:
                    print(f"   Descargando TODO el space")

            try:
                if config.confluence_parent_page:
                    parent_page = confluence_client.get_page_by_title(
                        config.confluence_space_key,
                        config.confluence_parent_page
                    )

                    if parent_page:
                        confluence_pages = download_confluence_tree_recursive(
                            confluence_client,
                            parent_page['id'],
                            output_dir / "confluence_raw"
                        )

                        if not args.json:
                            print(f"   ✅ {len(confluence_pages)} páginas descargadas")

                        logger.info(f"{len(confluence_pages)} páginas de Confluence descargadas")
                    else:
                        if not args.json:
                            print(f"   ⚠️  Página '{config.confluence_parent_page}' no encontrada")
                        logger.warning(f"Página padre '{config.confluence_parent_page}' no encontrada")
                else:
                    all_pages = confluence_client.get_space_pages(config.confluence_space_key)

                    for page in all_pages:
                        page_file = output_dir / "confluence_raw" / f"{page['id']}_{sanitize_filename(page['title'])}.json"
                        page_file.parent.mkdir(parents=True, exist_ok=True)

                        with open(page_file, 'w', encoding='utf-8') as f:
                            json.dump(page, f, indent=2, ensure_ascii=False)

                        confluence_pages.append(page)

                    if not args.json:
                        print(f"   ✅ {len(confluence_pages)} páginas descargadas del space completo")

                    logger.info(f"{len(confluence_pages)} páginas descargadas del space completo")

            except Exception as e:
                if not args.json:
                    print(f"   ⚠️  Error descargando Confluence: {e}")
                logger.error(f"Error descargando Confluence: {e}")

        else:
            if not args.json:
                print(f"\n⏭️  Paso 4/5: Saltando Confluence (modo={sync_mode})")

        # ========== PASO FINAL: Generar sync_context.md + import_report.md ==========
        # Numeración:
        #   - both:        paso 5/5
        #   - jira:        paso 4/4 (épica, historias, subtareas, consolidar)
        #   - confluence:  paso 2/2 (confluence, consolidar)
        last_step = 5 if sync_mode == "both" else (4 if sync_mode == "jira" else 2)
        total_steps = last_step
        if not args.json:
            print(f"\n📦 Paso {last_step}/{total_steps}: Consolidando datos descargados...")

        # Generar sync_context.md — resumen estructurado para que el agente lo use en /spec-kitti.specify
        context_file = output_dir / "sync_context.md"
        context_content = generate_sync_context(config, epic, stories, subtasks_by_parent, confluence_pages)
        with open(context_file, 'w', encoding='utf-8') as f:
            f.write(context_content)

        if not args.json:
            print(f"   ✅ Contexto de sync: {context_file.name}")

        # Generar reporte de importación
        report = generate_import_report(config, epic, stories, subtasks_by_parent, confluence_pages)
        report_file = output_dir / "import_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        if not args.json:
            print(f"   ✅ Reporte de importación: {report_file.name}")

        # ========== Salida final ==========
        total_subtasks = sum(len(v) for v in subtasks_by_parent.values())
        split_final = split_issues_by_type(stories) if stories else {'stories': [], 'tasks': [], 'other': []}
        n_stories_f = len(split_final['stories'])
        n_tasks_f = len(split_final['tasks'])
        n_other_f = len(split_final['other'])

        if args.json:
            result = {
                "success": True,
                "sync_mode": sync_mode,
                "epic_key": config.epic_key,
                "epic_title": epic_summary if epic else None,
                "children_count": len(stories),
                "stories_count": n_stories_f,
                "tasks_count": n_tasks_f,
                "other_count": n_other_f,
                "subtasks_count": total_subtasks,
                "subtasks_by_parent": {k: len(v) for k, v in subtasks_by_parent.items()},
                "confluence_pages_count": len(confluence_pages),
                "context_file": str(context_file.absolute()),
                "report_file": str(report_file.absolute()),
                "output_dir": str(output_dir.absolute()),
                "next_step": "/spec-kitti.specify"
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"\n{'='*70}")
            print("✅ ¡Datos sincronizados correctamente!")
            print(f"{'='*70}")
            print(f"\n📊 Resumen:")
            if epic:
                print(f"   • Épica: {config.epic_key} - {epic_summary}")
                print(f"   • Hijos directos de la épica: {len(stories)}")
                print(f"      ├── Historias: {n_stories_f}" + (f" ({total_subtasks} subtareas)" if total_subtasks else ""))
                print(f"      └── Tareas:    {n_tasks_f}")
                if n_other_f:
                    print(f"      └── Otros:     {n_other_f}")
            if confluence_pages:
                print(f"   • Páginas de Confluence: {len(confluence_pages)}")
            print(f"\n📁 Archivos en {output_dir.absolute()}:")
            print(f"   • sync_context.md  ← input listo para generar el spec")
            print(f"   • import_report.md ← resumen de la importación")
            if sync_mode in ("jira", "both"):
                print(f"   • jira_raw/        ← datos crudos de Jira en JSON")
                print(f"     ├── {config.epic_key}_epic.json")
                print(f"     ├── {config.epic_key}_stories.json  (historias + tareas)")
                if subtasks_by_parent:
                    print(f"     └── {config.epic_key}_subtasks.json (subtareas por historia)")
            if confluence_pages:
                print(f"   • confluence_raw/  ← páginas de Confluence en Markdown")
            print(f"\n{'='*70}")
            print("🤖 [AGENT] Ahora genera el spec.md leyendo sync_context.md")
            print(f"{'='*70}")
            print()

        return 0
    
    except KeyboardInterrupt:
        if not args.json:
            print("\n\n⚠️  Proceso interrumpido por el usuario")
        return 130
    
    except Exception as e:
        if args.json:
            result = {
                "success": False,
                "error": str(e)
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"\n❌ Error: {e}")
            logger.error(f"Error durante la sincronización: {e}", exc_info=True)
        return 1


def download_confluence_tree_recursive(client: ConfluenceClient, page_id: str, output_dir: Path) -> list:
    """
    Descarga recursivamente un árbol de páginas de Confluence
    
    Args:
        client: Cliente de Confluence
        page_id: ID de la página raíz
        output_dir: Directorio de salida
        
    Returns:
        Lista de páginas descargadas con markdown_content
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pages = []
    
    def download_recursive(pid: str):
        page = client.get_page_by_id(pid)
        
        # Convertir HTML a Markdown si hay contenido
        markdown_content = ""
        page_type = page.get('type', 'page')
        
        if page_type == 'page':
            # Solo convertir si es una página real (no folder)
            body_html = page.get('body', {}).get('storage', {}).get('value', '')
            if body_html:
                try:
                    import html2text
                    h = html2text.HTML2Text()
                    h.ignore_links = False
                    h.ignore_images = False
                    h.ignore_emphasis = False
                    markdown_content = h.handle(body_html)
                except Exception as e:
                    logger.warning(f"Error convirtiendo HTML a Markdown para {page['title']}: {e}")
                    markdown_content = body_html
        
        # Agregar markdown_content al diccionario de la página
        page['markdown_content'] = markdown_content
        
        # Solo agregar a la lista si tiene contenido (excluir folders vacíos)
        if page_type == 'page' and markdown_content.strip():
            pages.append(page)
        
        # Guardar JSON crudo
        page_file = output_dir / f"{page['id']}_{sanitize_filename(page['title'])}.json"
        with open(page_file, 'w', encoding='utf-8') as f:
            json.dump(page, f, indent=2, ensure_ascii=False)
        
        # Guardar archivo Markdown si tiene contenido
        if markdown_content.strip():
            md_file = output_dir / f"{page['id']}_{sanitize_filename(page['title'])}.md"
            
            # Crear header con metadata
            md_header = f"""# {page['title']}

**Confluence Page ID:** {page['id']}  
**Type:** {page_type}  
**Last Updated:** {page.get('version', {}).get('when', 'Unknown')}  
**URL:** {page.get('_links', {}).get('webui', '')}

---

"""
            
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(md_header + markdown_content)
            
            logger.debug(f"Guardado Markdown: {md_file}")
        
        # Descargar páginas hijas (siempre, incluso de folders)
        try:
            children = client.get_page_children(pid)
            for child in children:
                download_recursive(child['id'])
        except Exception as e:
            logger.warning(f"Error descargando hijas de {page['title']}: {e}")
    
    download_recursive(page_id)
    
    return pages


def generate_sync_context(
    config: AtlassianConfig,
    epic: dict | None,
    stories: list,
    subtasks_by_parent: dict,
    confluence_pages: list,
) -> str:
    """
    Genera sync_context.md — archivo de contexto estructurado que el agente
    usará como input para ejecutar /spec-kitti.specify.

    Estructura el contenido reflejando el modelo de jerarquía del proyecto:
      Épica
        ├── Tarea       (hijo directo, sin subtareas)
        └── Historia    (hijo directo, con subtareas)

    Args:
        config: Configuración de Atlassian
        epic: Datos de la épica (o None si modo confluence)
        stories: Lista de hijos directos de la épica (Stories + Tasks + otros)
        subtasks_by_parent: Dict {parent_key: [subtareas]} con las subtareas
                            agrupadas por su issue padre (típicamente historias)
        confluence_pages: Lista de páginas de Confluence descargadas
    """
    from ..utils.helpers import extract_text_from_adf, get_issue_type, split_issues_by_type

    def render_issue_header(issue: dict, level: str = "###") -> list[str]:
        """Renderiza el encabezado y metadatos comunes de un issue."""
        fld = issue.get('fields', {}) or {}
        desc = fld.get('description') or ''
        if isinstance(desc, dict):
            desc = extract_text_from_adf(desc)
        points = fld.get('story_points') or fld.get('customfield_10016') or 'TBD'
        out = [
            f"{level} [{issue['key']}] {fld.get('summary', '')}\n",
            f"**Tipo:** {get_issue_type(issue)} | "
            f"**Prioridad:** {(fld.get('priority') or {}).get('name', 'N/A')} | "
            f"**Story Points:** {points} | "
            f"**Estado:** {(fld.get('status') or {}).get('name', 'N/A')}  ",
        ]
        if desc:
            out.append(f"\n{desc}\n")
        return out

    lines: list[str] = []
    lines.append("# Sync Context — Input para /spec-kitti.specify")
    lines.append(f"\n**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    lines.append(f"**Modo:** {config.sync_mode}  ")

    if epic:
        lines.append(f"**Épica Jira:** [{epic['key']}]({config.jira_base_url}/browse/{epic['key']})  ")

    lines.append("\n---\n")

    # ── Sección Jira ──────────────────────────────────────────────────────────
    if epic:
        fields = epic.get('fields', {})
        description = fields.get('description') or ''
        if isinstance(description, dict):
            description = extract_text_from_adf(description)

        lines.append("## Épica de Jira\n")
        lines.append(f"**Key:** {epic['key']}  ")
        lines.append(f"**Título:** {fields.get('summary', '')}  ")
        lines.append(f"**Estado:** {fields.get('status', {}).get('name', 'N/A')}  ")
        lines.append(f"**Prioridad:** {fields.get('priority', {}).get('name', 'N/A')}  ")

        if description:
            lines.append(f"\n**Descripción:**\n\n{description}\n")

        if stories:
            split = split_issues_by_type(stories)
            tasks = split['tasks']
            stories_only = split['stories']
            others = split['other']
            total_subtasks = sum(len(v) for v in subtasks_by_parent.values())

            # Resumen jerárquico para el agente
            lines.append("\n### Jerarquía descargada\n")
            lines.append("```")
            lines.append(f"{epic['key']} — {fields.get('summary', '')}")
            if tasks:
                lines.append(f"├── Tareas ({len(tasks)})  — hijos directos, sin subtareas")
                for t in tasks:
                    lines.append(f"│    • {t['key']} — {t['fields'].get('summary', '')}")
            if stories_only:
                lines.append(f"└── Historias ({len(stories_only)}) — hijos directos, con subtareas")
                for s in stories_only:
                    sub_count = len(subtasks_by_parent.get(s['key'], []))
                    suffix = f" ({sub_count} subtareas)" if sub_count else " (sin subtareas)"
                    lines.append(f"     • {s['key']} — {s['fields'].get('summary', '')}{suffix}")
            if others:
                lines.append(f"└── Otros tipos ({len(others)})")
                for o in others:
                    lines.append(f"     • {o['key']} [{get_issue_type(o)}] — {o['fields'].get('summary', '')}")
            lines.append("```\n")

            # ── Tareas directas (sin subtareas según el modelo) ───────────────
            if tasks:
                lines.append(f"\n## Tareas directas de la épica ({len(tasks)})\n")
                lines.append("> Hijos directos de la épica de tipo **Task**. En este modelo no llevan subtareas.\n")
                for task in tasks:
                    lines.extend(render_issue_header(task, level="###"))
                    # Si por alguna razón una tarea tuviera subtareas, las mostramos como advertencia
                    task_subs = subtasks_by_parent.get(task['key'], [])
                    if task_subs:
                        lines.append(f"\n> ⚠️  Esta tarea tiene {len(task_subs)} subtareas (no esperado en el modelo).\n")
                        for st in task_subs:
                            lines.extend(render_issue_header(st, level="####"))
                            lines.append("")
                    lines.append("")

            # ── Historias con sus subtareas ───────────────────────────────────
            if stories_only:
                header = f"\n## Historias de la épica ({len(stories_only)}"
                if total_subtasks:
                    header += f" — {total_subtasks} subtareas en total"
                header += ")\n"
                lines.append(header)
                lines.append("> Hijos directos de la épica de tipo **Story**. Cada historia puede tener subtareas.\n")
                for story in stories_only:
                    lines.extend(render_issue_header(story, level="###"))
                    story_subtasks = subtasks_by_parent.get(story['key'], [])
                    if story_subtasks:
                        lines.append(f"\n#### Subtareas de {story['key']} ({len(story_subtasks)})\n")
                        for subtask in story_subtasks:
                            lines.extend(render_issue_header(subtask, level="#####"))
                            lines.append("")
                    else:
                        lines.append(f"\n*(Esta historia no tiene subtareas)*\n")
                    lines.append("")

            # ── Otros tipos (Bug, Improvement, etc.) ──────────────────────────
            if others:
                lines.append(f"\n## Otros issues vinculados a la épica ({len(others)})\n")
                for issue in others:
                    lines.extend(render_issue_header(issue, level="###"))
                    issue_subs = subtasks_by_parent.get(issue['key'], [])
                    if issue_subs:
                        lines.append(f"\n#### Subtareas de {issue['key']} ({len(issue_subs)})\n")
                        for st in issue_subs:
                            lines.extend(render_issue_header(st, level="#####"))
                            lines.append("")
                    lines.append("")

        lines.append("---\n")

    # ── Sección Confluence ────────────────────────────────────────────────────
    if confluence_pages:
        lines.append(f"## Documentación de Confluence ({len(confluence_pages)} páginas)\n")
        for page in confluence_pages:
            lines.append(f"### {page.get('title', 'Sin título')}\n")
            page_url = page.get('_links', {}).get('webui', '')
            if page_url and config.effective_confluence_base_url:
                lines.append(f"**URL:** {config.effective_confluence_base_url}{page_url}  \n")
            content = page.get('markdown_content', '').strip()
            if content:
                lines.append(content)
            lines.append("\n---\n")

    lines.append("\n## Instrucciones para el agente\n")
    lines.append("Este archivo contiene los datos descargados desde Jira y/o Confluence.")
    lines.append("Úsalo como contexto base para ejecutar `/spec-kitti.specify` y generar el `spec.md`.")
    lines.append("El spec debe seguir el template en `.spec-kitti/templates/spec-template.md`.")

    return '\n'.join(lines)


def generate_import_report(
    config: AtlassianConfig,
    epic: dict | None,
    stories: list,
    subtasks_by_parent: dict,
    confluence_pages: list,
) -> str:
    """
    Genera el reporte de importación.

    Refleja el modelo de jerarquía:
      Épica
        ├── Tarea       (Task — hijo directo, sin subtareas)
        └── Historia    (Story — hijo directo, con subtareas)
    """

    from ..utils.helpers import get_story_points, group_issues_by_component, split_issues_by_type

    total_subtasks = sum(len(v) for v in subtasks_by_parent.values())
    split = split_issues_by_type(stories) if stories else {'stories': [], 'tasks': [], 'other': []}
    n_stories = len(split['stories'])
    n_tasks = len(split['tasks'])
    n_other = len(split['other'])

    report = f"""# Jira/Confluence Import Report

**Import Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Sync Mode:** {config.sync_mode}  
**Duration:** N/A

## Summary

"""

    if epic:
        total_points = sum(get_story_points(s) for s in stories)
        story_keys = {s['key'] for s in split['stories']}
        task_keys = {t['key'] for t in split['tasks']}
        stories_with_subs = sum(1 for k in subtasks_by_parent if k in story_keys)
        tasks_with_subs = sum(1 for k in subtasks_by_parent if k in task_keys)

        report += f"""✅ **Successfully imported from Jira:**
- Epic: {epic['key']} "{epic['fields']['summary']}"
- Direct children of the epic: {len(stories)} ({total_points} total story points)
  - Stories (Historias): {n_stories} — {stories_with_subs}/{n_stories} have sub-tasks
  - Tasks (Tareas): {n_tasks}{f' — ⚠️ {tasks_with_subs} unexpectedly have sub-tasks' if tasks_with_subs else ' (no sub-tasks expected)'}"""
        if n_other:
            report += f"\n  - Other types: {n_other}"
        report += f"\n- Sub-tasks: {total_subtasks} (across {len(subtasks_by_parent)} parent issues)\n\n"

    if confluence_pages:
        report += f"""✅ **Successfully imported from Confluence:**
- Pages: {len(confluence_pages)}

"""

    if epic:
        report += """## Hierarchy Model

```
Epic
  ├── Task       (direct child, no sub-tasks)
  └── Story      (direct child, may have sub-tasks)
        └── Sub-task
```

"""

        grouped = group_issues_by_component(stories)
        report += """## Breakdown by Component

| Component | Issues | Story Points |
|-----------|--------|--------------|
"""
        for component, comp_stories in grouped.items():
            comp_points = sum(get_story_points(s) for s in comp_stories)
            report += f"| {component} | {len(comp_stories)} | {comp_points} |\n"

        if subtasks_by_parent:
            report += "\n## Sub-tasks by Parent (Story)\n\n"
            report += "| Parent | Type | Title | Sub-tasks |\n"
            report += "|--------|------|-------|-----------|\n"
            stories_by_key = {s['key']: s for s in stories}
            from ..utils.helpers import get_issue_type
            for parent_key, sts in subtasks_by_parent.items():
                parent = stories_by_key.get(parent_key)
                title = parent['fields'].get('summary', '') if parent else ''
                ptype = get_issue_type(parent) if parent else 'Unknown'
                report += f"| {parent_key} | {ptype} | {title} | {len(sts)} |\n"

        report += f"""
## Validation Results

✅ Epic metadata captured  
✅ {len(stories)} direct children imported ({n_stories} stories + {n_tasks} tasks{f' + {n_other} other' if n_other else ''})  
"""

        if total_subtasks:
            report += f"✅ {total_subtasks} sub-tasks downloaded from {stories_with_subs} stories  \n"
        else:
            report += "ℹ️  No sub-tasks found in the epic's children  \n"

    if confluence_pages:
        report += f"✅ {len(confluence_pages)} Confluence pages downloaded  \n"

    report += "\n## Generated Files\n\n"

    report += "- `sync_context.md` (consolidated context for `/spec-kitti.specify`)\n"
    if epic:
        report += "- `jira_raw/` (raw Jira data in JSON)\n"
        report += f"  - `{config.epic_key}_epic.json`\n"
        report += f"  - `{config.epic_key}_stories.json` — direct children (stories + tasks)\n"
        if subtasks_by_parent:
            report += f"  - `{config.epic_key}_subtasks.json` — sub-tasks grouped by parent story\n"

    if confluence_pages:
        report += "- `confluence_raw/` (raw Confluence data in JSON + Markdown)\n"

    epic_ref = f"Epic {config.epic_key}" if config.epic_key else "N/A"
    confluence_url_info = (
        f", Confluence URL: {config.effective_confluence_base_url}"
        if config.confluence_base_url and config.confluence_base_url != config.jira_base_url
        else ""
    )
    report += f"""
## Next Steps

1. Review `sync_context.md` for completeness
2. Run `/spec-kitti.specify` to generate `spec.md`
3. Run `/spec-kitti.clarify` to resolve ambiguities
4. Run `/spec-kitti.plan` to create implementation plan

---

*Config used: {epic_ref}, Jira URL: {config.jira_base_url}{confluence_url_info}*
"""

    return report


if __name__ == '__main__':
    sys.exit(main())

