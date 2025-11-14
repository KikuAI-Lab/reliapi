# План миграции и очистки репозиториев

**Дата:** 2025-01-15

---

## Задачи

1. ✅ Обновить публичный репозиторий ReliAPI (https://github.com/KikuAI-Lab/reliapi)
2. ⏳ Создать приватный форк и загрузить туда весь код reliapi/
3. ⏳ Удалить старые репозитории (stability-llm, deepstabilizer) на GitHub
4. ⏳ Очистить локальные файлы от мусора

---

## Шаг 1: Обновление публичного репозитория

### Файлы для обновления:
- ✅ README.md - обновлен на основе reliapi/README.md
- ⏳ docs/index.html - демо страница (уже обновлена ранее)
- ⏳ docs/wiki/* - Wiki страницы (уже обновлены ранее)

### Команды для коммита:
```bash
cd public-repo
git add README.md docs/
git commit -m "feat: Update README with new structure and streaming support"
git push origin main
```

---

## Шаг 2: Создание приватного репозитория

### Вариант A: Создать новый приватный репозиторий
```bash
# На GitHub создать новый приватный репозиторий: reliapi-private
# Затем:
cd /Users/nick/myprojects/Cursor/StabilityLLM
git clone https://github.com/KikuAI-Lab/reliapi-private.git reliapi-private
cd reliapi-private
# Скопировать весь код из reliapi/
cp -r ../reliapi/* .
cp -r ../reliapi/.* . 2>/dev/null || true
git add .
git commit -m "Initial commit: Full ReliAPI codebase"
git push origin main
```

### Вариант B: Использовать существующий репозиторий
Если есть существующий приватный репозиторий, просто загрузить туда код.

---

## Шаг 3: Проверка важных данных перед удалением

### deepstabilizer/
**Важные файлы для сохранения:**
- `deploy/config.prod.yaml` - production конфигурация
- `deploy/env.kiku-prod.example` - пример env переменных
- `deploy/nginx-deepstabilizer.conf` - nginx конфигурация
- `deploy/docker-compose.prod.yml` - docker compose для production
- `README.md` - документация (может быть полезной)
- `RELEASE_NOTES.md` - история релизов

**Можно удалить:**
- Все deploy скрипты (много дубликатов)
- Старые тесты
- Kubernetes конфигурации (если не используются)

### llm-router/
**Проверить:**
- Есть ли уникальная функциональность, которой нет в reliapi?
- Есть ли важные конфигурации?

### docs/ (корневой)
**Проверить:**
- Какие документы актуальны?
- Какие можно удалить?

---

## Шаг 4: Удаление старых репозиториев на GitHub

### Команды (требуют GitHub CLI или веб-интерфейс):
```bash
# Через GitHub CLI (если установлен)
gh repo delete KikuAI-Lab/stability-llm --confirm
gh repo delete KikuAI-Lab/deepstabilizer --confirm

# Или через веб-интерфейс:
# Settings → Danger Zone → Delete this repository
```

**ВАЖНО:** Перед удалением убедиться, что:
1. Все важные данные сохранены
2. Нет активных зависимостей от этих репозиториев
3. Все важные конфигурации перенесены в reliapi/

---

## Шаг 5: Очистка локальных файлов

### Директории для удаления:
```bash
# Старые проекты
rm -rf deepstabilizer/
rm -rf llm-router/

# Старые документы (если не используются)
rm -rf docs/  # кроме docs/reliapi/ если есть

# Старые OpenAPI спецификации (если не используются)
rm -rf openapi/

# Временные файлы
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete
find . -name ".pytest_cache" -type d -exec rm -rf {} +
find . -name ".mypy_cache" -type d -exec rm -rf {} +
```

### Файлы для проверки перед удалением:
- `docker-compose.yml` (корневой) - используется ли?
- `Makefile` (корневой) - используется ли?
- `README.md` (корневой) - можно удалить, если есть reliapi/README.md

---

## Итоговая структура

После очистки должна остаться:
```
StabilityLLM/
├── reliapi/          # Основной код (приватный репозиторий)
├── public-repo/      # Публичная документация и демо
└── .git/            # Git репозиторий (если нужен)
```

---

## Чеклист перед удалением

- [ ] Все важные конфигурации сохранены
- [ ] Все важные скрипты сохранены
- [ ] Публичный репозиторий обновлен
- [ ] Приватный репозиторий создан и код загружен
- [ ] Нет активных зависимостей от старых репозиториев
- [ ] Локальная очистка выполнена
- [ ] Старые репозитории удалены на GitHub

