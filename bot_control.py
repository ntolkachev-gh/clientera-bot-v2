#!/usr/bin/env python3
"""
Простой скрипт для управления стоматологическим ботом.
"""

import sys
import subprocess
import os

def show_help():
    """Показывает справку."""
    print("🦷 Управление стоматологическим ботом")
    print("=" * 40)
    print("Использование:")
    print("  python3 bot_control.py start   - Запустить бота")
    print("  python3 bot_control.py stop    - Остановить бота")  
    print("  python3 bot_control.py restart - Перезапустить бота")
    print("  python3 bot_control.py status  - Статус бота")
    print("  python3 bot_control.py help    - Показать справку")

def check_bot_running():
    """Проверяет, запущен ли бот."""
    try:
        result = subprocess.run(
            ['ps', 'aux'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        for line in result.stdout.split('\n'):
            if 'dental_bot.py' in line and 'grep' not in line and 'bot_control.py' not in line:
                return True
        return False
        
    except subprocess.CalledProcessError:
        return False

def start_bot():
    """Запускает бота."""
    print("🚀 Запуск стоматологического бота...")
    
    if check_bot_running():
        print("⚠️ Бот уже запущен!")
        return False
    
    try:
        # Запускаем бота в фоновом режиме
        subprocess.Popen(
            ['python3', 'dental_bot.py'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        
        print("✅ Бот запущен в фоновом режиме")
        print("📋 Для просмотра логов используйте: tail -f /tmp/dental_bot.log")
        return True
        
    except Exception as e:
        print(f" Ошибка запуска бота: {e}")
        return False

def stop_bot():
    """Останавливает бота."""
    print("🛑 Остановка бота...")
    
    try:
        result = subprocess.run(['python3', 'stop_bot.py'], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.returncode == 0
        
    except Exception as e:
        print(f" Ошибка остановки бота: {e}")
        return False

def restart_bot():
    """Перезапускает бота."""
    print("🔄 Перезапуск бота...")
    
    if check_bot_running():
        print("🛑 Останавливаем текущий экземпляр...")
        if not stop_bot():
            print(" Не удалось остановить бота")
            return False
    
    print("🚀 Запускаем бота...")
    return start_bot()

def show_status():
    """Показывает статус бота."""
    print("📊 Статус стоматологического бота:")
    print("=" * 40)
    
    if check_bot_running():
        print("🟢 Статус: ЗАПУЩЕН")
        
        # Показываем информацию о процессе
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, check=True)
            for line in result.stdout.split('\n'):
                if 'dental_bot.py' in line and 'grep' not in line and 'bot_control.py' not in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        pid = parts[1]
                        cpu = parts[2]
                        mem = parts[3]
                        print(f"📋 PID: {pid}")
                        print(f"💻 CPU: {cpu}%")
                        print(f"🧠 Memory: {mem}%")
                        break
        except:
            pass
            
        # Проверяем файл блокировки
        lock_file = "/tmp/dental_bot.lock"
        if os.path.exists(lock_file):
            print(f"🔒 Файл блокировки: {lock_file}")
        
    else:
        print("🔴 Статус: ОСТАНОВЛЕН")
        
        # Проверяем, есть ли забытый файл блокировки
        lock_file = "/tmp/dental_bot.lock"
        if os.path.exists(lock_file):
            print(f"⚠️ Найден забытый файл блокировки: {lock_file}")
            print("💡 Запустите: python3 stop_bot.py для очистки")

def main():
    """Главная функция."""
    if len(sys.argv) != 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'start':
        start_bot()
    elif command == 'stop':
        stop_bot()
    elif command == 'restart':
        restart_bot()
    elif command == 'status':
        show_status()
    elif command in ['help', '--help', '-h']:
        show_help()
    else:
        print(f" Неизвестная команда: {command}")
        show_help()

if __name__ == "__main__":
    main()
