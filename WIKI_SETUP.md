# Wiki Setup Instructions

GitHub Wiki для ReliAPI нужно инициализировать вручную через веб-интерфейс.

## Шаги для создания Wiki:

1. **Откройте Wiki страницу:**
   ```
   https://github.com/KikuAI-Lab/reliapi/wiki
   ```

2. **Создайте первую страницу:**
   - Нажмите "Create the first page"
   - Название: `Home`
   - Содержимое: скопируйте из `docs/wiki/Home.md`
   - Нажмите "Save Page"

3. **После создания первой страницы**, запустите скрипт:
   ```bash
   ./scripts/create_wiki.sh
   ```

   Или создайте страницы вручную через веб-интерфейс, скопировав содержимое из:
   - `docs/wiki/Overview.md`
   - `docs/wiki/Architecture.md`
   - `docs/wiki/Configuration.md`
   - `docs/wiki/Reliability-Features.md`
   - `docs/wiki/Comparison.md`

## Альтернативный способ (через клонирование Wiki репозитория):

После создания первой страницы через веб-интерфейс, GitHub создаст репозиторий `reliapi.wiki`.

Тогда можно клонировать и добавить файлы:

```bash
# Клонировать Wiki репозиторий
gh repo clone KikuAI-Lab/reliapi.wiki /tmp/reliapi-wiki

# Скопировать файлы
cp docs/wiki/*.md /tmp/reliapi-wiki/

# Закоммитить и запушить
cd /tmp/reliapi-wiki
git add *.md
git commit -m "Add all wiki pages"
git push origin main
```

## Готовые файлы:

Все Wiki страницы готовы в `docs/wiki/`:
- `Home.md` - главная страница
- `Overview.md` - обзор
- `Architecture.md` - архитектура
- `Configuration.md` - конфигурация
- `Reliability-Features.md` - функции надежности
- `Comparison.md` - сравнение с другими инструментами

