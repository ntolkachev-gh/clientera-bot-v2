#!/usr/bin/env python3
"""
Скрипт для остановки стоматологического бота.
"""

import os
import signal
import subprocess
import sys
import time

def find_bot_processes():
    """Находит все процессы бота."""
    try:
        # Ищем процессы с dental_bot в команде
        result = subprocess.run(
            ['ps', 'aux'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        bot_processes = []
        for line in result.stdout.split('\n'):
            if 'dental_bot.py' in line and 'grep' not in line and 'stop_bot.py' not in line:
                parts = line.split()
                if len(parts) >= 2:
                    pid = parts[1]
                    command = ' '.join(parts[10:])  # Команда
                    bot_processes.append({
                        'pid': int(pid),
                        'command': command
                    })
        
        return bot_processes
        
    except subprocess.CalledProcessError as e:
        print(f" Ошибка при поиске процессов: {e}")
        return []

def remove_lock_file():
    """Удаляет файл блокировки."""
    lock_file = "/tmp/dental_bot.lock"
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
            print(f"🗑️ Удален файл блокировки: {lock_file}")
            return True
        else:
            print(f"ℹ️ Файл блокировки не найден: {lock_file}")
            return False
    except Exception as e:
        print(f" Ошибка при удалении файла блокировки: {e}")
        return False

def stop_process(pid, process_name, force=False):
    """Останавливает процесс по PID."""
    try:
        if force:
            # Принудительная остановка
            os.kill(pid, signal.SIGKILL)
            print(f"💀 Принудительно остановлен процесс {pid} ({process_name})")
        else:
            # Мягкая остановка
            os.kill(pid, signal.SIGTERM)
            print(f"🛑 Отправлен сигнал остановки процессу {pid} ({process_name})")
            
        return True
        
    except ProcessLookupError:
        print(f"⚠️ Процесс {pid} уже не существует")
        return True
        
    except PermissionError:
        print(f" Нет прав для остановки процесса {pid}")
        return False
        
    except Exception as e:
        print(f" Ошибка при остановке процесса {pid}: {e}")
        return False

def wait_for_process_to_stop(pid, timeout=10):
    """Ждет остановки процесса."""
    for i in range(timeout):
        try:
            # Проверяем, существует ли еще процесс
            os.kill(pid, 0)  # Не убивает, только проверяет существование
            time.sleep(1)
            print(f"⏳ Ждем остановки процесса {pid}... ({i+1}/{timeout})")
        except ProcessLookupError:
            print(f"Процесс {pid} остановлен")
            return True
    
    return False

def main():
    """Главная функция."""
    print("🛑 Скрипт остановки стоматологического бота")
    print("=" * 50)
    
    # Находим процессы бота
    print("🔍 Поиск запущенных процессов бота...")
    bot_processes = find_bot_processes()
    
    if not bot_processes:
        print("✅ Процессы бота не найдены")
        # Все равно пытаемся удалить файл блокировки
        remove_lock_file()
        return
    
    print(f"📋 Найдено {len(bot_processes)} процессов бота:")
    for i, process in enumerate(bot_processes, 1):
        print(f"  {i}. PID: {process['pid']} - {process['command']}")
    
    # Останавливаем процессы
    print("\n🛑 Останавливаем процессы...")
    
    stopped_pids = []
    failed_pids = []
    
    for process in bot_processes:
        pid = process['pid']
        command = process['command']
        
        # Сначала пытаемся мягко остановить
        if stop_process(pid, command, force=False):
            if wait_for_process_to_stop(pid, timeout=5):
                stopped_pids.append(pid)
            else:
                print(f"⚠️ Процесс {pid} не остановился, применяем принудительную остановку...")
                if stop_process(pid, command, force=True):
                    if wait_for_process_to_stop(pid, timeout=3):
                        stopped_pids.append(pid)
                    else:
                        failed_pids.append(pid)
                else:
                    failed_pids.append(pid)
        else:
            failed_pids.append(pid)
    
    # Удаляем файл блокировки
    print("\n🗑️ Удаляем файл блокировки...")
    remove_lock_file()
    
    # Итоги
    print("\n" + "=" * 50)
    if stopped_pids:
        print(f"Успешно остановлено процессов: {len(stopped_pids)}")
        for pid in stopped_pids:
            print(f"  - PID: {pid}")
    
    if failed_pids:
        print(f" Не удалось остановить процессов: {len(failed_pids)}")
        for pid in failed_pids:
            print(f"  - PID: {pid}")
        print("\n💡 Попробуйте запустить скрипт с sudo или остановите процессы вручную:")
        for pid in failed_pids:
            print(f"  sudo kill -9 {pid}")
    
    if not failed_pids:
        print("🎉 Все процессы бота успешно остановлены!")
        print("✅ Теперь можно запустить бота заново")
    
    print("\n🚀 Для запуска бота используйте:")
    print("  python3 dental_bot.py")

if __name__ == "__main__":
    main()
