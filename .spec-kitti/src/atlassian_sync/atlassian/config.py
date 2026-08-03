"""
Configuración unificada para Jira y Confluence
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class AtlassianConfig:
    """
    Configuración para Jira y Confluence.

    Jira y Confluence pueden vivir en dominios distintos:
      JIRA_BASE_URL       = https://ueno-bank.atlassian.net
      CONFLUENCE_BASE_URL = https://itti-digital.atlassian.net  (opcional — usa JIRA_BASE_URL si no se define)

    Las credenciales (email + api_token) son compartidas entre ambos servicios.
    """

    # Credenciales (compartidas entre Jira y Confluence)
    email: str
    api_token: str

    # URL base de Jira
    jira_base_url: str  # https://ueno-bank.atlassian.net

    # URL base de Confluence — puede ser diferente al de Jira
    # Si no se especifica, hereda jira_base_url (comportamiento anterior)
    confluence_base_url: Optional[str] = None

    # Jira específico
    epic_key: Optional[str] = None  # Épica a importar (ej: PROJ-123) — requerida en modo jira/both

    # Confluence específico (opcional)
    confluence_space_key: Optional[str] = None
    confluence_parent_page: Optional[str] = None  # Título de página padre

    # Salida
    output_dir: str = ".spec-kitti"

    # Modo de sincronización
    sync_mode: str = "both"  # "jira" | "confluence" | "both"

    @property
    def effective_confluence_base_url(self) -> str:
        """URL efectiva de Confluence — usa confluence_base_url si está definida, si no jira_base_url."""
        return (self.confluence_base_url or self.jira_base_url).rstrip('/')

    def validate(self):
        """Valida la configuración"""
        if not self.email:
            raise ValueError("Email es requerido (JIRA_EMAIL)")
        if not self.api_token:
            raise ValueError("API token es requerido (JIRA_API_TOKEN)")

        valid_modes = ("jira", "confluence", "both")
        if self.sync_mode not in valid_modes:
            raise ValueError(f"sync_mode debe ser uno de: {', '.join(valid_modes)}")

        if self.sync_mode in ("jira", "both"):
            if not self.jira_base_url:
                raise ValueError("JIRA_BASE_URL es requerida para el modo jira/both")
            if not self.jira_base_url.startswith('http'):
                raise ValueError("JIRA_BASE_URL debe comenzar con http:// o https://")
            if not self.epic_key:
                raise ValueError("epic_key es requerido para el modo jira/both")

        if self.sync_mode in ("confluence", "both"):
            effective = self.effective_confluence_base_url
            if not effective:
                raise ValueError("JIRA_BASE_URL o CONFLUENCE_BASE_URL es requerida para el modo confluence/both")
            if not effective.startswith('http'):
                raise ValueError("La URL de Confluence debe comenzar con http:// o https://")
            if not self.confluence_space_key:
                raise ValueError("CONFLUENCE_SPACE_KEY es requerido para el modo confluence/both")

        if self.confluence_base_url and not self.confluence_base_url.startswith('http'):
            raise ValueError("CONFLUENCE_BASE_URL debe comenzar con http:// o https://")

        logger.debug("Configuración validada correctamente")

    @classmethod
    def from_env(
        cls,
        epic_key: Optional[str] = None,
        confluence_parent: Optional[str] = None,
        sync_mode: str = "both",
    ) -> 'AtlassianConfig':
        """
        Crea configuración desde variables de entorno.

        Variables soportadas:
          JIRA_EMAIL, JIRA_API_TOKEN, JIRA_BASE_URL  — siempre requeridas
          CONFLUENCE_BASE_URL                         — opcional; si no se define, usa JIRA_BASE_URL
          CONFLUENCE_SPACE_KEY                        — requerida en modo confluence/both
          SPEC_KITTI_OUTPUT_DIR                       — directorio de salida (default: .spec-kitti)
        """
        config = cls(
            email=os.getenv('JIRA_EMAIL', ''),
            api_token=os.getenv('JIRA_API_TOKEN', ''),
            jira_base_url=os.getenv('JIRA_BASE_URL', ''),
            confluence_base_url=os.getenv('CONFLUENCE_BASE_URL') or None,
            epic_key=epic_key,
            confluence_space_key=os.getenv('CONFLUENCE_SPACE_KEY'),
            confluence_parent_page=confluence_parent,
            output_dir=os.getenv('SPEC_KITTI_OUTPUT_DIR', '.spec-kitti'),
            sync_mode=sync_mode,
        )

        config.validate()
        logger.info(
            f"Configuración cargada desde ENV — Jira: {config.jira_base_url} | "
            f"Confluence: {config.effective_confluence_base_url} | modo: {config.sync_mode}"
        )
        return config

    @classmethod
    def from_dotenv(
        cls,
        env_file: Path,
        epic_key: Optional[str] = None,
        confluence_parent: Optional[str] = None,
        sync_mode: str = "both",
    ) -> 'AtlassianConfig':
        """
        Carga configuración desde archivo .env.

        Variables soportadas (ver from_env para la lista completa).
        """
        if not env_file.exists():
            raise FileNotFoundError(f"Archivo .env no encontrado: {env_file}")

        env_vars = {}
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip().strip('"').strip("'")
                    env_vars[key.strip()] = value

        config = cls(
            email=env_vars.get('JIRA_EMAIL', ''),
            api_token=env_vars.get('JIRA_API_TOKEN', ''),
            jira_base_url=env_vars.get('JIRA_BASE_URL', ''),
            confluence_base_url=env_vars.get('CONFLUENCE_BASE_URL') or None,
            epic_key=epic_key,
            confluence_space_key=env_vars.get('CONFLUENCE_SPACE_KEY'),
            confluence_parent_page=confluence_parent,
            output_dir=env_vars.get('SPEC_KITTI_OUTPUT_DIR', '.spec-kitti'),
            sync_mode=sync_mode,
        )

        config.validate()
        logger.info(
            f"Configuración cargada desde {env_file} — Jira: {config.jira_base_url} | "
            f"Confluence: {config.effective_confluence_base_url} | modo: {config.sync_mode}"
        )
        return config

    @property
    def jira_api_base(self) -> str:
        """URL base de la API de Jira"""
        return f"{self.jira_base_url.rstrip('/')}/rest/api/2"

    @property
    def confluence_api_base(self) -> str:
        """URL base de la API de Confluence"""
        return f"{self.effective_confluence_base_url}/wiki/rest/api"

    @property
    def auth(self) -> tuple:
        """Tupla de autenticación para requests"""
        return (self.email, self.api_token)
