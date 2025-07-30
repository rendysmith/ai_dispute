import asyncio
import os
import time

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

import torch
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity


dotenv_path = os.path.dirname(os.path.dirname(__file__))
print(dotenv_path)

abspath_path = os.path.dirname(os.path.abspath(__file__))
print(abspath_path)

async def save_model(model_name, save_path):
    '''Функция для скачивания моделей
    model_name: название модели на huggingface.co
    save_path: куда модель скачивать
    '''
    # Загружаем модель и сохраняем её в указанную директорию
    #model_name = 'sentence-transformers/all-MiniLM-L6-v2'

    # Создаём экземпляр модели
    model = SentenceTransformer(model_name)

    # Сохраняем модель на локальный диск
    model.save(save_path)

async def classify_topic(text, topics, threshold=0.4):
    #save_path = os.path.join(abspath_path, 'llm_model/all-MiniLM-L6-v2/')  # Путь для сохранения модели
    #model = SentenceTransformer(save_path)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    #model = SentenceTransformer("all-mpnet-base-v2")

    # Преобразуем все входные данные в эмбеддинги
    topic_embeddings = model.encode(topics)
    text_embedding = model.encode([text])

    # Вычисляем косинусную схожесть
    similarities = cosine_similarity(text_embedding, topic_embeddings)

    # Находим индекс наиболее подходящей темы
    most_similar_idx = similarities.argmax()
    max_similarity = similarities[0][most_similar_idx]

    if max_similarity < threshold:
        return "Неопределено", max_similarity

    return topics[most_similar_idx], similarities[0][most_similar_idx]


# Пример использования
if __name__ == "__main__":

    # Задаем список тем
    topics = [
        'Выгода',
        'Город Авто',
        'Город Афиша',
        'Город Продукты',
        'Город Топливо',
        'Мобайл',
        'МП Кошелёк',
        'Путешествия общие',
        'РК Выгода Промподборка',
        'Tbooking/Отели',
        'Travel/Авиабилеты'
    ]
    # Пример текста для классификации
    print('-- Мобайл')
    input_text = "У Тинькофф нет безлимита на мессенджеры, поэтому быстро кончаются гигабайты"

    # Определяем тему
    start_time = time.time()
    topic, confidence = asyncio.run(classify_topic(input_text, topics))


    print(f"Уверенность: {confidence:.2f}")
    print(f"Текст относится к теме: {topic}")
    print(time.time() - start_time)

