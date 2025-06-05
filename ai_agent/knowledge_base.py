"""
Модуль для работы с базой знаний на основе ChromaDB
"""

import json
import os
import logging
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

class KnowledgeBase:
    def __init__(self, data_dir: str = "data"):
        """Инициализация базы знаний"""
        self.data_dir = data_dir
        self.chroma_db_path = os.path.join(data_dir, "chroma_db")
        
        # Создаем директорию если не существует
        os.makedirs(self.chroma_db_path, exist_ok=True)
        
        # Инициализация ChromaDB
        self.client = chromadb.PersistentClient(
            path=self.chroma_db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Создание или получение коллекции
        self.collection = self.client.get_or_create_collection(
            name="risk_continuity_knowledge",
            metadata={"description": "База знаний по рискам непрерывности деятельности банка"}
        )
        
        # Загрузка базы знаний при инициализации
        self.load_knowledge_base()
    
    def load_knowledge_base(self):
        """Загрузка базы знаний из файла"""
        knowledge_file = os.path.join(self.data_dir, "knowledge_base.jsonl")
        
        if not os.path.exists(knowledge_file):
            logger.warning(f"Файл базы знаний не найден: {knowledge_file}")
            return
        
        try:
            # Проверяем, есть ли уже данные в коллекции
            existing_count = self.collection.count()
            if existing_count > 0:
                logger.info(f"База знаний уже загружена. Документов: {existing_count}")
                return
            
            documents = []
            metadatas = []
            ids = []
            
            with open(knowledge_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        
                        # Формируем документ для поиска (промпт + ответ)
                        document_text = f"Вопрос: {data['prompt']}\nОтвет: {data['response']}"
                        
                        # Подготовка метаданных с правильными типами
                        metadata = {
                            "topic": str(data["metadata"]["topic"]),
                            "lesson": int(data["metadata"]["lesson"]),
                            "difficulty": str(data["metadata"]["difficulty"]),
                            "keywords": ", ".join(data["metadata"]["keywords"]) if isinstance(data["metadata"]["keywords"], list) else str(data["metadata"]["keywords"]),
                            "prompt": str(data["prompt"])
                        }
                        
                        documents.append(document_text)
                        metadatas.append(metadata)
                        ids.append(f"doc_{line_num}")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Ошибка парсинга JSON в строке {line_num}: {e}")
                        continue
                    except KeyError as e:
                        logger.error(f"Отсутствует обязательное поле в строке {line_num}: {e}")
                        continue
            
            if documents:
                # Добавляем документы в коллекцию
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(f"Загружено {len(documents)} документов в базу знаний")
            else:
                logger.warning("Не найдено валидных документов для загрузки")
                
        except Exception as e:
            logger.error(f"Ошибка загрузки базы знаний: {e}")
            raise
    
    def search(self, query: str, n_results: int = 5, topic_filter: str = None) -> List[Dict[str, Any]]:
        """
        Поиск релевантных документов
        
        Args:
            query: Поисковый запрос
            n_results: Количество результатов
            topic_filter: Фильтр по теме
            
        Returns:
            Список найденных документов с метаданными
        """
        try:
            # Подготовка фильтра
            where_filter = {}
            if topic_filter:
                where_filter["topic"] = {"$eq": topic_filter}
            
            # Выполнение поиска
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"]
            )
            
            # Форматирование результатов
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    result = {
                        "document": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else 0.0
                    }
                    formatted_results.append(result)
            
            logger.debug(f"Найдено {len(formatted_results)} релевантных документов для запроса: {query}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Ошибка поиска в базе знаний: {e}")
            return []
    
    def get_documents_by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Получение всех документов по определенной теме"""
        try:
            results = self.collection.get(
                where={"topic": {"$eq": topic}},
                include=["documents", "metadatas"]
            )
            
            formatted_results = []
            if results['documents']:
                for i, doc in enumerate(results['documents']):
                    result = {
                        "document": doc,
                        "metadata": results['metadatas'][i] if results['metadatas'] else {}
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Ошибка получения документов по теме {topic}: {e}")
            return []
    
    def get_available_topics(self) -> List[str]:
        """Получение списка доступных тем"""
        try:
            # Получаем все метаданные
            results = self.collection.get(include=["metadatas"])
            
            topics = set()
            if results['metadatas']:
                for metadata in results['metadatas']:
                    if 'topic' in metadata:
                        topics.add(metadata['topic'])
            
            return sorted(list(topics))
            
        except Exception as e:
            logger.error(f"Ошибка получения списка тем: {e}")
            return []
    
    def add_document(self, prompt: str, response: str, metadata: Dict[str, Any]) -> bool:
        """
        Добавление нового документа в базу знаний
        
        Args:
            prompt: Вопрос
            response: Ответ
            metadata: Метаданные документа
            
        Returns:
            True если документ успешно добавлен
        """
        try:
            document_text = f"Вопрос: {prompt}\nОтвет: {response}"
            
            # Подготовка метаданных
            clean_metadata = {
                "topic": str(metadata.get("topic", "общее")),
                "lesson": int(metadata.get("lesson", 1)),
                "difficulty": str(metadata.get("difficulty", "beginner")),
                "keywords": ", ".join(metadata.get("keywords", [])) if isinstance(metadata.get("keywords"), list) else str(metadata.get("keywords", "")),
                "prompt": str(prompt)
            }
            
            # Генерация уникального ID
            doc_id = f"doc_{self.collection.count() + 1}"
            
            # Добавление документа
            self.collection.add(
                documents=[document_text],
                metadatas=[clean_metadata],
                ids=[doc_id]
            )
            
            logger.info(f"Добавлен новый документ с ID: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления документа: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Получение статистики коллекции"""
        try:
            count = self.collection.count()
            topics = self.get_available_topics()
            
            return {
                "total_documents": count,
                "topics_count": len(topics),
                "available_topics": topics
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {"total_documents": 0, "topics_count": 0, "available_topics": []}
    
    def reset_collection(self):
        """Сброс коллекции (осторожно - удаляет все данные!)"""
        try:
            self.client.delete_collection("risk_continuity_knowledge")
            self.collection = self.client.get_or_create_collection(
                name="risk_continuity_knowledge",
                metadata={"description": "База знаний по рискам непрерывности деятельности банка"}
            )
            logger.info("Коллекция сброшена")
            
        except Exception as e:
            logger.error(f"Ошибка сброса коллекции: {e}")


# Глобальный экземпляр базы знаний
_knowledge_base = None

def get_knowledge_base() -> KnowledgeBase:
    """Получение глобального экземпляра базы знаний"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base