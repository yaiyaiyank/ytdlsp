とあるbatファイルを生成するプログラム。
denoとかfirefoxは必須です。

# Install
## リポジトリをダウンロード
ダウンロードしたいディレクトリで
```
git clone https://github.com/yaiyaiyank/ytdlsp
cd ytdlsp
```
ytdlspフォルダ内で仮想環境ダウンロード
```
uv sync
```
```
uv lock --upgrade
```
## denoをダウンロード(Windows版)
```
winget install DenoLand.Deno
```

# Usage
ipynbで調整しながら
```python
from ytdlsp.make_bat import make_bat
# チャンネルURL
url = "https://www.youtube.com/@SPOLAVA"
# チャンネル
folder = r"I:\yt_dl\storage\スポーツ系"
make_bat(url, folder, timeout=4000)
```

# Tips
- firefoxのCookieで使ってるアカウントでyt-dlp使用時、そのアカウントで動画を見てるとたまに「他デバイスで～」みたいなのが出て動画が見れないことがある。メンシプ動画など、普段使いのアカウントで使いたい場合はしかたかない。寝る前や登校・出勤前にYouTubeを使わない時間に合わせてtimeoutを設定して実行しよう(提案)。

# F u t u r e
- ffmpegでAV1コーデックに変換して保存するやつ実装するかも。ただ、ロジックはおそらくこのリポジトリではなく、動画編集モジュールみたいなの開発して使う予定。ffmpegだけで動画編集やってみたいのです。
    ```python
    from ytdlsp.make_bat import make_bat
    # チャンネルURL
    url = "https://www.youtube.com/@akito2922"
    # チャンネル
    folder = r"I:\yt_dl\storage\勉強系"
    make_bat(url, folder, timeout=4000, codec="AV1")
    ```
    的なやつ。
- ffprobeで動画が破損していたら再dlする機能などもつけるかも。