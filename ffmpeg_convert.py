#!/usr/bin/env python3
#Tomaž 12. 6. 25, v1.0 inicial version
# Changes:
#   13. 6. 25 v1.1 added support for subtitles conversion and copying
#   13. 6. 25 v1.2 added support for UTF-8 conversion of subtitles
#   14. 6. 25 v1.3 changed output audio codec from aac to ac3
#   14. 6. 25 v1.4 added support for EAC3 audio codec, changed default audio codec to EAC3.
#                  Include only conversion of first audio and video stream! (Do we really need more than audio or video stream?)
#                  Added CRF setting for x265 codec, default is 20.  
#   14. 6. 25 v1.5 Added support for copying all audio and video streams of allowed codecs, but without real-time stats.
#   15. 6. 25 v1.6 Added support for dynamic bitrate mapping based on number of audio channels.
#
# Known issues:
#  - If the input .mkv file contains subtitles, they will be copied to the new file,
#    but any language tags will be lost.
#
#  - If the input file contains multiple audio or video streams that need to be converted,
#    only the first matching stream will be converted.
#    However:
#     - If only the video stream needs to be converted, you can use the global setting
#       COPY_ALL_AUDIO_OR_VIDEO_STREAMS_OF_ALLOWED_CODECS to allow copying all audio streams.
#     - If only the audio stream needs to be converted, the same setting allows copying all video streams.
#  - EAC3 on ffmpeg doesnt support more than 5.1 channels

VERSION = "1.6"
import os
import sys
import argparse
import subprocess
from pathlib import Path
import multiprocessing
import re

NUMBER_OF_THREADS = multiprocessing.cpu_count()
if NUMBER_OF_THREADS > 16:
    NUMBER_OF_THREADS = 16

# ====================
# Configuration section
# ====================

MULTITHREADING_ENABLED = True
# ====================

#FORCE_CONVERSION_VIDEO_CODECS = ["MPEG4-XVID","H264"]
FORCE_CONVERSION_VIDEO_CODECS = ["MPEG4-XVID"]
#FORCE_CONVERSION_VIDEO_CODECS = ["MPEG4"] #if you would like to convert all MPEG4 videos, use this
FORCE_CONVERSION_AUDIO_CODECS = ["DTS", "TRUEHD"]

#video CRF setting, lower is better quality, but bigger file size
#Usually between 18 and 28 vor x265, 18 is visually lossless, 28 is low quality
CRF = "20"  # Default CRF value for x265, can be adjusted

# New bitrate mapping
DEFAULT_BITRATE = "768k"  # Default bitrate if channels are unknown
BITRATE_MAP = {
    2: "384k",
    3: "448k",
    5: "768k",
    6: "768k",
    7: "1024k",
    8: "1536k"
}

OUTPUT_VIDEO_CODEC = "libx265"
#OUTPUT_AUDIO_CODEC = "aac"
#aac speed on old CPU is 1x-2x, conversion to ac3 is 35x-40x !

#Tested aac, ac3 and eac3
#OUTPUT_AUDIO_CODEC = "ac3" # max bitrate = 640k !!
#EAC3 is even faster then eac3 conversion on same old CPU, speed 45-50x
OUTPUT_AUDIO_CODEC = "aac" # libfdk_aac?

# If True, all audio and video streams that use allowed codecs will be copied instead of just the first stream.
# This is useful when input files contain multiple audio tracks (such as different languages or commentary),
# or multiple video streams (alternative angles, versions, etc.). When enabled, it ensures no potentially
# important streams are accidentally lost—even if only the video or audio stream is being converted.
#
# However, enabling this option may prevent FFmpeg from displaying real-time encoding statistics such as
# elapsed time, bitrate, and conversion speed. This is most likely to happen when multiple streams are being copied.
# If the input file contains only a single stream, stats may still be shown normally despite this setting.
#
# Example when False (normal stats shown):
# frame=171211 fps= 45 q=32.0 Lsize=2207382KiB time=01:59:00.84 bitrate=2532.3kbits/s speed=1.89x
#
# Example when True (stats may be disabled or shown as N/A):
# frame=171211 fps=1062 q=-1.0 Lq=-1.0 q=-1.0 size=15714940KiB time=N/A bitrate=N/A speed=N/A
#
# Do we really need more than one audio or video stream?
COPY_ALL_AUDIO_OR_VIDEO_STREAMS_OF_ALLOWED_CODECS = False  # False or True
# Paramether --output-mp4 will reset this setting to false (even if set to True in here)

SUPPORTED_EXTENSIONS = [".avi", ".mkv", ".mp4", ".mpg", ".mpeg", ".mov", ".wmv"]

# ====================
# ======================================================================================================================
#                  END OF CONFIGURATION SECTION
# ======================================================================================================================

# ====================
# Help
# ====================
def help():
    message = """
FFmpeg Video Converter Script, v{4} (Tomaž 2025)

Usage:
  python3 script.py <input_path> [-i] [--log output.log] [--dry-run] [--output-mp4] [-s]

Options:
  -i                    Only display video/audio codec info, no conversion.
  -s, --subs-only       Convert subtitles only (no video/audio processing).
  --log <filename>      Write output to log file instead of console.
  --dry-run             Simulate conversion without actually running ffmpeg.
  --output-mp4          Force output format to MP4 regardless of input format.
  --help, -h            Show this help message and exit.

Behavior:
  - If input is a file, convert it.
  - If input is a directory, recursively convert all known video formats.
  - Skips files starting with 'conv-'.
  - Output files are saved in the same folder as originals with 'conv-' prefix.
  - Conversion happens only if codec is on the forced conversion list.

Configuration:
  - FORCE_CONVERSION_VIDEO_CODECS: {0}
  - FORCE_CONVERSION_AUDIO_CODECS: {1}
  - OUTPUT_VIDEO_CODEC: {2}
  - OUTPUT_AUDIO_CODEC: {3}
""".format(FORCE_CONVERSION_VIDEO_CODECS, FORCE_CONVERSION_AUDIO_CODECS, OUTPUT_VIDEO_CODEC, OUTPUT_AUDIO_CODEC, VERSION)
    print(message)

# ====================
# Entry point check
# ====================
if len(sys.argv) == 1:
    help()
    sys.exit(0)

# ====================
def print_or_log(message, log_file=None):
    if log_file:
        with open(log_file, "a") as f:
            f.write(message + "\n")
    else:
        print(message)

# ====================
# Argument Parsing
# ====================
def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("input_path", nargs="?", help="Input file or directory")
    parser.add_argument("-i", action="store_true", dest="info_only", help="Show codec info only")
    parser.add_argument("-s", "--subs-only", action="store_true", dest="subs_only", help="Convert subtitles only")
    parser.add_argument("--log", dest="log_file", help="Path to log file")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without actual conversion")
    parser.add_argument("--help", "-h", action="store_true", dest="show_help", help="Show help")
    parser.add_argument("--output-mp4", action="store_true", dest="output_mp4", help="Force MP4 as output format for all conversions")
    args = parser.parse_args()

    if args.show_help:
        help()
        sys.exit(0)

    if not args.input_path and not args.info_only:
        #print("Error: Missing input path. Use --help for usage information.")
        print_or_log("Error: Missing input path. Use --help for usage information.", args.log_file)

        sys.exit(1)

    return args

# ====================
# Subtitle Encoding Conversion
# ====================
def convert_srt_to_utf8(original_path, log_file=None, dry_run=False):
    try:
        result = subprocess.run(["file", "-b", "--mime-encoding", str(original_path)], capture_output=True, text=True)
        encoding = result.stdout.strip()

        if encoding in ["unknown-8bit", "windows-1250"]:
            utf8_path = original_path.with_name(original_path.stem + ".utf8.srt")
            if utf8_path.exists():
                print_or_log(f"     UTF-8 version already exists: {utf8_path}", log_file)
                return utf8_path

            if dry_run:
                print_or_log(f"     DRY RUN: Would convert {original_path} from {encoding} to UTF-8", log_file)
            else:
                subprocess.run(["iconv", "-f", "windows-1250", "-t", "UTF-8", "-o", str(utf8_path), str(original_path)], check=True)
                print_or_log(f"     Subtitle converted from {encoding} to UTF-8: {utf8_path}", log_file)
            return utf8_path

    except Exception as e:
        print_or_log(f"     Error during subtitle encoding check/convert: {e}", log_file)
    return None

# ====================
def scan_file(file_path, log_file=None):
    """Returns a dict with detected video, audio codec names and audio metadata."""
    result = {"video_codec": None, "audio_codec": None, "audio_metadata": {}}

    try:
        video_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,codec_tag_string",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ]
        video_output_lines = subprocess.check_output(video_cmd, stderr=subprocess.DEVNULL).decode().strip().splitlines()
        codec_name = video_output_lines[0].strip().upper() if len(video_output_lines) > 0 else None
        codec_tag = video_output_lines[1].strip().upper() if len(video_output_lines) > 1 else None

        if codec_tag and not codec_tag.startswith("["):
            result["video_codec"] = f"{codec_name}-{codec_tag}"
        else:
            result["video_codec"] = codec_name

        audio_cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name,channels,sample_rate",
            "-of", "json",
            str(file_path)
        ]
        audio_info = subprocess.check_output(audio_cmd, stderr=subprocess.DEVNULL)
        import json
        parsed = json.loads(audio_info)
        if parsed.get("streams"):
            stream = parsed["streams"][0]
            result["audio_codec"] = stream.get("codec_name", "").upper()
            result["audio_metadata"] = {
                "channels": stream.get("channels"),
                "sample_rate": stream.get("sample_rate")
            }
        #print(f" Detected metadata: audio channels={result['audio_metadata'].get('channels', '?')}, sample rate={result['audio_metadata'].get('sample_rate', '?')} Hz")
        
    except subprocess.CalledProcessError:
        #print(f"Error: Failed to analyze file {file_path}")
        print_or_log(f"Error: Failed to analyze file {file_path}", log_file)

    return result

# ====================
def should_convert(video_codec, audio_codec):
    """Determine whether the video or audio stream needs conversion."""
    convert_video = False
    convert_audio = False

    if FORCE_CONVERSION_VIDEO_CODECS:
        #print(f"Forced video codecs: {FORCE_CONVERSION_VIDEO_CODECS}")

        # FORCE_CONVERSION_VIDEO_CODECS is here already uppercase
        for forced_codec in FORCE_CONVERSION_VIDEO_CODECS: 
            if "-" in forced_codec:
                if video_codec.upper() == forced_codec:
                    convert_video = True
                    break
            else:
                if video_codec.upper().startswith(forced_codec):
                    convert_video = True
                    break

    if FORCE_CONVERSION_AUDIO_CODECS:
        if audio_codec.upper() in FORCE_CONVERSION_AUDIO_CODECS:
            convert_audio = True

    return convert_video, convert_audio

# ====================
def copy_subtitle_if_exists(input_path, output_path, log_file=None, dry_run=False):
    utf8_subtitle_path = input_path.with_name(input_path.stem + ".utf8.srt")
    fallback_srt = input_path.with_suffix(".srt")
    output_srt = output_path.with_suffix(".srt")

    # If .utf8.srt exists and this is a video conversion, copy it as conv-*.srt
    if utf8_subtitle_path.exists():
        if not dry_run:
            try:
                with open(utf8_subtitle_path, 'rb') as src, open(output_srt, 'wb') as dst:
                    dst.write(src.read())
                print_or_log(f"     Subtitle copied: {output_srt.name}", log_file)
            except Exception as e:
                print_or_log(f"     Error copying subtitle: {e}", log_file)
        else:
            print_or_log(f"     DRY RUN: Would copy subtitle {utf8_subtitle_path} to {output_srt.name}", log_file)
        return

    # If only .srt exists and encoding is invalid, convert it to UTF-8 and save as conv-*.srt
    if fallback_srt.exists():
        try:
            result = subprocess.run(["file", "-b", "--mime-encoding", str(fallback_srt)], capture_output=True, text=True)
            encoding = result.stdout.strip()
            if encoding in ["unknown-8bit", "windows-1250"]:
                if not dry_run:
                    subprocess.run(["iconv", "-f", "windows-1250", "-t", "UTF-8", "-o", str(output_srt), str(fallback_srt)], check=True)
                    print_or_log(f" --> Subtitle converted and saved: {output_srt.name}", log_file)
                else:
                    print_or_log(f"     DRY RUN: Would convert {fallback_srt} and save as {output_srt.name}", log_file)
                return
            else:
                print_or_log(f"     Subtitle {fallback_srt} encoding '{encoding}' does not require conversion.", log_file)
                # If subtitle is already valid UTF-8 and output does not exist, copy it
                if not output_srt.exists():
                    if not dry_run:
                        try:
                            with open(fallback_srt, 'rb') as src, open(output_srt, 'wb') as dst:
                                dst.write(src.read())
                            print_or_log(f"     Subtitle copied (UTF-8, no conversion needed): {output_srt.name}", log_file)
                        except Exception as e:
                          print_or_log(f"     Error copying UTF-8 subtitle: {e}", log_file)
                    else:
                        print_or_log(f"     DRY RUN: Would copy subtitle {fallback_srt.name} to {output_srt.name}", log_file)
        except Exception as e:
            print_or_log(f"     Error checking/converting subtitle: {e}", log_file)
    return

# ====================
def build_video_args(input_path, convert_video, output_video_codec, output_ext):
    args = []

    if convert_video:
        args += ["-map", "0:v:0"]  # always convert only the first video stream
        args += ["-c:v", OUTPUT_VIDEO_CODEC]
        args += ["-x265-params", "rd=2:psy-rd=1.5:lookahead-slices=1"]
        args += ["-preset", "fast"]
        args += ["-crf", CRF]
    else:
        if COPY_ALL_AUDIO_OR_VIDEO_STREAMS_OF_ALLOWED_CODECS:
            args += ["-map", "0:v"]  # copy all video streams
        else:
            args += ["-map", "0:v:0"]  # copy only first video stream
        args += ["-c:v", "copy"]

    return args

# ====================
def build_audio_args(input_path, convert_audio, original_audio_codec, output_audio_codec, default_bitrate, scan_func):
    args = []

    if convert_audio:
        args += ["-map", "0:a:0"]  # always convert only the first audio stream
        args += ["-map_metadata", "-1"]
        args += ["-c:a", OUTPUT_AUDIO_CODEC]

        audio_info = scan_func(input_path).get("audio_metadata", {})
        ch = audio_info.get("channels")
        sr = audio_info.get("sample_rate", "?")
        ch_desc = "Unknown"
        ch_num = None

        if isinstance(ch, int):
            ch_num = ch
        elif isinstance(ch, str):
            match = re.match(r"(\d)(?:\.(\d))?", ch)
            if match:
                front = int(match.group(1))
                lfe = int(match.group(2)) if match.group(2) else 0
                ch_num = front + lfe

        if ch_num is not None:
            if ch_num > 8:
                ch_desc = f"{ch_num}ch"
            elif ch_num == 8:
                ch_desc = "7.1"
            elif ch_num == 6:
                ch_desc = "5.1"
            elif ch_num == 2:
                ch_desc = "2.0"
            elif ch_num == 1:
                ch_desc = "Mono"
            else:
                ch_desc = f"{ch_num}ch"
        else:
            ch_desc = "5.1"

        if OUTPUT_AUDIO_CODEC.upper() in ["AC3", "EAC3"] and ch_desc == "7.1": #AC3 supports max 5.1
            ch_desc = "5.1"
            ch_num = 6  # force to 5.1 for AC3

        bitrate = BITRATE_MAP.get(ch_num, DEFAULT_BITRATE)  # fallback if channels unknown
        args += ["-b:a", bitrate]

        title = f"{OUTPUT_AUDIO_CODEC.upper()} Audio / {ch_desc} / {sr} Hz / {bitrate}"
        args += ["-metadata:s:a:0", f"title={title}"]

        if OUTPUT_AUDIO_CODEC.upper() in ["AC3", "EAC3"]:
            args += ["-ac", "6", "-channel_layout", "5.1"] #AC3 supports max 5.1
        elif ch_num and ch_num > 2:
            args += ["-ac", str(ch_num)]

        args += ["-ar", "48000"]

        bps_value = bitrate.replace('k', '000')
        args += ["-metadata:s:a:0", f"BPS={bps_value}"]
    else:
        #args += ["-map", "0:a"]  # copy all audio streams
        args += ["-c:a", "copy"]
        if COPY_ALL_AUDIO_OR_VIDEO_STREAMS_OF_ALLOWED_CODECS:
            args += ["-map", "0:a"]  # copy all audio streams
        else:
            args += ["-map", "0:a:0"]  # copy only first audio stream
        args += ["-c:a", "copy"]

    return args

# ====================
def convert_file(input_path, output_path, convert_video, convert_audio, original_video_codec, original_audio_codec, dry_run=False, log_file=None):
    cmd = ["ffmpeg", "-y", "-i", str(input_path)]

    #copy subtitles if output is MKV
    if output_path.suffix.lower() == ".mkv":
        cmd += ["-map", "0:s?"]
        cmd += ["-c:s", "copy"]

    # Compose video and audio arguments
    cmd += build_video_args(input_path, convert_video, OUTPUT_VIDEO_CODEC, output_path.suffix.lower())
    cmd += build_audio_args(input_path, convert_audio, original_audio_codec, OUTPUT_AUDIO_CODEC, DEFAULT_BITRATE, scan_file)

    if MULTITHREADING_ENABLED:
        cmd += ["-threads", str(NUMBER_OF_THREADS)]
    
    cmd += [str(output_path)]

    if dry_run:
        print_or_log("     DRY RUN: Would run: " + " ".join(cmd), log_file)
        return

    try:
        print_or_log(f"CMD used: {cmd})", log_file)
        subprocess.run(cmd, check=True)
        video_status = original_video_codec if convert_video else "OK"
        audio_status = original_audio_codec if convert_audio else "OK"
        print_or_log(f" --> File {output_path} has been converted (video was: {video_status}, audio was: {audio_status})", log_file)
    except subprocess.CalledProcessError:
        print_or_log(f"     Error converting file {input_path}", log_file)
        raise

    copy_subtitle_if_exists(input_path, output_path, log_file, dry_run)

# ====================
def process_file(file_path, log_file=None, dry_run=False):
    if file_path.name.startswith("conv-"):
        print_or_log(f"     File {file_path} has already been converted (starts with 'conv-')", log_file)
        return False

    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return False

    output_ext = '.mkv' if file_path.suffix.lower() == '.mkv' else '.mp4'
    output_ext = '.mp4' if force_mp4 else ('.mkv' if file_path.suffix.lower() == '.mkv' else '.mp4')
    output_filename = f"conv-{file_path.stem}{output_ext}"
    output_path = file_path.parent / output_filename
    existing_files = list(file_path.parent.glob(f"conv-{file_path.stem}.*"))
    if existing_files:
        print_or_log(f"     File {file_path} has already been converted (conv-* exists)", log_file)
        return False

    codecs = scan_file(file_path, log_file)
    video_codec = codecs.get("video_codec")
    audio_codec = codecs.get("audio_codec")

    if not video_codec or not audio_codec:
        print_or_log(f"     Skipping {file_path} (could not detect codecs)", log_file)
        return False

    if dry_run:
        print_or_log(f"\nDRY-RUN: Checking {file_path.name}", log_file)
        print_or_log(f"     Detected codecs: video={video_codec}, audio={audio_codec}", log_file)

    convert_video, convert_audio = should_convert(video_codec, audio_codec)

    if dry_run:
        if convert_video or convert_audio:
            print_or_log(f"---> It would convert this file!", log_file)

    if not convert_video and not convert_audio:
        print_or_log(f"     File {file_path} already in correct format.", log_file)
        return False

    convert_file(file_path, output_path, convert_video, convert_audio, video_codec, audio_codec, dry_run, log_file)
    return True

# ====================
def process_subtitles_only(input_path, log_file=None, dry_run=False):
    total_files = 0
    converted_subs = 0
    files = [input_path] if input_path.is_file() else list(input_path.rglob("*"))
    for file in files:
        if file.suffix.lower() not in SUPPORTED_EXTENSIONS or file.name.startswith("conv-"):
            continue

        base_srt = file.with_suffix(".srt")
        utf8_srt = file.with_name(file.stem + ".utf8.srt")

        if utf8_srt.exists():
            print_or_log(f"     Subtitle already exists: {utf8_srt.name}", log_file)
            continue

        if base_srt.exists():
            try:
                result = subprocess.run(["file", "-b", "--mime-encoding", str(base_srt)], capture_output=True, text=True)
                encoding = result.stdout.strip()
                if encoding in ["unknown-8bit", "windows-1250"]:
                    if not dry_run:
                        subprocess.run(["iconv", "-f", "windows-1250", "-t", "UTF-8", "-o", str(utf8_srt), str(base_srt)], check=True)
                        print_or_log(f"     Subtitle converted and saved: {utf8_srt.name}", log_file)
                    else:
                        print_or_log(f"     DRY RUN: Would convert {base_srt.name} and save as {utf8_srt.name}", log_file)
                    converted_subs += 1
                else:
                    print_or_log(f"     Subtitle {base_srt.name} encoding '{encoding}' does not require conversion.", log_file)
            except Exception as e:
                print_or_log(f"     Error checking/converting subtitle: {e}", log_file)

        total_files += 1

    print_or_log("\nSubtitles Summary:", log_file)
    print_or_log(f"  Files checked: {total_files}", log_file)
    print_or_log(f"  Subtitles created: {converted_subs}", log_file)

# === Main Entry Point ===
if __name__ == "__main__":
    args = parse_args()
    input_path = Path(args.input_path)
    dry_run = args.dry_run
    log_file = args.log_file
    force_mp4 = args.output_mp4
    if force_mp4: #MP4 supports only one video and one audio stream, so we need to set COPY_ALL_AUDIO_OR_VIDEO_STREAMS_OF_ALLOWED_CODECS to False
        COPY_ALL_AUDIO_OR_VIDEO_STREAMS_OF_ALLOWED_CODECS = False

    #Convert codec lists to uppercase
    FORCE_CONVERSION_VIDEO_CODECS = [v.upper() for v in FORCE_CONVERSION_VIDEO_CODECS]
    FORCE_CONVERSION_AUDIO_CODECS = [a.upper() for a in FORCE_CONVERSION_AUDIO_CODECS]

    if args.info_only:
        if input_path.is_file():
            codecs = scan_file(input_path, log_file)
            print_or_log(f"{input_path}", log_file)
            print_or_log(f"  video codec: {codecs.get('video_codec')}", log_file)
            print_or_log(f"  audio codec: {codecs.get('audio_codec')}", log_file)
            sys.exit(0)

        elif input_path.is_dir():
            for file in input_path.rglob("*"):
                if not file.name.startswith("conv-") and file.suffix.lower() in SUPPORTED_EXTENSIONS:
                    codecs = scan_file(file)
                    print_or_log(f"{file}", log_file)
                    print_or_log(f"  video codec: {codecs.get('video_codec')}", log_file)
                    print_or_log(f"  audio codec: {codecs.get('audio_codec')}", log_file)
            sys.exit(0)

    if args.subs_only:
        process_subtitles_only(input_path, log_file, dry_run)
        sys.exit(0)

    total_files = 0
    converted = 0
    skipped = 0
    failed = 0
    converted_files = []  # list of tuples: (path, video_status, audio_status)
    failed_files = []


    if input_path.is_file():
        total_files += 1
        try:
            if process_file(input_path, log_file, dry_run):
                converted += 1
                codecs = scan_file(input_path, log_file)
                video_status = codecs.get('video_codec', 'N/A')
                audio_status = codecs.get('audio_codec', 'N/A')
                converted_files.append((str(input_path), video_status, audio_status))
            else:
                skipped += 1
        except Exception:
            print_or_log(f" !!! Error processing file {input_path}: {sys.exc_info()[1]}", log_file)
            failed += 1
            failed_files.append(str(input_path))
    elif input_path.is_dir():
        for file in input_path.rglob("*"):
            if not file.name.startswith("conv-") and file.suffix.lower() in SUPPORTED_EXTENSIONS:
                total_files += 1
                try:
                    if process_file(file, log_file, dry_run):
                        converted += 1
                        codecs = scan_file(file, log_file)
                        video_status, audio_status = codecs.get('video_codec', 'N/A'), codecs.get('audio_codec', 'N/A')
                        converted_files.append((str(file), video_status, audio_status))
                    else:
                        skipped += 1
                except Exception:
                    print_or_log(f" !!! Error processing file {file}: {sys.exc_info()[1]}", log_file)
                    failed_files.append(str(file))
                    failed += 1

    if converted_files:
        print_or_log("\nConverted files:", log_file)
        for fpath, vcodec, acodec in converted_files:
            print_or_log(f" {fpath} (Video was: {vcodec}, audio was: {acodec})", log_file)
          
    if failed_files:
        print_or_log("\nFailed files:", log_file)
        for f in failed_files:
            print_or_log(f" {f}", log_file)

    print_or_log("\nSummary:", log_file)
    print_or_log(f"  Total files checked: {total_files}", log_file)
    print_or_log(f"  Converted: {converted}", log_file)
    print_or_log(f"  Skipped: {skipped}", log_file)
    print_or_log(f"  Failed: {failed}", log_file)
    print_or_log(f"  Using {NUMBER_OF_THREADS} threads for conversion.", log_file)
    if dry_run:
        print_or_log("\nDRY RUN: No files were actually converted.", log_file)
