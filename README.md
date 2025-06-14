# FFmpeg Video Converter Script

A flexible and efficient command-line script designed for pre-processing video files for smooth **Direct Play** on devices like Samsung Smart TVs that lack support for legacy codecs.

### 🎯 Why This Script Exists

I run a Plex media server on low-powered hardware where real-time transcoding of high-resolution video is problematic and causes stuttering. To enable smooth Direct Play to my Samsung TV, I use this script to pre-convert incompatible formats ahead of time. My TV, for example, doesn't support older codecs like `MPEG4-XVID` or advanced audio formats such as `DTS` or `TRUEHD`, which are common in older or Blu-ray sourced content.

This script solves that by automatically converting only the necessary streams, resulting in files that play instantly and reliably.

---

## 📌 Features

- ✅ Convert an entire folder (recursively) or a single video file
- ✅ Converts video streams to H.265 (libx265) or any configured encoder with CRF control
- ✅ Converts DTS, TrueHD audio to EAC3 (default) or another user-defined codec
- ✅ Automatically processes subtitle files (.srt), including Windows-1250 to UTF-8 conversion
- ✅ Supports copying multiple streams when needed (via config flag)
- ✅ Multithreaded encoding using all available CPU cores (up to 16)
- ✅ Smart codec detection and selective conversion
- ✅ Dry-run mode to preview actions without executing
- ✅ Convert subtitles only, recursively across directories

---

## 🔧 Configuration Highlights (in-script)

```python
FORCE_CONVERSION_VIDEO_CODECS = ["MPEG4-XVID"]
FORCE_CONVERSION_AUDIO_CODECS = ["DTS", "TRUEHD"]
CRF = "20"  # lower = higher quality (range: 18–28)
OUTPUT_VIDEO_CODEC = "libx265"  # Can be changed to any ffmpeg-supported encoder
OUTPUT_AUDIO_CODEC = "eac3"     # Can be changed to ac3, aac, etc.
COPY_ALL_AUDIO_OR_VIDEO_STREAMS_OF_ALLOWED_CODECS = False  # Set to True to preserve all streams
```

---

## 🚀 Usage
```bash
#One time run:
chmod +x ffmpeg_convert.py

#And then you can call it like this:
./ffmpeg_convert.py 
```
```bash
python3 ffmpeg_convert.py <input_path> [options]
#or
./ffmpeg_convert.py <input_path> [options]
```

### 📁 Input

- A single video file (e.g. `movie.mkv`)
- Or a directory (e.g. `/media/films`) – processes all supported formats recursively

### ⚙️ Options

| Option              | Description                                    |
| ------------------- | ---------------------------------------------- |
| `-i`                | Show codec info only, no conversion            |
| `-s`, `--subs-only` | Convert subtitles only                         |
| `--log <file>`      | Output all messages to log file                |
| `--dry-run`         | Preview what would be done, without converting |
| `--help`, `-h`      | Display help and exit                          |

---

## 💡 Examples

### Convert a single file:

```bash
python3 script.py movie.mkv
```

### Convert all videos in a directory:

```bash
python3 script.py /path/to/videos
```

### Preview conversion without executing:

```bash
python3 script.py /path/to/videos --dry-run
```

### Convert only subtitles:

```bash
python3 script.py /path/to/videos --subs-only
```

### Log output to file:

```bash
python3 script.py movie.mkv --log output.log
```

---

## ⚠️ Known Issues

- Subtitles in `.mkv` files are copied, but language metadata is lost
- Only the **first** audio/video stream is converted
- To preserve additional streams (e.g. secondary audio tracks), set `COPY_ALL_AUDIO_OR_VIDEO_STREAMS_OF_ALLOWED_CODECS = True`
  - ⚠️ This may disable real-time FFmpeg stats like time/speed/bitrate

---

## 📂 Supported Formats

- `.avi`, `.mkv`, `.mp4`, `.mpg`, `.mpeg`, `.mov`, `.wmv`

---

## 👤 Author

GitHub: [@tomaz1](https://github.com/tomaz1)

---

## 🛠 Dependencies

- `ffmpeg`
- `ffprobe`
- `iconv` (for subtitle encoding conversion)
- Python 3.x

Tested on **Ubuntu Linux** environment.

---

## 📜 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

---

> “Do we really need more than one audio or video stream?” 😉

