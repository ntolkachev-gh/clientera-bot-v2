#!/usr/bin/env python3
"""
Тест для проверки исправлений в обработке стримов.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dental_bot import DentalRealtimeClient
import asyncio


async def test_stream_cleanup():
    """Тест очистки стримов и response_id."""
    client = DentalRealtimeClient()
    
    # Симулируем создание стрима
    user_id = 12345
    response_id = "resp_12345_123"
    openai_response_id = "resp_CELgRJCVFxPR1BL0SxK8B"
    
    # Создаем стрим
    client.active_streams[user_id] = {
        "response_id": response_id,
        "openai_response_id": openai_response_id,
        "accumulated_text": "Test text",
        "completed": False,
        "finalized": False,
        "created_at": asyncio.get_event_loop().time()
    }
    
    # Добавляем связи response_id -> user_id
    client.response_to_user[response_id] = user_id
    client.response_to_user[openai_response_id] = user_id
    
    print(f"До очистки:")
    print(f"  active_streams: {list(client.active_streams.keys())}")
    print(f"  response_to_user: {list(client.response_to_user.keys())}")
    print(f"  completed_responses: {len(client.completed_responses)}")
    
    # Симулируем отмену стрима
    await client.cancel_stream(user_id)
    
    print(f"\nПосле очистки:")
    print(f"  active_streams: {list(client.active_streams.keys())}")
    print(f"  response_to_user: {list(client.response_to_user.keys())}")
    print(f"  completed_responses: {len(client.completed_responses)}")
    
    # Проверяем, что все очищено
    assert len(client.active_streams) == 0, "active_streams должен быть пуст"
    assert len(client.response_to_user) == 0, "response_to_user должен быть пуст"
    assert response_id in client.completed_responses, f"response_id {response_id} должен быть в completed_responses"
    assert openai_response_id in client.completed_responses, f"openai_response_id {openai_response_id} должен быть в completed_responses"
    
    print("✅ Тест очистки стримов прошел успешно!")


async def test_duplicate_event_handling():
    """Тест обработки дублированных событий."""
    client = DentalRealtimeClient()
    
    # Симулируем response_id который уже завершен
    completed_response_id = "resp_CELgRJCVFxPR1BL0SxK8B"
    client.completed_responses.add(completed_response_id)
    
    print(f"Тестируем обработку дублированных событий для {completed_response_id}")
    
    # Симулируем события для уже завершенного response
    delta_event = {
        "type": "response.text.delta",
        "response_id": completed_response_id,
        "delta": "Some text"
    }
    
    done_event = {
        "type": "response.text.done",
        "response_id": completed_response_id,
        "text": "Complete text"
    }
    
    response_done_event = {
        "type": "response.done",
        "response_id": completed_response_id,
        "response": {
            "id": completed_response_id,
            "status": "completed"
        }
    }
    
    # Обрабатываем события - они должны быть проигнорированы
    await client.handle_event(delta_event)
    await client.handle_event(done_event) 
    await client.handle_event(response_done_event)
    
    print("✅ Тест обработки дублированных событий прошел успешно!")


async def test_cleanup_old_responses():
    """Тест очистки старых completed_responses."""
    client = DentalRealtimeClient()
    
    # Добавляем много completed_responses
    for i in range(1200):
        client.completed_responses.add(f"resp_test_{i}")
    
    print(f"До очистки: {len(client.completed_responses)} completed_responses")
    
    # Принудительно вызываем очистку
    client._last_cleanup = 0  # Сбрасываем время последней очистки
    client.cleanup_old_responses()
    
    print(f"После очистки: {len(client.completed_responses)} completed_responses")
    
    # Проверяем, что количество уменьшилось
    assert len(client.completed_responses) <= 500, "completed_responses должно быть <= 500"
    
    print("✅ Тест очистки старых записей прошел успешно!")


async def main():
    """Запуск всех тестов."""
    print("🧪 Запуск тестов исправлений стримов...")
    
    await test_stream_cleanup()
    print()
    
    await test_duplicate_event_handling()
    print()
    
    await test_cleanup_old_responses()
    print()
    
    print("🎉 Все тесты прошли успешно!")


if __name__ == "__main__":
    asyncio.run(main())
