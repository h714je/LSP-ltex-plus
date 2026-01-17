import os
import re
import copy
from pathlib import Path
from threading import Lock
import sublime
from typing import NamedTuple
from LSP.plugin.core.typing import Any, Dict, List, Set, Optional

SETTINGS_FILENAME = "LSP-ltex-plus.sublime-settings"


class SettingScope(NamedTuple):
    # The key expected/sent by the server (e.g., "ltex.dictionary")
    server_key: str
    # Keys in the user's settings that map to this scope (e.g., ["dictionary", "ltex.dictionary"])
    expand_keys: List[str]
    # The setting key to enable external files for this scope
    enable_key: str
    # The setting key for the directory path
    dir_key: str
    # Default subdirectory name if dir_key is not set
    default_subdir: str
    # Format string for the filename, e.g. "{lang}.txt" or "prefix.{lang}.txt"
    file_template: str


_SCOPES = [
    SettingScope(
        server_key="ltex.dictionary",
        expand_keys=["ltex.dictionary", "dictionary"],
        enable_key="use_external_dictionary_files",
        dir_key="external_dictionary_dir",
        default_subdir="dictionaries",
        file_template="{lang}.txt"
    ),
    SettingScope(
        server_key="ltex.hiddenFalsePositives",
        expand_keys=["ltex.hiddenFalsePositives", "hiddenFalsePositives"],
        enable_key="use_external_hidden_false_positives_files",
        dir_key="external_hidden_false_positives_dir",
        default_subdir="hidden_false_positives",
        file_template="hiddenFalsePositives.{lang}.txt"
    ),
    SettingScope(
        server_key="ltex.disabledRules",
        expand_keys=["ltex.disabledRules", "disabledRules"],
        enable_key="use_external_disabled_rules_files",
        dir_key="external_disabled_rules_dir",
        default_subdir="disabled_rules",
        file_template="disabledRules.{lang}.txt"
    ),
]


class SettingsManager:
    """
    Manages reading and writing of LSP-ltex-plus settings, 
    including handling of external dictionary files.
    """
    _lock = Lock()
    # Cache: path_str -> {"mtime": float, "words": Set[str]}
    _cache: Dict[str, Dict[str, Any]] = {}
    _lang_sanitize_re = re.compile(r"[^A-Za-z0-9._-]+")

    @classmethod
    def expand_settings(cls, server_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expands settings before sending to the server.
        Specifically, replaces dictionary file paths (starting with :) with the actual list of words.
        """
        # We don't necessarily need to load sublime settings here unless checking enables,
        # but the original logic didn't check enables for expansion, only for writing.
        # We just expand if we find the key.
        
        expanded = copy.deepcopy(server_settings)
        
        for scope in _SCOPES:
            # Find which key is present in the settings (prioritize server_key, then aliases)
            target_key = None
            if scope.server_key in expanded:
                target_key = scope.server_key
            else:
                for alias in scope.expand_keys:
                    if alias in expanded:
                        target_key = alias
                        break
            
            if not target_key:
                continue

            dict_cfg = cls._as_dict(expanded[target_key])
            
            for lang, items_any in dict_cfg.items():
                items = cls._as_list(items_any)
                # Check if it's a marker like [":/path/to/file.txt"]
                if len(items) == 1 and isinstance(items[0], str) and items[0].startswith(":"):
                    file_path_str = items[0][1:]
                    path = Path(file_path_str)
                    words_set = cls._ensure_cache_loaded(path)
                    dict_cfg[lang] = sorted(words_set)
            
            expanded[target_key] = dict_cfg

        return expanded

    @classmethod
    def update_from_code_action(cls, server_setting_key: str, value: Dict[str, Any]) -> bool:
        """
        Updates settings based on a code action from the server.
        Returns True if a manual configuration update notification is needed.
        """
        settings = sublime.load_settings(SETTINGS_FILENAME)
        
        # Find matching scope
        scope = next((s for s in _SCOPES if s.server_key == server_setting_key), None)

        if scope and cls._external_enabled(settings, scope):
            return cls._update_dictionary_external(settings, scope, value)

        # For normal settings (or if external dict is disabled), write directly to config.
        # LSP will handle the update/restart.
        cls._update_settings_plain(settings, server_setting_key, value)
        return False

    # --- Private Methods ---

    @classmethod
    def _update_dictionary_external(cls, settings: sublime.Settings, scope: SettingScope, value: Dict[str, Any]) -> bool:
        """
        Handles dictionary updates when external files are enabled.
        Returns True if manual update needed.
        """
        old_server_settings = cls._as_dict(settings.get("settings"))
        server_settings = dict(old_server_settings)

        # We always use the primary server_key for the internal settings storage to be consistent
        key = scope.server_key
        dict_cfg_any = cls._as_dict(server_settings.get(key))
        dict_cfg = dict(dict_cfg_any)

        changed_settings = False
        words_added_to_file = False

        for lang, items_any in cls._as_dict(value).items():
            lang_key = str(lang)
            incoming = [x for x in cls._as_list(items_any) if isinstance(x, str) and x]
            if not incoming:
                continue

            dict_path = cls._get_active_dict_path(settings, scope, lang_key)

            # Write new words to file
            added = cls._append_words_to_file(dict_path, incoming)
            if added:
                words_added_to_file = True

            # Check if we need to migrate existing settings-based words to file
            existing_list = [x for x in cls._as_list(dict_cfg.get(lang_key)) if isinstance(x, str) and x]
            embedded_words = [x for x in existing_list if not cls._is_external_marker(x)]
            
            if embedded_words:
                cls._append_words_to_file(dict_path, embedded_words)

            # Ensure setting points to the file marker
            marker = cls._create_marker(dict_path)
            if existing_list != [marker]:
                dict_cfg[lang_key] = [marker]
                changed_settings = True

        if changed_settings:
            server_settings[key] = dict_cfg
            cls._persist_settings(settings, server_settings)
            return False # LSP handles restart/update

        return words_added_to_file

    @classmethod
    def _update_settings_plain(cls, settings: sublime.Settings, key: str, value: Dict[str, Any]) -> None:
        old_server_settings = cls._as_dict(settings.get("settings"))
        server_settings = dict(old_server_settings)

        old_target_dict = cls._as_dict(server_settings.get(key))
        target_dict = dict(old_target_dict)

        changed = False

        for lang, items_any in cls._as_dict(value).items():
            lang_key = str(lang)
            existing = [x for x in cls._as_list(target_dict.get(lang_key)) if isinstance(x, str) and x]
            incoming = [x for x in cls._as_list(items_any) if isinstance(x, str) and x]

            merged = cls._merge_lists(existing, incoming)
            if merged != existing:
                target_dict[lang_key] = merged
                changed = True

        if changed:
            server_settings[key] = target_dict
            cls._persist_settings(settings, server_settings)

    @staticmethod
    def _persist_settings(settings: sublime.Settings, server_settings: Dict[str, Any]) -> None:
        settings.set("settings", server_settings)
        sublime.save_settings(SETTINGS_FILENAME)

    @classmethod
    def _get_active_dict_path(cls, settings: sublime.Settings, scope: SettingScope, lang: str) -> Path:
        base_dir = cls._get_external_dir(settings, scope)
        safe_lang = cls._lang_sanitize_re.sub("_", lang.strip()) or "unknown"
        filename = scope.file_template.format(lang=safe_lang)
        return base_dir / filename

    @classmethod
    def _get_external_dir(cls, settings: sublime.Settings, scope: SettingScope) -> Path:
        raw = settings.get(scope.dir_key)
        if isinstance(raw, str) and raw.strip():
            p = Path(os.path.expanduser(os.path.expandvars(raw.strip())))
            if not p.is_absolute():
                p = Path(sublime.packages_path(), "User", p)
            return p
        return Path(sublime.packages_path(), "User", "LSP-ltex-plus", scope.default_subdir)
        
    @classmethod
    def _append_words_to_file(cls, path: Path, words: List[str]) -> List[str]:
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with cls._lock:
            existing_set = cls._ensure_cache_loaded(path)
            added = []
            
            for w in words:
                w = w.strip()
                if not w or w.startswith("#") or w in existing_set:
                    continue
                existing_set.add(w)
                added.append(w)
            
            if not added:
                return []

            try:
                with path.open("a", encoding="utf-8", newline="\n") as f:
                    for w in added:
                        f.write(w)
                        f.write("\n")
                
                # Update mtime in cache to avoid re-reading our own write
                if path.exists():
                     cls._cache[str(path)]["mtime"] = path.stat().st_mtime
            except Exception:
                pass # logging?

            return added

    @classmethod
    def _ensure_cache_loaded(cls, path: Path) -> Set[str]:
        path_str = str(path)
        current_mtime = path.stat().st_mtime if path.exists() else -1.0

        entry = cls._cache.get(path_str)
        if entry and entry["mtime"] == current_mtime:
            return entry["words"]

        words = set()
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
                for line in content.splitlines():
                    w = line.strip()
                    if w and not w.startswith("#"):
                        words.add(w)
            except Exception:
                pass

        cls._cache[path_str] = {"mtime": current_mtime, "words": words}
        return words

    @staticmethod
    def _merge_lists(existing: List[str], incoming: List[str]) -> List[str]:
        out = list(existing)
        seen = set(existing)
        for item in incoming:
            if item not in seen:
                out.append(item)
                seen.add(item)
        return out

    # --- Helpers ---
    @staticmethod
    def _as_dict(val: Any) -> Dict[str, Any]:
        return val if isinstance(val, dict) else {}

    @staticmethod
    def _as_list(val: Any) -> List[Any]:
        return val if isinstance(val, list) else []

    @staticmethod
    def _is_external_marker(val: str) -> bool:
        return isinstance(val, str) and val.startswith(":") and len(val) > 1

    @staticmethod
    def _create_marker(path: Path) -> str:
        return ":" + str(path)

    @staticmethod
    def _external_enabled(settings: sublime.Settings, scope: SettingScope) -> bool:
        return bool(settings.get(scope.enable_key))