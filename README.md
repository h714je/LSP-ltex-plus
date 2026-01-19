

# LSP-ltex-plus

Latex/Markdown grammar check support for Sublime's LSP plugin provided through [ltex-plus/ltex-ls-plus](https://github.com/ltex-plus/ltex-ls-plus).

This plugin is a fork of [LSP-ltex-ls](https://github.com/sublimelsp/LSP-ltex-ls) adapted for LTeX Plus.


## Installation

1. Install [LSP](https://packagecontrol.io/packages/LSP) via Package Control.
2. Install this plugin.
3. Restart Sublime. The server will be downloaded automatically (requires internet connection).

**New in v1.2.0:**
- The plugin now auto-detects your platform (Windows/macOS/Linux) and architecture (x64/ARM64)
- Downloads the appropriate version **with bundled Java** - no separate Java installation needed!
- For unsupported platforms, falls back to platform-independent version ( requires Java 21+)

**Supported platforms with bundled Java:**
- ✅ Windows x64
- ✅ macOS x64 (Intel)
- ✅ macOS ARM64 (Apple Silicon)
- ✅ Linux x64
- ✅ Linux ARM64

Note: Currently LSP ignores non-workspace files. Add the folder to Sublime Text to enable the Server.

## Known Issues

- **Windows Process Termination**: On Windows, the `ltex-ls-plus.bat` script may sometimes fail to terminate the Java process when Sublime Text closes. If you experience this, or if you want more control over the JVM, you can configure the `command` directly in your settings to bypass the batch script:

  ```json
  "command": [
      "path/to/java.exe", // e.g. C:\\Program Files\\Java\\jdk-21\\bin\\java.exe

      "-Xrs",
      "-Xms64m",
      "-Xmx2G",
      "-Xlog:disable", // Important: Disable stdout logging to prevent breaking LSP

      "-Dapp.name=ltex-ls-plus",
      "-Dapp.home=${serverdir}",
      "-Dbasedir=${serverdir}",

      "-cp",
      "${serverdir}/lib/*",

      "org.bsplines.ltexls.LtexLanguageServerLauncher"
  ],
  ```


## Available Commands

Access these commands via Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`):

### LTeX: Clear Diagnostics
Clears all grammar and spelling errors from the current view. Useful when you want to temporarily hide diagnostics while focusing on content.

### LTeX: Show Status
Displays a dialog with plugin information:
- Server version and installation status
- Server installation path
- Active language setting
- External files configuration status

Helpful for troubleshooting and verifying your configuration.

### LTeX: Restart Server
Forces a restart of the LTeX language server. Use this when:
- Applying settings changes that require a restart
- Recovering from server errors
- Refreshing after manual dictionary file edits


## Magic Comments

You can control LTeX settings directly in your document using magic comments. This is useful for per-document configuration without changing global settings.

### Basic Usage

```latex
% LTeX: language=de-DE
% LTeX: enabled=false

Your text here...

% LTeX: enabled=true
```

### Common Examples

**Change language for a section:**
```latex
% LTeX: language=ru-RU
\section{Введение}
Текст на русском языке.

% LTeX: language=en-US
\section{Introduction}
Text in English.
```

**Disable specific rules:**
```latex
% LTeX: disabledRules=en-US:UPPERCASE_SENTENCE_START,EN_QUOTES
```

**Add words to dictionary:**
```latex
% LTeX: dictionary=en-US:LTeX,Markdown,reStructuredText
```

**Disable checking for code blocks:**
```latex
% LTeX: enabled=false
\begin{lstlisting}
  code here
\end{lstlisting}
% LTeX: enabled=true
```

📖 **Full documentation:** [Magic Comments Guide](https://ltex-plus.github.io/ltex-plus/advanced-usage.html#magic-comments)


## Settings Reference

All LTeX settings are available in `Preferences > Package Settings > LSP > Servers > LSP-ltex-plus > Settings`.

### Key Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `ltex.language` | Default language for grammar checking | `"en-US"` |
| `ltex.dictionary` | Custom words to ignore | `{}` |
| `ltex.disabledRules` | Rules to disable | `{}` |
| `ltex.enabledRules` | Rules to enable (if disabled by default) | `{}` |
| `ltex.additionalRules.enablePickyRules` | Enable strict rules (passive voice, etc.) | `false` |
| `ltex.checkFrequency` | When to check: `"edit"` or `"save"` | `"edit"` |
| `ltex.completionEnabled` | Enable word completion | `false` |

### Example Configuration

```json
{
  "settings": {
    "ltex.language": "en-US",
    "ltex.dictionary": {
      "en-US": ["LaTeX", "Markdown", "reStructuredText"]
    },
    "ltex.additionalRules.enablePickyRules": true,
    "ltex.checkFrequency": "save"
  }
}
```

### Project-Specific Settings

From the command palette run `Project: Edit Project` and add:

```js
{
   "settings": {
      "LSP": {
         "ltex-plus": {
            "settings": {
               // Put your settings here
            }
         }
      }
   }
}
```

📖 **Full settings list:** [LTeX Settings Documentation](https://ltex-plus.github.io/ltex-plus/settings.html)


## External Dictionary Files

Instead of storing dictionaries in settings (which requires server restart when modified), you can use external files.

### How to Enable

```json
{
  "use_external_dictionary_files": true,
  "use_external_hidden_false_positives_files": true,
  "use_external_disabled_rules_files": true
}
```

### Benefits

✅ **No server restart needed** - add words without restarting  
✅ **Cleaner settings** - keeps `.sublime-settings` file small  
✅ **Easy to share** - commit external files to Git for team use

### File Locations

**Default locations:**
- Dictionaries: `.../Packages/User/LSP-ltex-plus/dictionaries/{lang}.txt`
- Hidden False Positives: `.../Packages/User/LSP-ltex-plus/hidden_false_positives/hiddenFalsePositives.{lang}.txt`
- Disabled Rules: `.../Packages/User/LSP-ltex-plus/disabled_rules/disabledRules.{lang}.txt`

**Custom locations:**
```json
{
  "use_external_dictionary_files": true,
  "external_dictionary_dir": "~/Dropbox/ltex/dictionaries"
}
```

**Format:** One entry per line (plain text)


## Troubleshooting

### Server Won't Start

**Symptom:** No grammar checking, no errors shown.

**Solutions:**
1. **With bundled Java (v1.2.0+):** Should work automatically on supported platforms
   - Windows x64, macOS x64/ARM64, Linux x64/ARM64
2. **Without bundled Java:** Install Java 21+ and ensure it's in PATH or set `JAVA_HOME`
3. Check console (`View > Show Console`) for error messages

### No Errors/Warnings Shown

**Symptom:** File is open but no grammar checks appear.

**Solutions:**
1. **Add folder to workspace:** LSP requires files to be in a workspace
   - `Project > Add Folder to Project...`
2. **Check file type:** Ensure language is supported (LaTeX, Markdown, etc.)
3. **Run `LTeX: Show Status`** to check configuration

### Download Fails

**Symptom:** Server download times out or fails.

**Solutions:**
1. Check internet connection and proxy settings
2. Manual download from [GitHub Releases](https://github.com/ltex-plus/ltex-ls-plus/releases)
   - Extract to `~/.../Package Storage/LSP-ltex-plus/ltex-ls-plus-{version}/`

### Performance Issues

**Symptom:** Sublime Text slows down during checking.

**Solutions:**
1. Increase Java heap size:
   ```json
   "env": {
     "JAVA_OPTS": "-Xms128m -Xmx4G"
   }
   ```
2. Change check frequency to `"save"` instead of `"edit"`
3. Disable picky rules: `"ltex.additionalRules.enablePickyRules": false`

### Find Server Logs

- **Windows:** `%TEMP%` → search for `ltex-ls` files
- **macOS/Linux:** `/tmp/` → search for `ltex-ls` files


## Credits

*   Based on [LSP-ltex-ls](https://github.com/sublimelsp/LSP-ltex-ls).
*   Powered by [ltex-plus](https://github.com/ltex-plus/ltex-ls-plus).
