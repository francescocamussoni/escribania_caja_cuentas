"""
Generador de spec.md desde datos de Jira y Confluence
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging

from ..utils.helpers import (
    extract_text_from_adf,
    extract_acceptance_criteria,
    get_issue_priority,
    get_issue_status,
    get_story_points,
    group_issues_by_component,
    sort_issues_by_priority
)

logger = logging.getLogger(__name__)


class SpecGenerator:
    """Genera spec.md siguiendo el template de Spec-Kitti"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def generate_spec(
        self,
        epic: Optional[Dict],
        stories: List[Dict],
        confluence_pages: Optional[List[Dict]] = None,
        output_file: Path = None,
        constitution_md: Optional[str] = None
    ) -> str:
        """
        Genera el contenido de spec.md

        Args:
            epic: Épica de Jira (None en modo confluence-only)
            stories: Lista de historias (vacía en modo confluence-only)
            confluence_pages: Páginas de Confluence (opcional)
            output_file: Archivo donde guardar (opcional)
            constitution_md: Contenido del constitution.md del proyecto (opcional)

        Returns:
            Contenido del spec en Markdown
        """
        if epic:
            logger.info(f"Generando spec para épica {epic['key']}")
        else:
            logger.info("Generando spec solo desde Confluence (sin épica de Jira)")

        spec_content = []

        # Header
        spec_content.append(self._generate_header(epic))

        # Context
        spec_content.append(self._generate_context(epic, stories, confluence_pages))

        # Constitution & Principles (if provided)
        if constitution_md:
            spec_content.append(self._generate_constitution_section(constitution_md))

        # User Stories (solo si hay historias)
        if stories:
            spec_content.append(self._generate_user_stories(stories))

        # Technical Context (from Confluence)
        if confluence_pages:
            spec_content.append(self._generate_technical_context(confluence_pages))

        # Functional Requirements (solo si hay historias)
        if stories:
            spec_content.append(self._generate_functional_requirements(stories))
            spec_content.append(self._generate_nfr(stories))
            spec_content.append(self._generate_dependencies(stories))

        # Appendix
        spec_content.append(self._generate_appendix(epic, stories, confluence_pages))

        full_spec = '\n\n'.join(spec_content)

        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(full_spec)
            logger.info(f"Spec guardado en {output_file}")

        return full_spec
    
    def _generate_header(self, epic: Optional[Dict]) -> str:
        """Genera el header del spec"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if epic:
            fields = epic['fields']
            epic_key = epic['key']
            epic_url = f"{self.base_url}/browse/{epic_key}"
            return f"""# Feature Specification: {fields['summary']}

**Jira Epic:** [{epic_key}]({epic_url})  
**Status:** {get_issue_status(epic)}  
**Priority:** {get_issue_priority(epic)}  
**Last Updated:** {now}

---"""
        else:
            return f"""# Confluence Documentation Spec

**Source:** Confluence  
**Last Updated:** {now}

---"""
    
    def _generate_context(self, epic: Optional[Dict], stories: List[Dict], confluence_pages: Optional[List[Dict]]) -> str:
        """Genera la sección de contexto"""
        total_points = sum(get_story_points(s) for s in stories)

        content = "## Context\n"

        if epic:
            fields = epic['fields']
            description = extract_text_from_adf(fields.get('description'))
            content += f"\n{description if description else '*No description provided*'}\n"
            content += "\n### Source Documentation\n"
            content += f"\n- **Jira Epic:** [{epic['key']}]({self.base_url}/browse/{epic['key']})"
        else:
            content += "\n*Specification generated from Confluence documentation only.*\n"
            content += "\n### Source Documentation\n"

        if confluence_pages:
            content += "\n- **Confluence Pages:**"
            for page in confluence_pages[:5]:
                content += f"\n  - {page['title']}"

        if stories:
            content += f"\n- **Total Stories:** {len(stories)} stories"
            if total_points > 0:
                content += f" ({total_points} story points)"

        content += "\n\n---"

        return content
    
    def _generate_constitution_section(self, constitution_md: str) -> str:
        """Genera la sección de Constitution & Principles del proyecto"""
        content = f"""## Constitution & Principles

**Note:** This feature must comply with the project's constitution and guiding principles.

{constitution_md}

---"""
        
        return content
    
    def _generate_user_stories(self, stories: List[Dict]) -> str:
        """Genera la sección de user stories"""
        content = ["## User Stories"]
        
        # Agrupar por componente
        grouped = group_issues_by_component(stories)
        
        story_num = 1
        for component, component_stories in grouped.items():
            if len(grouped) > 1:
                content.append(f"\n### Component: {component}\n")
            
            # Ordenar por prioridad
            sorted_stories = sort_issues_by_priority(component_stories)
            
            for story in sorted_stories:
                content.append(self._format_story(story, story_num))
                story_num += 1
        
        return '\n'.join(content)
    
    def _format_story(self, story: Dict, number: int) -> str:
        """Formatea una user story"""
        fields = story['fields']
        story_key = story['key']
        story_url = f"{self.base_url}/browse/{story_key}"
        
        points = get_story_points(story)
        priority = get_issue_priority(story)
        status = get_issue_status(story)
        
        # Componentes
        components = fields.get('components', [])
        component_names = [c['name'] for c in components] if components else ['N/A']
        
        content = f"""
### Story {number}: [{story_key}] {fields['summary']}

**Priority:** {priority}  
**Story Points:** {points if points > 0 else 'TBD'}  
**Component:** {', '.join(component_names)}  
**Status:** {status}  
**Jira Link:** [{story_key}]({story_url})

**Description:**
{extract_text_from_adf(fields.get('description')) or '*No description provided*'}

**Acceptance Criteria:**"""
        
        criteria = extract_acceptance_criteria(story)
        if criteria:
            for criterion in criteria:
                content += f"\n- [ ] {criterion}"
        else:
            content += "\n- [ ] *Acceptance criteria to be defined*"
        
        # Dependencias
        issue_links = fields.get('issuelinks', [])
        if issue_links:
            content += "\n\n**Dependencies:**"
            for link in issue_links:
                if 'outwardIssue' in link:
                    linked = link['outwardIssue']
                    content += f"\n- {linked['key']}: {linked['fields']['summary']}"
        
        content += "\n\n---"
        
        return content
    
    def _generate_technical_context(self, pages: List[Dict]) -> str:
        """Genera la sección de contexto técnico desde Confluence"""
        content = ["## Technical Context\n"]
        
        for page in pages:
            content.append(f"### {page['title']}\n")
            
            # El contenido ya viene en Markdown desde el downloader
            body = page.get('markdown_content', '')
            if body:
                content.append(body[:2000])  # Limitar para no hacer el spec muy largo
                if len(body) > 2000:
                    content.append("\n\n*[Content truncated - see full page in Confluence]*")
            
            content.append("\n---\n")
        
        return '\n'.join(content)
    
    def _generate_functional_requirements(self, stories: List[Dict]) -> str:
        """Genera requisitos funcionales extraídos de las historias"""
        content = ["## Functional Requirements\n"]
        content.append("Based on the user stories above, the following functional requirements are identified:\n")
        
        fr_num = 1
        for story in stories:
            fields = story['fields']
            summary = fields['summary']
            
            # Extraer requisito funcional del summary
            content.append(f"{fr_num}. **FR-{fr_num:03d}: {summary}**")
            
            # Agregar descripción breve
            description = extract_text_from_adf(fields.get('description'))
            if description:
                first_line = description.split('\n')[0][:150]
                content.append(f"   - {first_line}\n")
            
            fr_num += 1
        
        return '\n'.join(content)
    
    def _generate_nfr(self, stories: List[Dict]) -> str:
        """Genera requisitos no funcionales extraídos"""
        content = ["## Non-Functional Requirements\n"]
        
        # Buscar NFRs implícitos en descripciones
        nfrs = {
            'Performance': [],
            'Security': [],
            'Scalability': [],
            'Usability': []
        }
        
        for story in stories:
            description = extract_text_from_adf(story.get('fields', {}).get('description', ''))
            if not description:
                continue
            
            desc_lower = description.lower()
            
            if any(word in desc_lower for word in ['performance', 'fast', 'speed', 'latency', 'response time']):
                nfrs['Performance'].append(f"- Story {story['key']} implies performance requirements")
            
            if any(word in desc_lower for word in ['security', 'authentication', 'authorization', 'encrypt']):
                nfrs['Security'].append(f"- Story {story['key']} implies security requirements")
            
            if any(word in desc_lower for word in ['scale', 'concurrent', 'load', 'capacity']):
                nfrs['Scalability'].append(f"- Story {story['key']} implies scalability requirements")
        
        # Agregar solo categorías con contenido
        has_nfrs = False
        for category, items in nfrs.items():
            if items:
                has_nfrs = True
                content.append(f"### {category}\n")
                content.extend(items)
                content.append("")
        
        if not has_nfrs:
            content.append("*Non-functional requirements to be defined during planning phase.*\n")
        
        return '\n'.join(content)
    
    def _generate_dependencies(self, stories: List[Dict]) -> str:
        """Genera sección de dependencias"""
        content = ["## Dependencies\n"]
        
        # Detectar dependencias entre historias
        dependencies = []
        for story in stories:
            issue_links = story.get('fields', {}).get('issuelinks', [])
            for link in issue_links:
                if 'outwardIssue' in link:
                    linked = link['outwardIssue']
                    dependencies.append({
                        'from': story['key'],
                        'to': linked['key'],
                        'type': link.get('type', {}).get('name', 'relates to')
                    })
        
        if dependencies:
            # Generar diagrama Mermaid
            content.append("```mermaid")
            content.append("graph TD")
            for dep in dependencies:
                content.append(f"    {dep['from']}[{dep['from']}] --> {dep['to']}[{dep['to']}]")
            content.append("```\n")
            
            content.append("**Dependency List:**")
            for dep in dependencies:
                content.append(f"- {dep['from']} → {dep['to']} ({dep['type']})")
        else:
            content.append("*No explicit dependencies detected between stories.*\n")
        
        return '\n'.join(content)
    
    def _generate_appendix(self, epic: Optional[Dict], stories: List[Dict], confluence_pages: Optional[List[Dict]]) -> str:
        """Genera el apéndice con metadata"""
        total_points = sum(get_story_points(s) for s in stories)

        content = f"""## Appendix

### Import Metadata

- **Import Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        if epic:
            content += f"\n- **Jira Epic:** {epic['key']}"
            content += f"\n- **Stories Imported:** {len(stories)}"
            content += f"\n- **Total Story Points:** {total_points}"

        if confluence_pages:
            content += f"\n- **Confluence Pages:** {len(confluence_pages)}"

        content += "\n\n### Raw Links\n"

        if epic:
            content += f"\n- **Jira Epic URL:** {self.base_url}/browse/{epic['key']}"
            content += f"\n- **JQL Query:** `\"Epic Link\" = {epic['key']} AND type = Story`"

        if confluence_pages:
            content += "\n- **Confluence Pages:**"
            for page in confluence_pages[:10]:
                page_url = page.get('_links', {}).get('webui', page.get('url', ''))
                content += f"\n  - [{page['title']}]({page_url})"

        content += "\n\n---\n\n*This specification was auto-generated by Spec-Kitti. Manual edits will be preserved.*"

        return content

