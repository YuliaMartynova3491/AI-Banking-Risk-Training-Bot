"""
Узлы (nodes) для AI-агента на LangGraph - ВЕРСИЯ ДЛЯ РУССКОГО ЯЗЫКА
"""
import logging
from typing import Dict, Any
from langchain_core.messages import AIMessage, SystemMessage

from services.user_analysis_service import user_analysis_service
from services.adaptive_content_service import adaptive_content_service

logger = logging.getLogger(__name__)

# Системный промпт для принуждения к русскому языку
RUSSIAN_SYSTEM_PROMPT = """
Ты - эксперт по банковским рискам в России. 

КРИТИЧЕСКИ ВАЖНО:
- Отвечай ТОЛЬКО на русском языке
- НЕ показывай процесс размышления
- НЕ используй китайские иероглифы или другие языки
- Давай прямые, понятные ответы
- Используй примеры только из российских банков: Сбербанк, ВТБ, Альфа-Банк
- Объясняй сложные термины простыми словами

Стиль: краткий, профессиональный, мотивирующий.
"""

class AgentNodes:
    """Класс, содержащий все узлы AI-агента."""
    llm = None

    @staticmethod
    def analyze_user_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел анализа пользователя."""
        user_id = state.get("user_id")
        if not user_id:
            return {**state, "error": "User ID not provided"}
        
        try:
            logger.info(f"Анализирую пользователя {user_id}...")
            user_analysis = user_analysis_service.get_full_user_analysis(user_id)

            return {
                **state,
                "user_analysis": user_analysis,
                "messages": state.get("messages", []) + [AIMessage(content="Анализ профиля завершен.")]
            }
        except Exception as e:
            logger.error(f"Ошибка анализа пользователя {user_id}: {e}", exc_info=True)
            return {**state, "error": f"Analysis failed: {e}"}

    @staticmethod
    def provide_assistance_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел предоставления персонализированной помощи - ИСПРАВЛЕНО ДЛЯ РУССКОГО"""
        if not AgentNodes.llm:
            return {**state, "assistance_response": "AI-помощник временно недоступен."}
            
        try:
            user_question = state.get("user_question", "")
            user_analysis = state.get("user_analysis", {})
            user_profile = user_analysis.get("user_profile", {})
            topic = state.get("topic")

            # Поиск релевантного контента
            relevant_content = adaptive_content_service.search_relevant_content(
                query=user_question, topic_filter=topic, n_results=3
            )
            context_text = "\n\n".join([item['document'] for item in relevant_content])

            # ИСПРАВЛЕННЫЙ ПРОМПТ для принуждения к русскому языку
            prompt_text = f"""{RUSSIAN_SYSTEM_PROMPT}

Пользователь задал вопрос: "{user_question}"

Уровень опыта: {user_profile.get("experience_level", "начинающий")}

Релевантная информация из базы знаний:
{context_text}

Дай краткий и понятный ответ (не более 400 слов) ТОЛЬКО на русском языке:
1. Прямо ответь на вопрос
2. Используй простые слова
3. Приведи пример из российского банка
4. Добавь мотивацию к дальнейшему изучению

ВАЖНО: Не показывай размышления, отвечай сразу по существу."""

            # Создаем сообщения с системным промптом
            messages = [
                SystemMessage(content=RUSSIAN_SYSTEM_PROMPT),
                AIMessage(content=prompt_text)
            ]
            
            response = AgentNodes.llm.invoke(messages)
            
            # Очищаем ответ от возможных технических вставок
            clean_response = AgentNodes._clean_response(response.content)
            
            return {**state, "assistance_response": clean_response}
            
        except Exception as e:
            logger.error(f"Ошибка предоставления помощи: {e}", exc_info=True)
            return {**state, "assistance_response": "Извините, не удалось обработать ваш запрос. Попробуйте переформулировать вопрос."}

    @staticmethod
    def adapt_path_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел адаптации пути обучения - ИСПРАВЛЕНО"""
        if not AgentNodes.llm:
            return {**state, "adaptation_message": "Рекомендации временно недоступны."}
        
        try:
            user_analysis = state.get("user_analysis", {})
            user_progress = user_analysis.get("user_progress", {})
            
            # Простой анализ без LLM для надежности
            total_completed = user_progress.get("total_lessons_completed", 0)
            total_score = user_progress.get("total_score", 0)
            
            if total_completed == 0:
                message = "🎯 Начните с изучения основ рисков нарушения непрерывности. Это фундамент для понимания всей методики."
            elif total_score >= 90:
                message = "🌟 Отличные результаты! Вы демонстрируете глубокое понимание материала. Продолжайте в том же духе!"
            elif total_score >= 80:
                message = "✅ Хорошая работа! Вы успешно осваиваете материал. Рекомендуем закрепить знания на практических примерах."
            elif total_score >= 60:
                message = "📚 Рекомендуем уделить больше внимания изучению материалов перед тестированием. Используйте помощь AI-агента."
            else:
                message = "💪 Не сдавайтесь! Повторите пройденные уроки и обязательно изучите материалы. Обращайтесь за помощью к AI."

            return {
                **state,
                "adaptation_message": message,
                "adapted_difficulty": user_analysis.get("content_settings", {}).get("difficulty", "intermediate")
            }
            
        except Exception as e:
            logger.error(f"Ошибка адаптации пути: {e}", exc_info=True)
            return {**state, "adaptation_message": "Продолжайте изучение в текущем темпе!"}

    @staticmethod
    def _clean_response(response: str) -> str:
        """Очистка ответа от технических вставок и китайских символов"""
        import re
        
        # Удаляем китайские символы
        response = re.sub(r'[\u4e00-\u9fff]+', '', response)
        
        # Удаляем технические фразы на английском
        technical_phrases = [
            "Let me think about this",
            "I need to",
            "Based on the context",
            "Here's what",
            "Let me explain"
        ]
        
        for phrase in technical_phrases:
            response = response.replace(phrase, "")
        
        # Удаляем лишние пробелы и переносы
        response = re.sub(r'\s+', ' ', response).strip()
        
        # Ограничиваем длину
        if len(response) > 500:
            response = response[:500] + "..."
        
        return response