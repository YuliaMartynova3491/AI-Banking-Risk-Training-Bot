# Файл: core/knowledge_base.py

"""
Модуль для работы с базой знаний на основе ChromaDB (ИСПРАВЛЕННАЯ ВЕРСИЯ)
- Убрана циклическая ссылка на самого себя
- Улучшена обработка ошибок
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
        self.data_dir = data_dir
        self.chroma_db_path = os.path.join(data_dir, "chroma_db")
        os.makedirs(self.chroma_db_path, exist_ok=True)
        
        try:
            self.client = chromadb.PersistentClient(
                path=self.chroma_db_path,
                settings=Settings(anonymized_telemetry=False, allow_reset=True)
            )
            self.collection = self.client.get_or_create_collection(
                name="risk_continuity_knowledge",
                metadata={"hnsw:space": "cosine"} # Рекомендуется для эмбеддингов
            )
            self.load_knowledge_base()
        except Exception as e:
            logger.critical(f"Не удалось инициализировать ChromaDB: {e}. Проверьте зависимости и права доступа.")
            raise

    def load_knowledge_base(self):
        knowledge_file = os.path.join(self.data_dir, "knowledge_base.jsonl")
        if not os.path.exists(knowledge_file):
            logger.warning(f"Файл базы знаний не найден: {knowledge_file}")
            return

        if self.collection.count() > 0:
            logger.info(f"База знаний уже загружена. Документов: {self.collection.count()}")
            return
        
        documents, metadatas, ids = [], [], []
        with open(knowledge_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                try:
                    data = json.loads(line)
                    doc_text = f"Вопрос: {data['prompt']}\nОтвет: {data['response']}"
                    metadata = {k: str(v) for k, v in data["metadata"].items()}
                    metadata["prompt"] = data["prompt"] # Добавляем оригинальный вопрос в метаданные
                    documents.append(doc_text)
                    metadatas.append(metadata)
                    ids.append(f"doc_{i}")
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Ошибка парсинга строки {i} в knowledge_base.jsonl: {e}")

        if documents:
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
            logger.info(f"Загружено {len(documents)} документов в базу знаний.")

    def search(self, query: str, n_results: int = 5, topic_filter: str = None) -> List[Dict[str, Any]]:
        try:
            where_filter = {"topic": topic_filter} if topic_filter else None
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    result = {
                        "document": doc,
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i]
                    }
                    formatted_results.append(result)
            return formatted_results
        except Exception as e:
            logger.error(f"Ошибка поиска в базе знаний: {e}")
            return []
    
    def get_documents_by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Получение всех документов по определенной теме."""
        try:
            # Используем get, а не query, для получения документов по фильтру
            results = self.collection.get(
                where={"topic": topic},
                include=["documents", "metadatas"]
            )
            
            formatted_results = []
            if results['documents']:
                for i, doc in enumerate(results['documents']):
                    result = {
                        "document": doc,
                        "metadata": results['metadatas'][i]
                    }
                    formatted_results.append(result)
            return formatted_results
        except Exception as e:
            logger.error(f"Ошибка получения документов по теме {topic}: {e}")
            return []

# Глобальный экземпляр для "ленивой" загрузки
_knowledge_base_instance = None

def get_knowledge_base() -> KnowledgeBase:
    """
    Получение глобального экземпляра базы знаний.
    Создает его только при первом вызове.
    """
    global _knowledge_base_instance
    if _knowledge_base_instance is None:
        _knowledge_base_instance = KnowledgeBase()
    return _knowledge_base_instance