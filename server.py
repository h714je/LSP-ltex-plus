import os
import platform
import shutil
import tarfile
import zipfile
import tempfile
import urllib.request
import urllib.error
import sublime
from typing import Optional

# Constants
GITHUB_DL_URL: str = "https://github.com/ltex-plus/ltex-ls-plus/releases/download/{0}/ltex-ls-plus-{0}{1}"
SERVER_FOLDER_NAME: str = "ltex-ls-plus-{}"
LATEST_TESTED_RELEASE: str = "18.6.1"
STORAGE_FOLDER_NAME: str = "LSP-ltex-plus"
SETTINGS_FILENAME: str = "LSP-ltex-plus.sublime-settings"


class LTeXPlusServer:
    """
    Manages LTeX Plus language server installation and updates.
    
    This class handles:
    - Platform detection for bundled Java downloads
    - Server download with progress tracking
    - Archive extraction (ZIP and TAR.GZ)
    - Server version management
    """
    
    @classmethod
    def storage_path(cls) -> str:
        """
        Get the Package Storage directory path.
        
        Returns:
            Absolute path to Sublime Text's Package Storage directory.
        """
        return os.path.join(sublime.cache_path(), "..", "Package Storage")

    @classmethod
    def basedir(cls) -> str:
        """
        Get this plugin's directory in Package Storage.
        
        Returns:
            Absolute path to LSP-ltex-plus storage directory.
            Example: ~/.../Package Storage/LSP-ltex-plus/
        """
        return os.path.join(cls.storage_path(), STORAGE_FOLDER_NAME)

    @classmethod
    def serverversion(cls) -> str:
        """
        Get the LTeX server version to use.
        
        Checks user settings for custom version, falls back to tested default.
        
        Returns:
            Version string (e.g., "18.6.1").
        """
        settings = sublime.load_settings(SETTINGS_FILENAME)
        version: Optional[str] = settings.get("version")
        if version:
            return version
        
        return LATEST_TESTED_RELEASE

    @classmethod
    def serverdir(cls) -> str:
        """
        Get the server installation directory.
        
        Returns:
            Absolute path to server directory containing bin/ and lib/ folders.
            Example: ~/.../Package Storage/LSP-ltex-plus/ltex-ls-plus-18.6.1/
        """
        return os.path.join(
            cls.basedir(), SERVER_FOLDER_NAME.format(cls.serverversion())
        )

    @classmethod
    def _detect_platform_suffix(cls) -> str:
        """
        Detect platform and architecture for bundled Java download.
        
        Performs robust platform detection with fallback to platform-independent
        version for unsupported systems.
        
        Supported platforms:
            - Windows x64
            - macOS x64 (Intel)
            - macOS ARM64 (Apple Silicon)
            - Linux x64
            - Linux ARM64
        
        Returns:
            Archive suffix string:
                - '-windows-x64.zip' for Windows
                - '-mac-x64.tar.gz' or '-mac-arm64.tar.gz' for macOS
                - '-linux-x64.tar.gz' or '-linux-arm64.tar.gz' for Linux
                - '.tar.gz' for unsupported platforms (requires Java 21+)
        
        Note:
            Logs detection results to console for debugging.
        """
        system: str = platform.system().lower()
        machine: str = platform.machine().lower()
        
        print(f"LSP-ltex-plus: Detected OS: {system}, Architecture: {machine}")
        
        # Normalize architecture names - be generous with variants
        arch: Optional[str] = None
        
        if machine in ('amd64', 'x86_64', 'x64', 'em64t'):
            arch = 'x64'
        elif machine in ('arm64', 'aarch64', 'armv8', 'arm64e'):
            arch = 'arm64'
        elif machine in ('i386', 'i686', 'x86', 'i86pc'):
            # 32-bit x86 - not supported by ltex-ls-plus, fallback
            print(f"LSP-ltex-plus: 32-bit architecture '{machine}' not supported, using platform-independent version")
            return '.tar.gz'
        elif machine.startswith('arm') or machine.startswith('aarch'):
            # Other ARM variants (armv7l, etc.) - try to determine if 64-bit
            if '64' in machine or machine in ('aarch64',):
                arch = 'arm64'
            else:
                print(f"LSP-ltex-plus: 32-bit ARM '{machine}' not supported, using platform-independent version")
                return '.tar.gz'
        else:
            # Unknown architecture, fallback
            print(f"LSP-ltex-plus: Unknown architecture '{machine}', using platform-independent version")
            return '.tar.gz'
        
        # Map to ltex-ls-plus archive names
        if system in ('windows', 'win32', 'cygwin'):
            return f'-windows-{arch}.zip'
        elif system in ('darwin', 'macos'):  # macOS
            return f'-mac-{arch}.tar.gz'
        elif system in ('linux', 'linux2'):
            return f'-linux-{arch}.tar.gz'
        else:
            # Unknown OS (FreeBSD, OpenBSD, etc.), fallback
            print(f"LSP-ltex-plus: Unknown OS '{system}', using platform-independent version")
            return '.tar.gz'

    @classmethod
    def needs_update_or_installation(cls) -> bool:
        """
        Check if server needs to be installed or updated.
        
        Returns:
            True if server directory doesn't exist, False otherwise.
        """
        return not os.path.isdir(cls.serverdir())

    @classmethod
    def install_or_update(cls) -> None:
        """
        Download and install the LTeX Plus language server.
        
        This method:
        1. Detects platform and determines appropriate download
        2. Downloads server archive with progress tracking
        3. Extracts archive (supports ZIP and TAR.GZ)
        4. Moves server to final installation directory
        
        The installation is atomic - if any step fails, an error message
        is displayed and the method returns early.
        
        Side effects:
            - Creates directories in Package Storage
            - Downloads ~200MB archive from GitHub
            - Displays progress messages in status bar
            - Shows error dialogs on failure
        
        Note:
            For bundled Java versions, no separate Java installation needed.
            For platform-independent version, Java 21+ must be installed.
        """
        version: str = cls.serverversion()
        if not version:
            return

        basedir: str = cls.basedir()
        if os.path.isdir(basedir):
            shutil.rmtree(basedir)
        os.makedirs(basedir)

        with tempfile.TemporaryDirectory() as tempdir:
            # Detect platform and determine archive format
            suffix: str = cls._detect_platform_suffix()
            is_zip: bool = suffix.endswith('.zip')
            archive_ext: str = 'zip' if is_zip else 'tar.gz'
            archive_path: str = os.path.join(tempdir, f"server.{archive_ext}")
            
            download_url: str = GITHUB_DL_URL.format(version, suffix)
            print(f"LSP-ltex-plus: downloading from {download_url}")
            print(f"LSP-ltex-plus: detected platform suffix: {suffix}")
            
            # Progress tracking callback
            def download_progress(block_num: int, block_size: int, total_size: int) -> None:
                """
                Display download progress with percentage and file size.
                
                Args:
                    block_num: Number of blocks downloaded
                    block_size: Size of each block in bytes
                    total_size: Total file size in bytes
                """
                downloaded: int = block_num * block_size
                if total_size > 0:
                    percent: int = min(100, int(downloaded * 100 / total_size))
                    downloaded_mb: float = downloaded / (1024 * 1024)
                    total_mb: float = total_size / (1024 * 1024)
                    sublime.status_message(
                        f"LSP-ltex-plus: downloading server... {percent}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)"
                    )
                else:
                    downloaded_mb: float = downloaded / (1024 * 1024)
                    sublime.status_message(
                        f"LSP-ltex-plus: downloading server... ({downloaded_mb:.1f} MB)"
                    )
            
            try:
                urllib.request.urlretrieve(download_url, archive_path, reporthook=download_progress)
                sublime.status_message("LSP-ltex-plus: download complete!")
            except urllib.error.URLError as e:
                sublime.error_message(f"LSP-ltex-plus: Error downloading server: {e}")
                return

            sublime.status_message("LSP-ltex-plus: extracting server...")
            
            try:
                if is_zip:
                    with zipfile.ZipFile(archive_path, 'r') as archive:
                        archive.extractall(tempdir)
                else:
                    with tarfile.open(archive_path, "r:gz") as archive:
                        archive.extractall(tempdir)
            except (zipfile.BadZipFile, tarfile.TarError) as e:
                sublime.error_message(f"LSP-ltex-plus: Error extracting server: {e}")
                return

            # Move extracted server to final location
            extracted_folder_name: str = SERVER_FOLDER_NAME.format(version)
            src_path: str = os.path.join(tempdir, extracted_folder_name)
            dst_path: str = basedir
            
            shutil.move(src_path, dst_path)
            
            sublime.status_message(f"LSP-ltex-plus: installed server version {version}")

