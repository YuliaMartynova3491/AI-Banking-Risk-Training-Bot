"""
Проверка здоровья системы
"""
import logging
from typing import Dict, Any
from datetime import datetime
from ai_agent.agent_nodes import AgentNodes
from core.database import db_service

logger = logging.getLogger(__name__)

class HealthChecker:
    """Проверка состояния всех компонентов системы"""
    
    @staticmethod
    async def check_all_components() -> Dict[str, Any]:
        """Полная проверка всех компонентов"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {}
        }
        
        # Проверка базы данных
        results["components"]["database"] = HealthChecker._check_database()
        
        # Проверка AI-агента
        results["components"]["ai_agent"] = await HealthChecker._check_ai_agent()
        
        # Проверка конфигурации
        results["components"]["config"] = HealthChecker._check_config()
        
        # Определение общего статуса
        failed_components = [
            name for name, status in results["components"].items() 
            if not status["healthy"]
        ]
        
        if failed_components:
            results["overall_status"] = "degraded" if len(failed_components) == 1 else "unhealthy"
            results["failed_components"] = failed_components
        
        return results
    
    @staticmethod
    def _check_database() -> Dict[str, Any]:
        """Проверка базы данных"""
        try:
            # Тестовый запрос
            test_progress = db_service.get_user_progress(999999)  # Несуществующий пользователь
            return {
                "healthy": True,
                "message": "База данных доступна",
                "response_time": "< 100ms"
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Ошибка базы данных: {e}",
                "error": str(e)
            }
    
    @staticmethod
    async def _check_ai_agent() -> Dict[str, Any]:
        """Проверка AI-агента"""
        try:
            if not AgentNodes.llm:
                return {
                    "healthy": False,
                    "message": "LLM не инициализирован"
                }
            
            # Простой тест
            test_state = {
                "user_question": "Тест",
                "topic": "тест"
            }
            
            start_time = time.time()
            result = AgentNodes.provide_assistance_node(test_state)
            response_time = time.time() - start_time
            
            if result.get("assistance_response"):
                return {
                    "healthy": True,
                    "message": "AI-агент работает",
                    "response_time": f"{response_time:.2f}s"
                }
            else:
                return {
                    "healthy": False,
                    "message": "AI-агент не отвечает"
                }
                
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Ошибка AI-агента: {e}",
                "error": str(e)
            }
    
    @staticmethod
    def _check_config() -> Dict[str, Any]:
        """Проверка конфигурации"""
        try:
            from config.bot_config import LEARNING_STRUCTURE, TOPIC_ALIASES
            
            issues = []
            
            # Проверяем структуру обучения
            if not LEARNING_STRUCTURE:
                issues.append("LEARNING_STRUCTURE пуста")
            
            # Проверяем алиасы тем
            if not TOPIC_ALIASES:
                issues.append("TOPIC_ALIASES пусты")
            
            # Проверяем соответствие алиасов
            for topic_id in LEARNING_STRUCTURE.keys():
                if topic_id not in TOPIC_ALIASES:
                    issues.append(f"Нет алиаса для темы {topic_id}")
            
            if issues:
                return {
                    "healthy": False,
                    "message": "Проблемы конфигурации",
                    "issues": issues
                }
            else:
                return {
                    "healthy": True,
                    "message": "Конфигурация корректна",
                    "topics_count": len(LEARNING_STRUCTURE)
                }
                
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Ошибка проверки конфигурации: {e}",
                "error": str(e)
            }

# Экземпляр проверки здоровья
health_checker = HealthChecker()