import os
import platform
import shutil
import tarfile
import zipfile
import tempfile
import urllib.request
import urllib.error
import sublime

# Constants
GITHUB_DL_URL = "https://github.com/ltex-plus/ltex-ls-plus/releases/download/{0}/ltex-ls-plus-{0}{1}"
SERVER_FOLDER_NAME = "ltex-ls-plus-{}"
LATEST_TESTED_RELEASE = "18.6.1"
STORAGE_FOLDER_NAME = "LSP-ltex-plus"
SETTINGS_FILENAME = "LSP-ltex-plus.sublime-settings"

class LTeXPlusServer:
    @classmethod
    def storage_path(cls) -> str:
        return os.path.join(sublime.cache_path(), "..", "Package Storage")

    @classmethod
    def basedir(cls) -> str:
        """
        The directory of this plugin in Package Storage.
        """
        return os.path.join(cls.storage_path(), STORAGE_FOLDER_NAME)

    @classmethod
    def serverversion(cls) -> str:
        """
        Returns the version of ltex-ls to use.
        """
        settings = sublime.load_settings(SETTINGS_FILENAME)
        version = settings.get("version")
        if version:
            return version
        
        return LATEST_TESTED_RELEASE

    @classmethod
    def serverdir(cls) -> str:
        """
        The directory of the server. In here are the "bin" and "lib" folders.
        """
        return os.path.join(
            cls.basedir(), SERVER_FOLDER_NAME.format(cls.serverversion())
        )

    @classmethod
    def _detect_platform_suffix(cls) -> str:
        """
        Detect platform and architecture to download the appropriate bundled version.
        Returns suffix like '-windows-x64.zip' or '-linux-x64.tar.gz'.
        Falls back to '.tar.gz' (platform-independent, no bundled Java) if detection fails.
        """
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        print(f"LSP-ltex-plus: Detected OS: {system}, Architecture: {machine}")
        
        # Normalize architecture names - be generous with variants
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
        return not os.path.isdir(cls.serverdir())

    @classmethod
    def install_or_update(cls) -> None:
        version = cls.serverversion()
        if not version:
            return

        basedir = cls.basedir()
        if os.path.isdir(basedir):
            shutil.rmtree(basedir)
        os.makedirs(basedir)

        with tempfile.TemporaryDirectory() as tempdir:
            # Detect platform and determine archive format
            suffix = cls._detect_platform_suffix()
            is_zip = suffix.endswith('.zip')
            archive_ext = 'zip' if is_zip else 'tar.gz'
            archive_path = os.path.join(tempdir, f"server.{archive_ext}")
            
            download_url = GITHUB_DL_URL.format(version, suffix)
            print(f"LSP-ltex-plus: downloading from {download_url}")
            print(f"LSP-ltex-plus: detected platform suffix: {suffix}")
            
            # Progress tracking
            def download_progress(block_num, block_size, total_size):
                """Display download progress with percentage and size."""
                downloaded = block_num * block_size
                if total_size > 0:
                    percent = min(100, int(downloaded * 100 / total_size))
                    downloaded_mb = downloaded / (1024 * 1024)
                    total_mb = total_size / (1024 * 1024)
                    sublime.status_message(
                        f"LSP-ltex-plus: downloading server... {percent}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)"
                    )
                else:
                    downloaded_mb = downloaded / (1024 * 1024)
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

            # The extracted folder usually looks like "ltex-ls-plus-18.6.1"
            extracted_folder_name = SERVER_FOLDER_NAME.format(version)
            src_path = os.path.join(tempdir, extracted_folder_name)
            dst_path = basedir
            
            # Move contents to basedir so structure is .../LSP-ltex-plus/ltex-ls-plus-18.6.1/
            # wait, LTeX-ls logic moves it to basedir/SERVER_FOLDER_NAME ?
            # Let's check typical structure. default basedir is .../LSP-ltex-plus.
            # We want .../LSP-ltex-plus/ltex-ls-plus-18.6.1
            
            shutil.move(src_path, dst_path)
            
            sublime.status_message(f"LSP-ltex-plus: installed server version {version}")
