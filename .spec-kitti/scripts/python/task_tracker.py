#!/usr/bin/env python3
"""
Task Tracker Helper for Spec-Kitti
Automatically updates task-status.json during implementation
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class TaskTracker:
    def __init__(self, feature_dir: str):
        self.feature_dir = Path(feature_dir)
        self.status_file = self.feature_dir / "task-status.json"
        self.dashboard_file = self.feature_dir / "PROGRESS.md"
        
        if not self.status_file.exists():
            raise FileNotFoundError(f"task-status.json not found in {feature_dir}")
    
    def load_status(self) -> Dict:
        """Load task status from JSON"""
        with open(self.status_file, 'r') as f:
            return json.load(f)
    
    def save_status(self, status: Dict):
        """Save task status to JSON"""
        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=2)
    
    def mark_in_progress(self, task_id: str):
        """Mark task as in progress"""
        status = self.load_status()
        
        # Find task
        task = next((t for t in status['tasks'] if t['id'] == task_id), None)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Update task
        task['status'] = 'in_progress'
        task['started_at'] = datetime.now().isoformat()
        
        # Update counters
        status['in_progress'] = status.get('in_progress', 0) + 1
        status['pending'] = status.get('pending', 0) - 1
        status['updated_at'] = datetime.now().isoformat()
        
        self.save_status(status)
        
        # Log
        timestamp = datetime.now().strftime('%H:%M')
        print(f"[{timestamp}] ⏳ Task {task_id} marcada como 'in_progress'")
    
    def mark_completed(self, task_id: str, files_changed: List[str], 
                       tests_passed: bool, iterations: int = 1):
        """Mark task as completed"""
        status = self.load_status()
        
        # Find task
        task = next((t for t in status['tasks'] if t['id'] == task_id), None)
        if not task or task['status'] != 'in_progress':
            raise ValueError(f"Task {task_id} is not in progress")
        
        # Calculate duration
        start_time = datetime.fromisoformat(task['started_at'])
        end_time = datetime.now()
        duration_minutes = round((end_time - start_time).total_seconds() / 60)
        
        # Update task
        task['status'] = 'completed'
        task['completed_at'] = end_time.isoformat()
        task['duration_minutes'] = duration_minutes
        task['files_changed'] = files_changed
        task['tests_passed'] = tests_passed
        task['iterations'] = iterations
        task['implemented_by'] = 'executor-agent'
        
        # Update counters
        status['completed'] = status.get('completed', 0) + 1
        status['in_progress'] = status.get('in_progress', 0) - 1
        status['progress_percentage'] = (status['completed'] / status['total_tasks']) * 100
        status['updated_at'] = end_time.isoformat()
        
        # Find next task
        next_task = self._find_next_task(status)
        if next_task:
            status['next_recommended_tasks'] = [{
                'id': next_task['id'],
                'title': next_task['title'],
                'reason': 'All dependencies met, next in priority'
            }]
        
        self.save_status(status)
        self.generate_dashboard(status)
        
        # Log
        timestamp = datetime.now().strftime('%H:%M')
        print(f"[{timestamp}] ✅ Task {task_id} completada ({duration_minutes} min)")
        print(f"📊 Progreso: {status['completed']}/{status['total_tasks']} ({status['progress_percentage']:.2f}%)")
        
        if next_task:
            print(f"💡 Siguiente: {next_task['id']} - {next_task['title']}")
    
    def mark_failed(self, task_id: str, error: str, error_details: str, next_action: str):
        """Mark task as failed"""
        status = self.load_status()
        
        # Find task
        task = next((t for t in status['tasks'] if t['id'] == task_id), None)
        if not task or task['status'] != 'in_progress':
            raise ValueError(f"Task {task_id} is not in progress")
        
        # Update task
        task['status'] = 'failed'
        task['failed_at'] = datetime.now().isoformat()
        task['error'] = error
        task['error_details'] = error_details
        task['retry_count'] = task.get('retry_count', 0) + 1
        task['next_action'] = next_action
        
        # Update counters
        status['failed'] = status.get('failed', 0) + 1
        status['in_progress'] = status.get('in_progress', 0) - 1
        status['updated_at'] = datetime.now().isoformat()
        
        self.save_status(status)
        self.generate_dashboard(status)
        
        # Log
        timestamp = datetime.now().strftime('%H:%M')
        print(f"[{timestamp}] ❌ Task {task_id} falló")
        print(f"Error: {error}")
        print(f"Detalles: {error_details}")
        print(f"Acción: {next_action}")
    
    def generate_dashboard(self, status: Dict):
        """Generate PROGRESS.md dashboard"""
        completed = status.get('completed', 0)
        in_progress = status.get('in_progress', 0)
        pending = status.get('pending', 0)
        failed = status.get('failed', 0)
        total = status.get('total_tasks', 0)
        progress = status.get('progress_percentage', 0)
        
        # Progress bar
        bar_length = 30
        filled = int(bar_length * progress / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        markdown = f"""# Progreso: {status.get('feature', 'Feature')}

**Última actualización:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 📊 Resumen General

- **Total de tareas:** {total}
- **Completadas:** {completed} ✅
- **En progreso:** {in_progress} 🔄
- **Pendientes:** {pending} ⏳
- **Fallidas:** {failed} ❌
- **Progreso:** {bar} {progress:.2f}%

## 📋 Tareas por Estado

### ✅ Completadas ({completed})

"""
        
        # List completed tasks
        for task in status.get('tasks', []):
            if task.get('status') == 'completed':
                duration = task.get('duration_minutes', 0)
                markdown += f"- ✅ {task.get('id')}: {task.get('title')} ({duration} min)\n"
        
        markdown += f"\n### 🔄 En Progreso ({in_progress})\n\n"
        
        # List in progress
        for task in status.get('tasks', []):
            if task.get('status') == 'in_progress':
                markdown += f"- 🔄 {task.get('id')}: {task.get('title')}\n"
        
        markdown += f"\n### ⏳ Pendientes ({pending})\n\n"
        
        # List first 10 pending
        pending_tasks = [t for t in status.get('tasks', []) if t.get('status') == 'pending']
        for task in pending_tasks[:10]:
            markdown += f"- ⏳ {task.get('id')}: {task.get('title')}\n"
        
        if len(pending_tasks) > 10:
            markdown += f"\n... y {len(pending_tasks) - 10} más\n"
        
        # Failed tasks
        if failed > 0:
            markdown += f"\n### ❌ Fallidas ({failed})\n\n"
            for task in status.get('tasks', []):
                if task.get('status') == 'failed':
                    markdown += f"- ❌ {task.get('id')}: {task.get('title')}\n"
                    markdown += f"  - Error: {task.get('error', 'Unknown')}\n"
                    markdown += f"  - Acción: {task.get('next_action', 'Revisar manualmente')}\n\n"
        
        # Next recommended task
        next_tasks = status.get('next_recommended_tasks', [])
        if next_tasks:
            next_task = next_tasks[0]
            markdown += f"""
## 🎯 Siguiente Paso Recomendado

**{next_task.get('id')}: {next_task.get('title')}**

Razón: {next_task.get('reason', 'Next in priority')}

```bash
/spec-kitti.implement --task "{next_task.get('id')}"
```
"""
        
        # Write dashboard
        with open(self.dashboard_file, 'w') as f:
            f.write(markdown)
        
        print(f"📊 Dashboard actualizado: {self.dashboard_file}")
    
    def _find_next_task(self, status: Dict) -> Optional[Dict]:
        """Find next recommended task"""
        # Find first pending task with all dependencies met
        for task in status.get('tasks', []):
            if task.get('status') == 'pending':
                deps = task.get('dependencies', [])
                if self._dependencies_met(deps, status):
                    return task
        return None
    
    def _dependencies_met(self, dependencies: List[str], status: Dict) -> bool:
        """Check if all dependencies are completed"""
        if not dependencies:
            return True
        
        for dep_id in dependencies:
            dep_task = next((t for t in status['tasks'] if t['id'] == dep_id), None)
            if not dep_task or dep_task.get('status') != 'completed':
                return False
        
        return True


def main():
    """CLI interface for task tracker"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: task_tracker.py <feature_dir> <command> [args]")
        print("Commands:")
        print("  start <task_id>")
        print("  complete <task_id> <files_changed_json> <tests_passed> [iterations]")
        print("  fail <task_id> <error> <error_details> <next_action>")
        sys.exit(1)
    
    feature_dir = sys.argv[1]
    command = sys.argv[2]
    
    tracker = TaskTracker(feature_dir)
    
    if command == 'start':
        task_id = sys.argv[3]
        tracker.mark_in_progress(task_id)
    
    elif command == 'complete':
        task_id = sys.argv[3]
        files_changed = json.loads(sys.argv[4])
        tests_passed = sys.argv[5].lower() == 'true'
        iterations = int(sys.argv[6]) if len(sys.argv) > 6 else 1
        tracker.mark_completed(task_id, files_changed, tests_passed, iterations)
    
    elif command == 'fail':
        task_id = sys.argv[3]
        error = sys.argv[4]
        error_details = sys.argv[5]
        next_action = sys.argv[6]
        tracker.mark_failed(task_id, error, error_details, next_action)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()

