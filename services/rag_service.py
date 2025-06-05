"""
RAG сервис для генерации вопросов на основе базы знаний (с ленивой инициализацией)
"""
import json
import logging
import random
from typing import List, Dict, Any, Optional
from pathlib import Path

from config.settings import settings
from core.models import GeneratedQuestion, KnowledgeItem

logger = logging.getLogger(__name__)


class MockCollection:
    """Имитация ChromaDB collection для совместимости"""
    
    def __init__(self, knowledge_base):
        self.knowledge_base = knowledge_base
    
    def count(self):
        return len(self.knowledge_base)


class RAGService:
    """Сервис для работы с базой знаний и генерации вопросов"""
    
    def __init__(self):
        self.embedding_model = None
        self.llm = None
        self.chroma_client = None
        self.collection = None
        self.knowledge_base = []
        self._initialized = False
        
        # Пытаемся инициализировать простую версию
        self._load_simple_knowledge_base()
    
    def _load_simple_knowledge_base(self):
        """Загрузка базы знаний из JSONL файла в память"""
        knowledge_path = Path(settings.knowledge_base_path)
        
        if not knowledge_path.exists():
            logger.warning(f"Файл базы знаний не найден: {knowledge_path}")
            self._create_fallback_knowledge_base()
            return
        
        try:
            with open(knowledge_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        self.knowledge_base.append(data)
            
            logger.info(f"Загружено {len(self.knowledge_base)} элементов в базу знаний")
            
            # Создаем простую имитацию collection для совместимости
            self.collection = MockCollection(self.knowledge_base)
            
        except Exception as e:
            logger.error(f"Ошибка загрузки базы знаний: {e}")
            self._create_fallback_knowledge_base()
    
    def _create_fallback_knowledge_base(self):
        """Создание базовой базы знаний"""
        self.knowledge_base = [
            {
                "prompt": "Что такое риск нарушения непрерывности деятельности?",
                "response": "Риск нарушения непрерывности деятельности банка - это риск возникновения угроз, которые могут привести к нарушению способности банка поддерживать свою операционную устойчивость, исполнять критически важные процессы и операции.",
                "metadata": {"topic": "основы_рисков", "lesson": 1, "difficulty": "beginner", "keywords": ["риск", "непрерывность"]}
            },
            {
                "prompt": "Кто участвует в оценке риска нарушения непрерывности?",
                "response": "В оценке риска участвуют три основные группы: УОР (Управление операционных рисков), владельцы процессов/эксперты процессов, и специализированные подразделения.",
                "metadata": {"topic": "основы_рисков", "lesson": 1, "difficulty": "beginner", "keywords": ["УОР", "владельцы процессов"]}
            },
            {
                "prompt": "Что такое RTO?",
                "response": "RTO (Recovery Time Objective) - это целевое время восстановления процесса после реализации угрозы непрерывности, в течение которого он должен быть восстановлен до приемлемого уровня.",
                "metadata": {"topic": "критичность_процессов", "lesson": 2, "difficulty": "intermediate", "keywords": ["RTO", "время восстановления"]}
            },
            {
                "prompt": "Что такое MTPD?",
                "response": "MTPD (Maximum Tolerable Period of Disruption) - максимально приемлемый период прерывания, по истечении которого неблагоприятные последствия от прерывания деятельности банка становятся неприемлемыми.",
                "metadata": {"topic": "критичность_процессов", "lesson": 2, "difficulty": "intermediate", "keywords": ["MTPD", "период прерывания"]}
            },
            {
                "prompt": "Какие типы угроз выделяются в методике?",
                "response": "В методике выделяется шесть типов угроз: техногенные, социальные, природные, геополитические, экономические и биолого-социальные.",
                "metadata": {"topic": "оценка_рисков", "lesson": 1, "difficulty": "intermediate", "keywords": ["типы угроз", "техногенные", "природные"]}
            }
        ]
        
        self.collection = MockCollection(self.knowledge_base)
        
        logger.info("Создана базовая база знаний")
    
    def _init_advanced_features(self):
        """Ленивая инициализация продвинутых функций"""
        if self._initialized:
            return True
            
        try:
            # Пытаемся инициализировать ChromaDB
            import chromadb
            from chromadb.config import Settings
            
            self.chroma_client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Пытаемся инициализировать LLM
            from langchain_openai import ChatOpenAI
            
            self.llm = ChatOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_api_base,
                model=settings.openai_model,
                temperature=0.7
            )
            
            self._initialized = True
            logger.info("Продвинутые функции RAG инициализированы")
            return True
            
        except Exception as e:
            logger.warning(f"Не удалось инициализировать продвинутые функции: {e}")
            return False
    
    def search_relevant_content(self, query: str, topic: str = None, 
                              lesson: int = None, n_results: int = 5) -> List[Dict[str, Any]]:
        """Поиск релевантного контента в базе знаний"""
        try:
            results = []
            
            for item in self.knowledge_base:
                metadata = item.get("metadata", {})
                
                # Фильтры
                if topic and metadata.get("topic") != topic:
                    continue
                
                if lesson and metadata.get("lesson") != lesson:
                    continue
                
                # Простой поиск по ключевым словам
                text_content = f"{item.get('prompt', '')} {item.get('response', '')}"
                if query.lower() in text_content.lower():
                    results.append({
                        'document': f"Вопрос: {item['prompt']}\nОтвет: {item['response']}",
                        'metadata': metadata,
                        'distance': 0.5  # Заглушка
                    })
            
            return results[:n_results]
            
        except Exception as e:
            logger.error(f"Ошибка поиска в базе знаний: {e}")
            return []
    
    def generate_questions(self, topic: str, lesson_id: int, 
                          difficulty: str = "intermediate", 
                          count: int = 3) -> List[GeneratedQuestion]:
        """Генерация вопросов для урока"""
        try:
            # Пытаемся использовать продвинутую генерацию
            if self._init_advanced_features() and self.llm:
                return self._generate_questions_with_llm(topic, lesson_id, difficulty, count)
            else:
                # Используем статические вопросы
                return self._get_fallback_questions(topic, lesson_id, count)
                
        except Exception as e:
            logger.error(f"Ошибка генерации вопросов: {e}")
            return self._get_fallback_questions(topic, lesson_id, count)
    
    def _generate_questions_with_llm(self, topic: str, lesson_id: int, 
                                   difficulty: str, count: int) -> List[GeneratedQuestion]:
        """Генерация вопросов с помощью LLM"""
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import JsonOutputParser
            
            # Поиск релевантного контента
            relevant_content = self.search_relevant_content(
                query=f"урок {lesson_id} тема {topic}",
                topic=topic,
                lesson=lesson_id,
                n_results=5
            )
            
            if not relevant_content:
                return self._get_fallback_questions(topic, lesson_id, count)
            
            context_text = "\n\n".join([item['document'] for item in relevant_content])
            
            prompt_template = ChatPromptTemplate.from_template("""
Ты - эксперт по банковским рискам. На основе контекста создай {count} вопросов.

Контекст: {context}

Требования:
- Уровень: {difficulty}
- 4 варианта ответа
- Один правильный ответ
- Объяснение к правильному ответу

JSON формат:
[{{"question": "текст", "options": ["1","2","3","4"], "correct_answer": 0, "explanation": "объяснение"}}]
""")
            
            json_parser = JsonOutputParser()
            chain = prompt_template | self.llm | json_parser
            
            result = chain.invoke({
                "context": context_text,
                "difficulty": difficulty,
                "count": count
            })
            
            generated_questions = []
            for item in result:
                try:
                    question = GeneratedQuestion(
                        question=item["question"],
                        options=item["options"],
                        correct_answer=item["correct_answer"],
                        explanation=item["explanation"],
                        source_context=context_text[:300],
                        difficulty=difficulty,
                        confidence_score=0.8
                    )
                    generated_questions.append(question)
                except Exception as e:
                    logger.error(f"Ошибка создания вопроса: {e}")
                    continue
            
            return generated_questions if generated_questions else self._get_fallback_questions(topic, lesson_id, count)
            
        except Exception as e:
            logger.error(f"Ошибка генерации с LLM: {e}")
            return self._get_fallback_questions(topic, lesson_id, count)
    
    def _get_fallback_questions(self, topic: str, lesson_id: int, count: int) -> List[GeneratedQuestion]:
        """Статические вопросы как запасной вариант"""
        fallback_questions = {
            "основы_рисков": {
                1: [
                    GeneratedQuestion(
                        question="Что является основной целью оценки риска нарушения непрерывности деятельности?",
                        options=[
                            "Выявление и анализ угроз непрерывности",
                            "Увеличение прибыли банка", 
                            "Сокращение персонала",
                            "Расширение филиальной сети"
                        ],
                        correct_answer=0,
                        explanation="Основная цель - выявление, анализ и оценка угроз, которые могут нарушить операционную устойчивость банка.",
                        source_context="Базовые знания",
                        difficulty="beginner",
                        confidence_score=0.9
                    ),
                    GeneratedQuestion(
                        question="Кто является инициатором проведения оценки риска нарушения непрерывности?",
                        options=[
                            "Владельцы процессов",
                            "УОР (Управление операционных рисков)",
                            "Специализированные подразделения", 
                            "Руководство банка"
                        ],
                        correct_answer=1,
                        explanation="УОР выступает инициатором проведения оценки, подготавливает данные и верифицирует результаты.",
                        source_context="Базовые знания",
                        difficulty="beginner",
                        confidence_score=0.9
                    ),
                    GeneratedQuestion(
                        question="Какие источники информации используются для оценки риска?",
                        options=[
                            "Только внутренние данные банка",
                            "Только внешние источники информации",
                            "Внутренние и внешние источники информации",
                            "Только данные СМИ"
                        ],
                        correct_answer=2,
                        explanation="Для оценки используются как внутренние данные банка, так и внешние источники информации.",
                        source_context="Базовые знания",
                        difficulty="intermediate",
                        confidence_score=0.9
                    )
                ]
            },
            "критичность_процессов": {
                1: [
                    GeneratedQuestion(
                        question="Что является объектом риска нарушения непрерывности деятельности?",
                        options=[
                            "Процесс категории 'Критически важный'",
                            "Любой бизнес-процесс банка",
                            "Только ИТ-процессы",
                            "Процессы обслуживания клиентов"
                        ],
                        correct_answer=0,
                        explanation="Объектом риска является процесс, категорированный как 'Критически важный'.",
                        source_context="Базовые знания",
                        difficulty="intermediate",
                        confidence_score=0.9
                    )
                ],
                2: [
                    GeneratedQuestion(
                        question="Что означает аббревиатура RTO?",
                        options=[
                            "Recovery Time Objective",
                            "Risk Transfer Operation",
                            "Rapid Technical Operation",
                            "Resource Time Optimization"
                        ],
                        correct_answer=0,
                        explanation="RTO (Recovery Time Objective) - целевое время восстановления процесса.",
                        source_context="Базовые знания",
                        difficulty="intermediate",
                        confidence_score=0.9
                    )
                ]
            }
        }
        
        questions = fallback_questions.get(topic, {}).get(lesson_id, [])
        selected_questions = questions[:count] if questions else []
        
        # Если недостаточно вопросов, добавляем базовые
        while len(selected_questions) < count:
            selected_questions.append(GeneratedQuestion(
                question=f"Вопрос {len(selected_questions) + 1} по теме {topic}",
                options=["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
                correct_answer=0,
                explanation="Базовое объяснение",
                source_context="Автогенерация",
                difficulty="beginner",
                confidence_score=0.5
            ))
        
        return selected_questions
    
    def get_adaptive_questions(self, user_id: str, topic: str, lesson_id: int,
                             user_performance: Dict[str, Any]) -> List[GeneratedQuestion]:
        """Генерация адаптивных вопросов"""
        # Определяем уровень сложности
        avg_score = user_performance.get('average_score', 70)
        
        if avg_score >= 90:
            difficulty = "advanced"
        elif avg_score >= 75:
            difficulty = "intermediate"
        else:
            difficulty = "beginner"
        
        logger.info(f"Адаптивные вопросы для {user_id}: сложность={difficulty}")
        
        return self.generate_questions(
            topic=topic,
            lesson_id=lesson_id,
            difficulty=difficulty,
            count=settings.questions_per_lesson
        )
    
    def get_explanation(self, question: str, user_answer: str, correct_answer: str) -> str:
        """Генерация объяснения для неправильного ответа"""
        try:
            if self.llm:
                # Используем LLM если доступен
                from langchain_core.prompts import ChatPromptTemplate
                
                prompt_template = ChatPromptTemplate.from_template("""
Объясни ошибку пользователя кратко и понятно (2-3 предложения).

Вопрос: {question}
Ответ пользователя: {user_answer}  
Правильный ответ: {correct_answer}
""")
                
                chain = prompt_template | self.llm
                response = chain.invoke({
                    "question": question,
                    "user_answer": user_answer,
                    "correct_answer": correct_answer
                })
                
                return response.content
            else:
                return f"Правильный ответ: {correct_answer}. Изучите материал внимательнее."
                
        except Exception as e:
            logger.error(f"Ошибка генерации объяснения: {e}")
            return "Изучите материал еще раз и попробуйте снова."


# Глобальный экземпляр сервиса
rag_service = RAGService()