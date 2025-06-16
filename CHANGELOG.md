# Changelog

Vse pomembne spremembe tega projekta bodo dokumentirane v tej datoteki.

Format je v skladu s [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [v1.7](https://github.com/tomaz1/ffmpeg_convert/releases/tag/v1.7) - 2025-06-16
### Added
- Added support for `--max-video-bitrate N` option to force video conversion if bitrate exceeds N kbps.
- Added `--crf` override option with fallback to `DEFAULT_CRF` (default: 20).
- FFmpeg now applies `-maxrate` and `-bufsize` when bitrate exceeds limit.
- `should_convert` now returns reasons for conversion (e.g., codec, bitrate).
- Improved dry-run logging for multiple conversion reasons.

## [1.6] - 2025-06-15
### Added
- Added support for dynamic audio bitrate mapping based on number of audio channels.

## [1.5] - 2025-06-14
### Added
- Added support for copying all audio and video streams of allowed codecs, but without real-time stats.

### Changed
- Changed default output audio codec from EAC to AAC since ffmpeg doesn't support 7.1 in EAC!

## [1.4] - 2025-06-14
### Added
- Added support for EAC3 audio codec, changed default audio codec to EAC3.
- Added CRF setting for x265 codec, default is 20.

### Changed
- Include only conversion of first audio and video stream! (Do we really need more than audio or video stream?)

## [1.3] - 2025-06-14
### Changed
- Changed default output audio codec from AAC to EAC3

## [1.2] - 2025-06-13
### Added
- Added support for UTF-8 conversion of subtitles

## [1.1] - 2025-06-13
### Added
- Added support for subtitles conversion and copying

## [1.0] - 2025-06-12
### Added
- Inicial version
