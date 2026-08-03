"""
Configuración del sistema de logging
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(log_level: str = "INFO", log_file: Path = None):
    """
    Configura el sistema de logging
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Ruta al archivo de log (opcional)
    """
    # Formato de los mensajes
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configurar el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Limpiar handlers existentes
    root_logger.handlers.clear()
    
    # Handler para consola (solo WARNING y superior)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter(log_format, date_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Handler para archivo (si se especifica)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_formatter = logging.Formatter(log_format, date_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Silenciar logs de librerías externas
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def get_log_file_path(output_dir: Path) -> Path:
    """
    Genera una ruta para el archivo de log
    
    Args:
        output_dir: Directorio base de salida
        
    Returns:
        Ruta al archivo de log
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dir = output_dir / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f'confluence_downloader_{timestamp}.log'


