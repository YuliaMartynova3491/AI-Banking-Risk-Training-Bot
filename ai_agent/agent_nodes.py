"""
Узлы (nodes) для AI-агента на LangGraph
"""
import logging
from typing import Dict, Any, List
from langchain_core.messages import AIMessage, HumanMessage

from core.database import db_service
from services.rag_service import rag_service
from services.progress_service import progress_service
from config.bot_config import LEARNING_STRUCTURE

logger = logging.getLogger(__name__)


class AgentNodes:
    """Класс, содержащий все узлы AI-агента"""
    
    @staticmethod
    def analyze_user_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел анализа пользователя и его прогресса"""
        user_id = state.get("user_id")
        
        if not user_id:
            return {**state, "error": "User ID not provided"}
        
        try:
            logger.info(f"Анализирую пользователя {user_id}")
            
            # Получаем подробный прогресс
            progress_summary = db_service.get_user_progress_summary(user_id)
            detailed_stats = progress_service.get_overall_statistics(user_id)
            
            # Анализируем паттерны обучения
            learning_patterns = AgentNodes._analyze_learning_patterns(detailed_stats)
            
            # Определяем персональные характеристики
            user_profile = AgentNodes._build_user_profile(progress_summary, detailed_stats)
            
            return {
                **state,
                "user_progress": progress_summary.dict(),
                "detailed_statistics": detailed_stats,
                "learning_patterns": learning_patterns,
                "user_profile": user_profile,
                "messages": state.get("messages", []) + [AIMessage(content="Анализирую ваш прогресс и стиль обучения...")]
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа пользователя {user_id}: {e}")
            return {**state, "error": f"Analysis failed: {str(e)}"}
    
    @staticmethod
    def personalize_content_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел персонализации контента на основе анализа пользователя"""
        try:
            user_profile = state.get("user_profile", {})
            learning_patterns = state.get("learning_patterns", {})
            
            # Определяем стратегию персонализации
            personalization_strategy = AgentNodes._determine_personalization_strategy(
                user_profile, learning_patterns
            )
            
            # Настраиваем параметры контента
            content_settings = AgentNodes._configure_content_settings(personalization_strategy)
            
            return {
                **state,
                "personalization_strategy": personalization_strategy,
                "content_settings": content_settings,
                "messages": state.get("messages", []) + [AIMessage(content="Настраиваю персонализированный подход к обучению...")]
            }
            
        except Exception as e:
            logger.error(f"Ошибка персонализации контента: {e}")
            return {**state, "error": f"Personalization failed: {str(e)}"}
    
    @staticmethod
    def generate_questions_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел генерации адаптивных вопросов"""
        try:
            user_id = state.get("user_id")
            topic = state.get("topic")
            lesson_id = state.get("lesson_id")
            content_settings = state.get("content_settings", {})
            
            # Получаем настройки для генерации
            difficulty = content_settings.get("difficulty", "intermediate")
            question_count = content_settings.get("question_count", 3)
            focus_areas = content_settings.get("focus_areas", [])
            
            # Генерируем вопросы через RAG
            questions = rag_service.generate_questions(
                topic=topic,
                lesson_id=lesson_id,
                difficulty=difficulty,
                count=question_count
            )
            
            # Фильтруем и адаптируем вопросы
            adapted_questions = AgentNodes._adapt_questions_to_user(
                questions, content_settings, focus_areas
            )
            
            return {
                **state,
                "generated_questions": [q.dict() for q in adapted_questions],
                "generation_metadata": {
                    "difficulty": difficulty,
                    "count": len(adapted_questions),
                    "focus_areas": focus_areas
                },
                "messages": state.get("messages", []) + [AIMessage(content=f"Сгенерировал {len(adapted_questions)} персонализированных вопросов")]
            }
            
        except Exception as e:
            logger.error(f"Ошибка генерации вопросов: {e}")
            return {**state, "error": f"Question generation failed: {str(e)}"}
    
    @staticmethod
    def provide_assistance_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел предоставления персонализированной помощи"""
        try:
            user_question = state.get("user_question", "")
            topic = state.get("topic")
            lesson_id = state.get("lesson_id")
            user_profile = state.get("user_profile", {})
            
            # Поиск релевантной информации
            relevant_content = rag_service.search_relevant_content(
                query=user_question,
                topic=topic,
                lesson=lesson_id,
                n_results=3
            )
            
            # Генерируем персонализированный ответ
            personalized_response = AgentNodes._generate_personalized_response(
                user_question, relevant_content, user_profile
            )
            
            return {
                **state,
                "assistance_response": personalized_response,
                "relevant_sources": [item['metadata'] for item in relevant_content],
                "messages": state.get("messages", []) + [AIMessage(content="Подготовил персонализированный ответ...")]
            }
            
        except Exception as e:
            logger.error(f"Ошибка предоставления помощи: {e}")
            return {
                **state,
                "assistance_response": "К сожалению, не могу найти ответ на ваш вопрос. Попробуйте переформулировать.",
                "error": str(e)
            }
    
    @staticmethod
    def adapt_difficulty_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел адаптации уровня сложности"""
        try:
            user_profile = state.get("user_profile", {})
            learning_patterns = state.get("learning_patterns", {})
            current_performance = state.get("current_performance", {})
            
            # Анализируем необходимость адаптации
            adaptation_analysis = AgentNodes._analyze_difficulty_adaptation_need(
                user_profile, learning_patterns, current_performance
            )
            
            # Определяем новый уровень сложности
            new_difficulty = AgentNodes._calculate_optimal_difficulty(adaptation_analysis)
            
            # Генерируем объяснение адаптации
            adaptation_explanation = AgentNodes._generate_adaptation_explanation(
                adaptation_analysis, new_difficulty
            )
            
            return {
                **state,
                "adapted_difficulty": new_difficulty,
                "adaptation_reason": adaptation_analysis["reason"],
                "adaptation_explanation": adaptation_explanation,
                "confidence": adaptation_analysis["confidence"],
                "messages": state.get("messages", []) + [AIMessage(content=adaptation_explanation)]
            }
            
        except Exception as e:
            logger.error(f"Ошибка адаптации сложности: {e}")
            return {
                **state,
                "adapted_difficulty": "intermediate",
                "error": str(e)
            }
    
    @staticmethod
    def provide_encouragement_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел генерации персонализированного поощрения"""
        try:
            user_profile = state.get("user_profile", {})
            performance_data = state.get("performance_data", {})
            context = state.get("encouragement_context", {})
            
            # Определяем тип ситуации
            situation_type = AgentNodes._classify_encouragement_situation(
                performance_data, context
            )
            
            # Генерируем персонализированное сообщение
            encouragement = AgentNodes._generate_personalized_encouragement(
                user_profile, situation_type, performance_data
            )
            
            return {
                **state,
                "encouragement_message": encouragement,
                "situation_type": situation_type,
                "messages": state.get("messages", []) + [AIMessage(content=encouragement)]
            }
            
        except Exception as e:
            logger.error(f"Ошибка генерации поощрения: {e}")
            return {
                **state,
                "encouragement_message": "Продолжайте обучение!",
                "error": str(e)
            }
    
    # Вспомогательные методы
    
    @staticmethod
    def _analyze_learning_patterns(detailed_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ паттернов обучения пользователя"""
        patterns = {
            "learning_speed": "normal",
            "consistency": "variable",
            "strength_areas": [],
            "challenge_areas": [],
            "preferred_difficulty": "intermediate",
            "engagement_level": "medium"
        }
        
        try:
            # Анализ скорости обучения
            completion_rate = detailed_stats.get("overall_completion", 0)
            if completion_rate > 80:
                patterns["learning_speed"] = "fast"
            elif completion_rate < 40:
                patterns["learning_speed"] = "slow"
            
            # Анализ сильных и слабых сторон
            topic_stats = detailed_stats.get("topics_statistics", {})
            for topic_id, stats in topic_stats.items():
                avg_score = stats.get("average_score", 0)
                if avg_score >= 85:
                    patterns["strength_areas"].append(topic_id)
                elif avg_score > 0 and avg_score < 70:
                    patterns["challenge_areas"].append(topic_id)
            
            # Анализ предпочтительной сложности
            avg_score = detailed_stats.get("average_score", 70)
            if avg_score >= 90:
                patterns["preferred_difficulty"] = "advanced"
            elif avg_score < 65:
                patterns["preferred_difficulty"] = "beginner"
            
        except Exception as e:
            logger.error(f"Ошибка анализа паттернов обучения: {e}")
        
        return patterns
    
    @staticmethod
    def _build_user_profile(progress_summary, detailed_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Построение профиля пользователя"""
        profile = {
            "experience_level": "beginner",
            "motivation_level": "medium",
            "learning_style": "balanced",
            "support_needs": "medium",
            "goal_orientation": "completion"
        }
        
        try:
            # Определяем уровень опыта
            completed_lessons = progress_summary.total_lessons_completed
            if completed_lessons >= 10:
                profile["experience_level"] = "advanced"
            elif completed_lessons >= 5:
                profile["experience_level"] = "intermediate"
            
            # Определяем уровень мотивации
            avg_score = detailed_stats.get("average_score", 0)
            if avg_score >= 85:
                profile["motivation_level"] = "high"
            elif avg_score < 60:
                profile["motivation_level"] = "low"
            
            # Определяем потребность в поддержке
            weak_topics_count = len(detailed_stats.get("weak_topics", []))
            if weak_topics_count >= 2:
                profile["support_needs"] = "high"
            elif weak_topics_count == 0:
                profile["support_needs"] = "low"
                
        except Exception as e:
            logger.error(f"Ошибка построения профиля пользователя: {e}")
        
        return profile
    
    @staticmethod
    def _determine_personalization_strategy(user_profile: Dict[str, Any], 
                                          learning_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Определение стратегии персонализации"""
        strategy = {
            "approach": "adaptive",
            "support_level": user_profile.get("support_needs", "medium"),
            "encouragement_frequency": "normal",
            "difficulty_progression": "gradual",
            "content_focus": "balanced"
        }
        
        # Настройка на основе профиля
        if user_profile.get("motivation_level") == "low":
            strategy["encouragement_frequency"] = "high"
            strategy["support_level"] = "high"
        
        if learning_patterns.get("learning_speed") == "fast":
            strategy["difficulty_progression"] = "accelerated"
        elif learning_patterns.get("learning_speed") == "slow":
            strategy["difficulty_progression"] = "gentle"
        
        return strategy
    
    @staticmethod
    def _configure_content_settings(strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Настройка параметров контента"""
        settings = {
            "difficulty": "intermediate",
            "question_count": 3,
            "explanation_detail": "medium",
            "focus_areas": [],
            "hint_availability": True
        }
        
        # Настройка на основе стратегии
        if strategy.get("support_level") == "high":
            settings["explanation_detail"] = "detailed"
            settings["hint_availability"] = True
        elif strategy.get("support_level") == "low":
            settings["explanation_detail"] = "concise"
        
        return settings
    
    @staticmethod
    def _adapt_questions_to_user(questions: List, content_settings: Dict[str, Any], 
                               focus_areas: List[str]) -> List:
        """Адаптация вопросов под пользователя"""
        # В реальной реализации здесь была бы логика фильтрации и адаптации
        # вопросов на основе настроек пользователя
        return questions
    
    @staticmethod
    def _generate_personalized_response(question: str, relevant_content: List[Dict], 
                                      user_profile: Dict[str, Any]) -> str:
        """Генерация персонализированного ответа"""
        # Базовая реализация - в продакшене использовался бы LLM
        response = "На основе вашего вопроса и материала курса: "
        
        if relevant_content:
            # Используем первый релевантный результат
            content = relevant_content[0].get('document', '')
            # Извлекаем ответную часть
            if 'Ответ:' in content:
                answer_part = content.split('Ответ:')[1].strip()
                response += answer_part[:300] + ("..." if len(answer_part) > 300 else "")
            else:
                response += "Информация найдена в учебных материалах."
        else:
            response += "К сожалению, не нашел точной информации по вашему вопросу."
        
        # Добавляем персонализированную поддержку
        support_level = user_profile.get("support_needs", "medium")
        if support_level == "high":
            response += "\n\n💡 Если что-то непонятно, обязательно задавайте дополнительные вопросы!"
        
        return response
    
    @staticmethod
    def _analyze_difficulty_adaptation_need(user_profile: Dict[str, Any], 
                                          learning_patterns: Dict[str, Any],
                                          current_performance: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ необходимости адаптации сложности"""
        analysis = {
            "needs_adaptation": False,
            "reason": "current_level_appropriate",
            "confidence": 0.5,
            "suggested_change": "none"
        }
        
        try:
            current_difficulty = learning_patterns.get("preferred_difficulty", "intermediate")
            recent_scores = current_performance.get("recent_scores", [])
            
            if recent_scores:
                avg_recent_score = sum(recent_scores) / len(recent_scores)
                
                if avg_recent_score >= 95 and current_difficulty != "advanced":
                    analysis.update({
                        "needs_adaptation": True,
                        "reason": "consistently_excellent_performance",
                        "suggested_change": "increase",
                        "confidence": 0.8
                    })
                elif avg_recent_score < 60 and current_difficulty != "beginner":
                    analysis.update({
                        "needs_adaptation": True,
                        "reason": "struggling_with_current_level",
                        "suggested_change": "decrease",
                        "confidence": 0.9
                    })
        
        except Exception as e:
            logger.error(f"Ошибка анализа адаптации сложности: {e}")
        
        return analysis
    
    @staticmethod
    def _calculate_optimal_difficulty(adaptation_analysis: Dict[str, Any]) -> str:
        """Расчет оптимального уровня сложности"""
        if not adaptation_analysis.get("needs_adaptation", False):
            return "intermediate"  # По умолчанию
        
        suggested_change = adaptation_analysis.get("suggested_change", "none")
        
        if suggested_change == "increase":
            return "advanced"
        elif suggested_change == "decrease":
            return "beginner"
        else:
            return "intermediate"
    
    @staticmethod
    def _generate_adaptation_explanation(adaptation_analysis: Dict[str, Any], 
                                       new_difficulty: str) -> str:
        """Генерация объяснения адаптации сложности"""
        if not adaptation_analysis.get("needs_adaptation", False):
            return "Текущий уровень сложности подходит для вас."
        
        reason = adaptation_analysis.get("reason", "")
        
        explanations = {
            "consistently_excellent_performance": f"🌟 Отличные результаты! Повышаю уровень сложности до '{new_difficulty}' для лучшего развития ваших знаний.",
            "struggling_with_current_level": f"📚 Замечаю трудности с текущим материалом. Снижаю сложность до '{new_difficulty}' для лучшего усвоения основ.",
        }
        
        return explanations.get(reason, f"Адаптирую сложность до уровня '{new_difficulty}' на основе вашего прогресса.")
    
    @staticmethod
    def _classify_encouragement_situation(performance_data: Dict[str, Any], 
                                        context: Dict[str, Any]) -> str:
        """Классификация ситуации для поощрения"""
        score = performance_data.get("score", 0)
        is_improvement = context.get("is_improvement", False)
        consecutive_failures = context.get("consecutive_failures", 0)
        
        if score >= 90:
            return "excellent_performance"
        elif score >= 80:
            if is_improvement:
                return "good_improvement"
            else:
                return "good_performance"
        elif score >= 60:
            return "moderate_performance"
        elif consecutive_failures >= 2:
            return "struggling_needs_support"
        else:
            return "needs_encouragement"
    
    @staticmethod
    def _generate_personalized_encouragement(user_profile: Dict[str, Any], 
                                           situation_type: str,
                                           performance_data: Dict[str, Any]) -> str:
        """Генерация персонализированного поощрения"""
        motivation_level = user_profile.get("motivation_level", "medium")
        experience_level = user_profile.get("experience_level", "beginner")
        
        base_messages = {
            "excellent_performance": {
                "high": "🌟 Невероятно! Вы демонстрируете мастерское владение материалом!",
                "medium": "🎉 Отличный результат! Вы отлично разбираетесь в теме!",
                "low": "✨ Великолепно! Видите, как хорошо у вас получается!"
            },
            "good_improvement": {
                "high": "📈 Заметен отличный прогресс! Продолжайте развиваться!",
                "medium": "👏 Хороший рост! Вы движетесь в правильном направлении!",
                "low": "🌱 Прогресс очевиден! У вас все получается!"
            },
            "good_performance": {
                "high": "✅ Стабильно хорошие результаты! Надежно!",
                "medium": "👍 Хороший результат! Вы на правильном пути!",
                "low": "🙂 Неплохо! Вы справляетесь!"
            },
            "moderate_performance": {
                "high": "💪 Есть потенциал для роста! Еще немного усилий!",
                "medium": "📚 Неплохо, но можно лучше! Продолжайте изучать!",
                "low": "🤗 Не расстраивайтесь! Все приходит с практикой!"
            },
            "struggling_needs_support": {
                "high": "🆘 Понимаю, что трудно. Давайте найдем подходящий подход!",
                "medium": "🤝 Не сдавайтесь! Обратитесь за помощью к AI-помощнику!",
                "low": "💙 Все в порядке! Каждый учится в своем темпе!"
            },
            "needs_encouragement": {
                "high": "🎯 Не останавливайтесь! Успех близко!",
                "medium": "🌈 Продолжайте! Каждая попытка приближает к цели!",
                "low": "🌟 Вы молодец, что продолжаете! Это важно!"
            }
        }
        
        # Получаем базовое сообщение
        situation_messages = base_messages.get(situation_type, base_messages["needs_encouragement"])
        base_message = situation_messages.get(motivation_level, situation_messages["medium"])
        
        # Добавляем персонализацию по опыту
        if experience_level == "beginner":
            base_message += " Помните: каждый эксперт когда-то был новичком!"
        elif experience_level == "advanced":
            base_message += " Ваш опыт - отличная основа для дальнейшего роста!"
        
        return base_message
            )
            
            return {
                "adapted_difficulty": new_difficulty,
                "adaptation_reason": adaptation_analysis["reason"],
                "adaptation_explanation": adaptation_explanation,
                "confidence": adaptation_analysis["confidence"],
                "messages": [AIMessage(content=adaptation_explanation)]
            }
            
        except Exception as e:
            logger.error(f"Ошибка адаптации сложности: {e}")
            return {
                "adapted_difficulty": "intermediate",
                "error": str(e)
            }
    
    @staticmethod
    def provide_encouragement_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Узел генерации персонализированного поощрения"""
        try:
            user_profile = state.get("user_profile", {})
            performance_data = state.get("performance_data", {})
            context = state.get("encouragement_context", {})
            
            # Определяем тип ситуации
            situation_type = AgentNodes._classify_encouragement_situation(
                performance_data, context
            )
            
            # Генерируем персонализированное сообщение
            encouragement = AgentNodes._generate_personalized_encouragement(
                user_profile, situation_type, performance_data
            )
            
            return {
                "encouragement_message": encouragement,
                "situation_type": situation_type,
                "messages": [AIMessage(content=encouragement)]
            }
            
        except Exception as e:
            logger.error(f"Ошибка генерации поощрения: {e}")
            return {
                "encouragement_message": "Продолжайте обучение!",
                "error": str(e)
            }
    
    # Вспомогательные методы
    
    @staticmethod
    def _analyze_learning_patterns(detailed_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ паттернов обучения пользователя"""
        patterns = {
            "learning_speed": "normal",
            "consistency": "variable",
            "strength_areas": [],
            "challenge_areas": [],
            "preferred_difficulty": "intermediate",
            "engagement_level": "medium"
        }
        
        try:
            # Анализ скорости обучения
            completion_rate = detailed_stats.get("overall_completion", 0)
            if completion_rate > 80:
                patterns["learning_speed"] = "fast"
            elif completion_rate < 40:
                patterns["learning_speed"] = "slow"
            
            # Анализ сильных и слабых сторон
            topic_stats = detailed_stats.get("topics_statistics", {})
            for topic_id, stats in topic_stats.items():
                avg_score = stats.get("average_score", 0)
                if avg_score >= 85:
                    patterns["strength_areas"].append(topic_id)
                elif avg_score > 0 and avg_score < 70:
                    patterns["challenge_areas"].append(topic_id)
            
            # Анализ предпочтительной сложности
            avg_score = detailed_stats.get("average_score", 70)
            if avg_score >= 90:
                patterns["preferred_difficulty"] = "advanced"
            elif avg_score < 65:
                patterns["preferred_difficulty"] = "beginner"
            
        except Exception as e:
            logger.error(f"Ошибка анализа паттернов обучения: {e}")
        
        return patterns
    
    @staticmethod
    def _build_user_profile(progress_summary, detailed_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Построение профиля пользователя"""
        profile = {
            "experience_level": "beginner",
            "motivation_level": "medium",
            "learning_style": "balanced",
            "support_needs": "medium",
            "goal_orientation": "completion"
        }
        
        try:
            # Определяем уровень опыта
            completed_lessons = progress_summary.total_lessons_completed
            if completed_lessons >= 10:
                profile["experience_level"] = "advanced"
            elif completed_lessons >= 5:
                profile["experience_level"] = "intermediate"
            
            # Определяем уровень мотивации
            avg_score = detailed_stats.get("average_score", 0)
            if avg_score >= 85:
                profile["motivation_level"] = "high"
            elif avg_score < 60:
                profile["motivation_level"] = "low"
            
            # Определяем потребность в поддержке
            weak_topics_count = len(detailed_stats.get("weak_topics", []))
            if weak_topics_count >= 2:
                profile["support_needs"] = "high"
            elif weak_topics_count == 0:
                profile["support_needs"] = "low"
                
        except Exception as e:
            logger.error(f"Ошибка построения профиля пользователя: {e}")
        
        return profile
    
    @staticmethod
    def _determine_personalization_strategy(user_profile: Dict[str, Any], 
                                          learning_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Определение стратегии персонализации"""
        strategy = {
            "approach": "adaptive",
            "support_level": user_profile.get("support_needs", "medium"),
            "encouragement_frequency": "normal",
            "difficulty_progression": "gradual",
            "content_focus": "balanced"
        }
        
        # Настройка на основе профиля
        if user_profile.get("motivation_level") == "low":
            strategy["encouragement_frequency"] = "high"
            strategy["support_level"] = "high"
        
        if learning_patterns.get("learning_speed") == "fast":
            strategy["difficulty_progression"] = "accelerated"
        elif learning_patterns.get("learning_speed") == "slow":
            strategy["difficulty_progression"] = "gentle"
        
        return strategy
    
    @staticmethod
    def _configure_content_settings(strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Настройка параметров контента"""
        settings = {
            "difficulty": "intermediate",
            "question_count": 3,
            "explanation_detail": "medium",
            "focus_areas": [],
            "hint_availability": True
        }
        
        # Настройка на основе стратегии
        if strategy.get("support_level") == "high":
            settings["explanation_detail"] = "detailed"
            settings["hint_availability"] = True
        elif strategy.get("support_level") == "low":
            settings["explanation_detail"] = "concise"
        
        return settings
    
    @staticmethod
    def _adapt_questions_to_user(questions: List, content_settings: Dict[str, Any], 
                               focus_areas: List[str]) -> List:
        """Адаптация вопросов под пользователя"""
        # В реальной реализации здесь была бы логика фильтрации и адаптации
        # вопросов на основе настроек пользователя
        return questions
    
    @staticmethod
    def _generate_personalized_response(question: str, relevant_content: List[Dict], 
                                      user_profile: Dict[str, Any]) -> str:
        """Генерация персонализированного ответа"""
        # Базовая реализация - в продакшене использовался бы LLM
        response = "На основе вашего вопроса и материала курса: "
        
        if relevant_content:
            # Используем первый релевантный результат
            content = relevant_content[0].get('document', '')
            # Извлекаем ответную часть
            if 'Ответ:' in content:
                answer_part = content.split('Ответ:')[1].strip()
                response += answer_part[:300] + ("..." if len(answer_part) > 300 else "")
            else:
                response += "Информация найдена в учебных материалах."
        else:
            response += "К сожалению, не нашел точной информации по вашему вопросу."
        
        # Добавляем персонализированную поддержку
        support_level = user_profile.get("support_needs", "medium")
        if support_level == "high":
            response += "\n\n💡 Если что-то непонятно, обязательно задавайте дополнительные вопросы!"
        
        return response
    
    @staticmethod
    def _analyze_difficulty_adaptation_need(user_profile: Dict[str, Any], 
                                          learning_patterns: Dict[str, Any],
                                          current_performance: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ необходимости адаптации сложности"""
        analysis = {
            "needs_adaptation": False,
            "reason": "current_level_appropriate",
            "confidence": 0.5,
            "suggested_change": "none"
        }
        
        try:
            current_difficulty = learning_patterns.get("preferred_difficulty", "intermediate")
            recent_scores = current_performance.get("recent_scores", [])
            
            if recent_scores:
                avg_recent_score = sum(recent_scores) / len(recent_scores)
                
                if avg_recent_score >= 95 and current_difficulty != "advanced":
                    analysis.update({
                        "needs_adaptation": True,
                        "reason": "consistently_excellent_performance",
                        "suggested_change": "increase",
                        "confidence": 0.8
                    })
                elif avg_recent_score < 60 and current_difficulty != "beginner":
                    analysis.update({
                        "needs_adaptation": True,
                        "reason": "struggling_with_current_level",
                        "suggested_change": "decrease",
                        "confidence": 0.9
                    })
        
        except Exception as e:
            logger.error(f"Ошибка анализа адаптации сложности: {e}")
        
        return analysis
    
    @staticmethod
    def _calculate_optimal_difficulty(adaptation_analysis: Dict[str, Any]) -> str:
        """Расчет оптимального уровня сложности"""
        if not adaptation_analysis.get("needs_adaptation", False):
            return "intermediate"  # По умолчанию
        
        suggested_change = adaptation_analysis.get("suggested_change", "none")
        
        if suggested_change == "increase":
            return "advanced"
        elif suggested_change == "decrease":
            return "beginner"
        else:
            return "intermediate"
    
    @staticmethod
    def _generate_adaptation_explanation(adaptation_analysis: Dict[str, Any], 
                                       new_difficulty: str) -> str:
        """Генерация объяснения адаптации сложности"""
        if not adaptation_analysis.get("needs_adaptation", False):
            return "Текущий уровень сложности подходит для вас."
        
        reason = adaptation_analysis.get("reason", "")
        
        explanations = {
            "consistently_excellent_performance": f"🌟 Отличные результаты! Повышаю уровень сложности до '{new_difficulty}' для лучшего развития ваших знаний.",
            "struggling_with_current_level": f"📚 Замечаю трудности с текущим материалом. Снижаю сложность до '{new_difficulty}' для лучшего усвоения основ.",
        }
        
        return explanations.get(reason, f"Адаптирую сложность до уровня '{new_difficulty}' на основе вашего прогресса.")
    
    @staticmethod
    def _classify_encouragement_situation(performance_data: Dict[str, Any], 
                                        context: Dict[str, Any]) -> str:
        """Классификация ситуации для поощрения"""
        score = performance_data.get("score", 0)
        is_improvement = context.get("is_improvement", False)
        consecutive_failures = context.get("consecutive_failures", 0)
        
        if score >= 90:
            return "excellent_performance"
        elif score >= 80:
            if is_improvement:
                return "good_improvement"
            else:
                return "good_performance"
        elif score >= 60:
            return "moderate_performance"
        elif consecutive_failures >= 2:
            return "struggling_needs_support"
        else:
            return "needs_encouragement"
    
    @staticmethod
    def _generate_personalized_encouragement(user_profile: Dict[str, Any], 
                                           situation_type: str,
                                           performance_data: Dict[str, Any]) -> str:
        """Генерация персонализированного поощрения"""
        motivation_level = user_profile.get("motivation_level", "medium")
        experience_level = user_profile.get("experience_level", "beginner")
        
        base_messages = {
            "excellent_performance": {
                "high": "🌟 Невероятно! Вы демонстрируете мастерское владение материалом!",
                "medium": "🎉 Отличный результат! Вы отлично разбираетесь в теме!",
                "low": "✨ Великолепно! Видите, как хорошо у вас получается!"
            },
            "good_improvement": {
                "high": "📈 Заметен отличный прогресс! Продолжайте развиваться!",
                "medium": "👏 Хороший рост! Вы движетесь в правильном направлении!",
                "low": "🌱 Прогресс очевиден! У вас все получается!"
            },
            "good_performance": {
                "high": "✅ Стабильно хорошие результаты! Надежно!",
                "medium": "👍 Хороший результат! Вы на правильном пути!",
                "low": "🙂 Неплохо! Вы справляетесь!"
            },
            "moderate_performance": {
                "high": "💪 Есть потенциал для роста! Еще немного усилий!",
                "medium": "📚 Неплохо, но можно лучше! Продолжайте изучать!",
                "low": "🤗 Не расстраивайтесь! Все приходит с практикой!"
            },
            "struggling_needs_support": {
                "high": "🆘 Понимаю, что трудно. Давайте найдем подходящий подход!",
                "medium": "🤝 Не сдавайтесь! Обратитесь за помощью к AI-помощнику!",
                "low": "💙 Все в порядке! Каждый учится в своем темпе!"
            },
            "needs_encouragement": {
                "high": "🎯 Не останавливайтесь! Успех близко!",
                "medium": "🌈 Продолжайте! Каждая попытка приближает к цели!",
                "low": "🌟 Вы молодец, что продолжаете! Это важно!"
            }
        }
        
        # Получаем базовое сообщение
        situation_messages = base_messages.get(situation_type, base_messages["needs_encouragement"])
        base_message = situation_messages.get(motivation_level, situation_messages["medium"])
        
        # Добавляем персонализацию по опыту
        if experience_level == "beginner":
            base_message += " Помните: каждый эксперт когда-то был новичком!"
        elif experience_level == "advanced":
            base_message += " Ваш опыт - отличная основа для дальнейшего роста!"
        
        return base_message