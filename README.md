# CIDR Merger & IP Range Parser (IP2Location)

**Удобное графическое приложение** для работы с IP-диапазонами и CIDR-блоками.

Приложение загружает **актуальные IPv4-диапазоны стран** напрямую с сайта [IP2Location LITE](https://lite.ip2location.com), объединяет пересекающиеся диапазоны и конвертирует между форматами.

## Возможности

- Загрузка IP-диапазонов для любой страны (или нескольких сразу) с IP2Location (RU/EN версия).
- Автоматическое **слияние** пересекающихся и соседних диапазонов.
- Конвертация:
  - Диапазоны `IP-IP` ↔ **CIDR** (`a.b.c.d/xx`)
  - Одиночные IP тоже поддерживаются.
- Поиск по названию страны + множественный выбор.
- Импорт / экспорт списков в `.txt`.
- Статистика загруженных стран.
- Сохранение размера и позиции окна.
- Горячие клавиши (`Ctrl+C`, `Ctrl+V`, `Ctrl+A` и др.) + контекстное меню.
- Поддержка русского и английского интерфейса сайта.

## Скриншоты

<img width="1199" height="710" alt="image" src="https://github.com/user-attachments/assets/4a291b7e-3905-4012-aa4d-341f62ca599d" />
<img width="1201" height="712" alt="image" src="https://github.com/user-attachments/assets/66d4023f-20d2-4ad5-b368-f460d7845c50" />


## Установка и запуск

### 1. Клонирование репозитория

```bash
git clone https://github.com/nebbbes/CIDR_Merger_IP_Range_Parser.git
cd CIDR_Merger_IP_Range_Parser
2. Установка зависимостей
pip install -r requirements.txt
3. Запуск
python ip.py
Требования:

Python 3.8 или выше
Интернет-соединение (для загрузки диапазонов стран)

Сборка в исполняемый .exe (Windows)
## 🚀 Скачать готовый .exe (Windows)

[![Download CIDR_Merger.exe](https://img.shields.io/badge/Download-CIDR_Merger.exe-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/nebbbes/CIDR_Merger_IP_Range_Parser/releases/latest/download/CIDR_Merger.exe)

**[Все релизы →](https://github.com/nebbbes/CIDR_Merger_IP_Range_Parser/releases/latest)**

Коротко сборка в исполняемый .exe (в PowerShell):
PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install requests beautifulsoup4 pyinstaller
pyinstaller --onefile --windowed --clean --name "CIDR_Merger" ip.py
Готовый .exe появится в папке dist/.

Файлы проекта

ip.py — основной код приложения
requirements.txt
ip_merger_settings.ini — создаётся автоматически (настройки окна)
