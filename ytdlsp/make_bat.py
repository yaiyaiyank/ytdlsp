import json
import re
import subprocess
from path_utils_module import (
    Path,
    validation_path,
    validation_path_list,
    USER_DOWNLOAD_FOLDER_PATH,
    sanitize_windows_path_name,
)
from urllib.parse import urlparse

BASE_YTDLP_COMMAND = [
    "yt-dlp",
    "--cookies-from-browser",
    "firefox",
    "--remote-components",
    "ejs:npm",
]
DL_SAMUNE_COMMAND = BASE_YTDLP_COMMAND + ["-a", "urls.txt", "--skip-download", "--paths", "samune", "--write-thumbnail"]
DL_VIDEO_COMMAND = BASE_YTDLP_COMMAND + ["-a", "urls.txt"]


class Channnel:
    def __init__(self, url: str):
        self.validation_channel_url(url)
        url = self.normalize_channel_url(url)
        self.url = url

    def set_handle(self, first_data: dict):
        # 入力URLが @handle ならそれを優先
        handle = self.get_handle_from_url(self.url)

        if handle is None:
            handle = self.find_handle(first_data)

        self.handle = handle

    def get_canonical_channel_url(self) -> str:
        if self.handle is not None:
            canonical_channel_url = f"https://www.youtube.com/{self.handle}"
        else:
            # /channel/UCxxxx のようなURLの場合のフォールバック
            raise ValueError("handleの取得ができませんでした。")

        return canonical_channel_url

    @staticmethod
    def validation_channel_url(url: str):
        if "/channel/" in url or "/@" in url:
            return
        raise ValueError("チャンネルURLじゃあないです。")

    @staticmethod
    def normalize_channel_url(url: str) -> str:
        """
        URL末尾の /videos, /shorts, /streams などを除去して
        チャンネルのベースURLにする。
        """
        url = url.strip().rstrip("/")

        for suffix in ("/videos", "/shorts", "/streams", "/featured"):
            url = url.removesuffix(suffix)
        return url

    @staticmethod
    def get_handle_from_url(url: str) -> str | None:
        """@handle形式のURLならハンドルを取得する。"""
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]

        for part in parts:
            if part.startswith("@"):
                return part

        return None

    def get_tab_info(self, tab_url: str) -> dict | None:
        """
        yt-dlpでタブを調べる。
        動画が存在すればJSONを返し、存在しなければNone。
        """
        command = BASE_YTDLP_COMMAND + [
            "--flat-playlist",
            "--playlist-end",
            "1",
            "--dump-single-json",
            "--no-warnings",
            tab_url,
        ]

        result = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
        )

        if result.returncode != 0:
            return None

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

        entries = data.get("entries") or []

        if not entries:
            return None

        return data

    def find_channel_name(self, data: dict) -> str | None:
        """yt-dlpのJSONからチャンネル名を探す。"""
        candidates = [
            data.get("channel"),
            data.get("uploader"),
            data.get("playlist_channel"),
        ]

        entries = data.get("entries") or []
        if entries:
            entry = entries[0]

            candidates.extend(
                [
                    entry.get("channel"),
                    entry.get("uploader"),
                ]
            )

        for value in candidates:
            if value:
                return value

        # playlist titleが「チャンネル名 - Videos」等なら末尾を削る
        title = data.get("title")
        if title:
            title = re.sub(
                r"\s*-\s*(Videos|Shorts|Live|Streams)$",
                "",
                title,
                flags=re.IGNORECASE,
            )
            return title

        return None

    def find_handle(self, data: dict) -> str | None:
        """yt-dlpのJSON内から @handle を探す。"""
        keys = (
            "uploader_id",
            "channel_url",
            "uploader_url",
        )

        objects = [data]

        entries = data.get("entries") or []
        if entries:
            objects.append(entries[0])

        for obj in objects:
            for key in keys:
                value = obj.get(key)

                if not isinstance(value, str):
                    continue

                # uploader_id = @example
                if value.startswith("@"):
                    return value

                # URL内の @example
                handle = self.get_handle_from_url(value)
                if handle:
                    return handle

        return None


def make_bat(url: str, root_folder: Path | str, timeout: int = 1000):
    root_folder = validation_path(root_folder, parents_mkdir=True)

    TAB_INFO = ["videos", "shorts", "streams"]
    channel = Channnel(url)

    print()
    print("チャンネルを確認しています...")

    found_tabs: dict[str, dict] = {}

    for tab_name in TAB_INFO:
        tab_url = f"{channel.url}/{tab_name}"

        print(f"確認中: {tab_name}")

        data = channel.get_tab_info(tab_url)

        if data is not None:
            found_tabs[tab_name] = data
            print("  -> あり")
        else:
            print("  -> なし")

    if not found_tabs:
        print()
        print("動画・ショート・ライブが見つかりませんでした。")
        return

    # 最初に見つかったタブからチャンネル情報を取得
    first_data = next(iter(found_tabs.values()))

    channel.set_handle(first_data)

    # "http s://www.youtube.com/@ハンドル"
    canonical_channel_url = channel.get_canonical_channel_url()

    channel_name = channel.find_channel_name(first_data)

    if channel_name is None:
        raise RuntimeError("チャンネル名を取得できませんでした。")

    channel_name = sanitize_windows_path_name(channel_name)

    print()
    print(f"チャンネル名: {channel_name}")
    print(f"チャンネルハンドル: {channel.handle}")
    print(canonical_channel_url)

    for category in found_tabs:
        category_url = f"{canonical_channel_url}/{category}"
        category_folder = root_folder / channel_name / category
        create_category_bat_file(category_folder, category_url, timeout)


def create_category_bat_file(category_folder: Path | str, category_url: str, timeout: int):
    category_folder = validation_path(category_folder, parents_mkdir=True)
    category_folder.mkdir(parents=True, exist_ok=True)
    dl_samune_command = " ".join(DL_SAMUNE_COMMAND)
    dl_video_command = " ".join(DL_VIDEO_COMMAND)
    timeout_command = f"timeout {timeout}"
    # URL入力用テキストファイルを書き込み
    url_text_path = category_folder / "urls.txt"
    url_text_path.write_text(f"{category_url}{'\n' * 10}")
    # サムネ保存batファイルを書き込み
    dl_samune_bat_path = category_folder / "dl_samune.bat"
    dl_samune_bat_path.write_text(f"{timeout_command}\n{dl_samune_command}\n{timeout_command}")
    # 動画保存batファイルを書き込み
    dl_video_bat_path = category_folder / "dl_video.bat"
    dl_video_bat_path.write_text(f"{timeout_command}\n{dl_video_command}\n{timeout_command}")
    # サムネ+動画保存batファイルを書き込み
    dl_video_samune_bat_path = category_folder / "dl_video_samune.bat"
    dl_video_samune_bat_path.write_text(
        f"{timeout_command}\n{dl_samune_command}\n{dl_video_command}\n{timeout_command}"
    )


def create_text_file(path: Path | str, text: str | list[str]):
    """.txt, .batなどのテキストファイルを作成。"""
    path = validation_path(path, parents_mkdir=True)

    if isinstance(text, str):
        text = [text]
    text = "\n".join(text)
    # テキストを書き込む
    path.write_text(text)
