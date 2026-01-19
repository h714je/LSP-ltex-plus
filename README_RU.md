

# LSP-ltex-plus

Поддержка проверки грамматики LaTeX/Markdown для плагина LSP в Sublime Text, обеспечиваемая через [ltex-plus/ltex-ls-plus](https://github.com/ltex-plus/ltex-ls-plus).

Этот плагин является форком [LSP-ltex-ls](https://github.com/sublimelsp/LSP-ltex-ls), адаптированным для LTeX Plus.


## Установка

1. Установите [LSP](https://packagecontrol.io/packages/LSP) через Package Control.
2. Установите этот плагин.
3. Перезапустите Sublime. Сервер будет скачан автоматически (требуется подключение к интернету).

**Требования:**
- Java Runtime Environment (JRE) версии 21 или выше должна быть установлена и доступна в системном PATH или настроена через `JAVA_HOME`.
  - Этот плагин скачивает платформо-независимую версию `ltex-ls-plus`, которая **не** включает встроенную Java.

Примечание: В настоящее время LSP игнорирует файлы, не входящие в рабочую область. Добавьте папку в Sublime Text, чтобы включить сервер.

## Известные проблемы

- **Завершение процесса в Windows**: На Windows скрипт `ltex-ls-plus.bat` иногда может оставлять процесс Java запущенным после закрытия Sublime Text. Если вы столкнулись с этим, вы можете настроить запуск Java напрямую в настройках `command`:

  ```json
  "command": [
      "C:\\path\\to\\java.exe", 

      "-Xrs",
      "-Xms64m",
      "-Xmx2G",
      "-Xlog:disable", // ВАЖНО: Запрещаем Java писать логи в stdout

      "-Dapp.name=ltex-ls-plus",
      "-Dapp.home=${serverdir}",
      "-Dbasedir=${serverdir}",

      "-cp",
      "${serverdir}/lib/*",

      "org.bsplines.ltexls.LtexLanguageServerLauncher"
  ],
  ```


## Доступные команды

Доступ к командам через палитру команд (`Ctrl+Shift+P` / `Cmd+Shift+P`):

### LTeX: Clear Diagnostics
Очищает все грамматические и орфографические ошибки из текущего вида. Полезно, когда нужно временно скрыть диагностику для фокусировки на содержании.

### LTeX: Show Status
Показывает диалог с информацией о плагине:
- Версия сервера и статус установки
- Путь установки сервера
- Активный язык проверки
- Статус конфигурации внешних файлов

Помогает при диагностике проблем и проверке конфигурации.

### LTeX: Restart Server
Принудительно перезапускает языковой сервер LTeX. Используйте когда:
- Применяете изменения настроек, требующие перезапуска
- Восстанавливаетесь после ошибок сервера
- Обновляете после ручного редактирования файлов словарей


## Настройка

Вот несколько способов настройки пакета и языкового сервера.

- Через `Preferences > Package Settings > LSP > Servers > LSP-ltex-plus`
- Настройка для конкретного проекта.
  Из палитры команд запустите `Project: Edit Project` и добавьте свои настройки в:

  ```js
  {
     "settings": {
        "LSP": {
           "ltex-plus": {
              "settings": {
                 // Поместите ваши настройки здесь
              }
           }
        }
     }
  }
  ```

### Настройка языка
- Установите строку языка в настройках сервера
- Используйте **Magic Comments Helper**: сниппеты для настройки прямо в коде (например, введите `ltex:lang` для вставки комментария с языком). Подробности см. в [официальной документации](https://ltex-plus.github.io/ltex-plus/advanced-usage.html#magic-comments).

### Внешние файлы

Этот плагин поддерживает хранение словарей, скрытых ложных срабатываний и отключенных правил во внешних файлах. Это полезно для совместного использования конфигураций или поддержания чистоты файла настроек.

Чтобы включить эту функцию, добавьте следующее в ваш `LSP-ltex-plus.sublime-settings`:

```json
{
  "use_external_dictionary_files": true,
  "use_external_hidden_false_positives_files": true,
  "use_external_disabled_rules_files": true
}
```

Когда включено, действия с кодом (Добавить в словарь, Скрыть ложное срабатывание, Отключить правило) будут записывать данные в файлы в директории вашего пакета User вместо обновления файла настроек напрямую.

**Расположение по умолчанию:**
*   Словари: `.../Packages/User/LSP-ltex-plus/dictionaries/{lang}.txt`
*   Скрытые ложные срабатывания: `.../Packages/User/LSP-ltex-plus/hidden_false_positives/hiddenFalsePositives.{lang}.txt`
*   Отключенные правила: `.../Packages/User/LSP-ltex-plus/disabled_rules/disabledRules.{lang}.txt`

**Пользовательское расположение:**
Вы можете настроить директории, задав параметры:
*   `external_dictionary_dir`
*   `external_hidden_false_positives_dir`
*   `external_disabled_rules_dir`

Пример:
```json
{
  "use_external_dictionary_files": true,
  "external_dictionary_dir": "~/Dropbox/ltex/dictionaries"
}
```

## Благодарности

*   Основано на [LSP-ltex-ls](https://github.com/sublimelsp/LSP-ltex-ls).
*   Работает на базе [ltex-plus](https://github.com/ltex-plus/ltex-ls-plus).
