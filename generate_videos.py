#!/usr/bin/env python3
"""
(V3.1 FFMPEG Edition) Peter Griffin Social Media Video Production Pipeline
Uses ffmpeg-python for robust and efficient video composition.
"""

import os
import json
import argparse
import logging
from pathlib import Path
import traceback
import tempfile
import time

try:
    import ffmpeg
    import whisper
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Please ensure you're in the chatterbox-venv environment and have run:")
    print("pip install ffmpeg-python openai-whisper Pillow")
    exit(1)

# --- Configuration ---
CONFIG = {
    # File Paths
    "ASSETS_DIR": Path("video_assets"),
    "SCREENSHOT_DIR": Path("twitter_analysis/screenshots"),
    "AUDIO_DIR": Path("chatterbox/audio_production/final_audio"),
    "OUTPUT_DIR": Path("final_videos_ffmpeg"), # New output folder

    # Video Settings
    "VIDEO_RESOLUTION": (1080, 1920),
    "VIDEO_FPS": 60,
    "SCREENSHOT_DURATION_SECONDS": 5,

    # Peter Griffin Avatar
    "AVATAR_WIDTH": 500,
    "AVATAR_POSITION": "W-w-30:H-h-30", # FFMPEG overlay expression for right-bottom with 30px margin
    
    # Caption Settings
    "CAPTION_FONT": "Impact",
    "CAPTION_FONT_SIZE": 18, # Increased font size for yellow captions
    "CAPTION_COLOR": "&H00FFFFFF",       # ASS format: &HBBGGRR -> White (default text)
    "CAPTION_HIGHLIGHT_COLOR": "&H00207BBB", # ASS format: &HBBGGRR -> Bright Yellow (highlighted word)
    "CAPTION_OUTLINE_COLOR": "&H000000", # ASS format -> Black
    "CAPTION_OUTLINE_WIDTH": 3,
    "CAPTION_MAX_WORDS_PER_LINE": 4,

    # Whisper ASR Model
    "WHISPER_MODEL": "base",
}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VideoGeneratorFFMPEG:
    """Orchestrates video generation using ffmpeg-python."""

    def __init__(self):
        self.output_dir = CONFIG["OUTPUT_DIR"]
        self.output_dir.mkdir(exist_ok=True)
        self.whisper_model = None

    def load_whisper_model(self):
        """Loads the Whisper model for transcription."""
        if self.whisper_model:
            return
        try:
            logger.info(f"Loading Whisper model '{CONFIG['WHISPER_MODEL']}'...")
            self.whisper_model = whisper.load_model(CONFIG['WHISPER_MODEL'])
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Could not load Whisper model. Error: {e}")
            raise

    def transcribe_audio(self, audio_path: Path) -> list:
        """Transcribes audio to get word-level timestamps."""
        self.load_whisper_model()
        logger.info(f"Transcribing {audio_path.name} for captions...")
        try:
            result = self.whisper_model.transcribe(str(audio_path), word_timestamps=True)
            all_words = [word for segment in result.get('segments', []) for word in segment.get('words', [])]
            logger.info(f"Transcription complete. Found {len(all_words)} words.")
            return all_words
        except Exception as e:
            logger.error(f"Transcription failed for {audio_path.name}: {e}")
            return []

    def _format_time(self, seconds: float) -> str:
        """Converts seconds to ASS subtitle format H:MM:SS.ss"""
        h = int(seconds / 3600)
        m = int((seconds % 3600) / 60)
        s = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{h:01}:{m:02}:{s:02}.{cs:02}"

    def create_ass_subtitle_files(self, words: list, temp_dir: Path) -> tuple:
        """Creates two separate .ass subtitle files for different positioning with karaoke highlighting."""
        # Top subtitles (when screenshot is displayed)
        ass_top_path = temp_dir / "captions_top.ass"
        # Middle subtitles (when screenshot is gone)
        ass_middle_path = temp_dir / "captions_middle.ass"
        
        # Style for top position (alignment 8 = top center)
        style_top = (f"Style: Default,{CONFIG['CAPTION_FONT']},{CONFIG['CAPTION_FONT_SIZE']},"
                     f"{CONFIG['CAPTION_COLOR']},&H00FFFFFF,{CONFIG['CAPTION_OUTLINE_COLOR']},"
                     f"&H00000000,-1,0,0,0,100,100,0,0,1,{CONFIG['CAPTION_OUTLINE_WIDTH']},"
                     f"0,8,30,30,50,1")
        
        # Style for middle position (alignment 5 = middle center)
        style_middle = (f"Style: Default,{CONFIG['CAPTION_FONT']},{CONFIG['CAPTION_FONT_SIZE']},"
                        f"{CONFIG['CAPTION_COLOR']},&H00FFFFFF,{CONFIG['CAPTION_OUTLINE_COLOR']},"
                        f"&H00000000,-1,0,0,0,100,100,0,0,1,{CONFIG['CAPTION_OUTLINE_WIDTH']},"
                        f"0,5,30,30,30,1")

        header_top = f"""
[Script Info]
Title: Peter Griffin Narration - Top
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_top}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        header_middle = f"""
[Script Info]
Title: Peter Griffin Narration - Middle
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_middle}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        lines_top = []
        lines_middle = []
        current_line_words = []
        current_line_word_data = []
        line_start_time = 0.0
        screenshot_duration = CONFIG['SCREENSHOT_DURATION_SECONDS']

        for i, word_data in enumerate(words):
            word_text = word_data['word'].strip().upper()
            start_time = word_data['start']
            end_time = word_data['end']
            
            if not current_line_words:
                line_start_time = start_time

            current_line_words.append(word_text)
            current_line_word_data.append(word_data)

            if len(current_line_words) >= CONFIG['CAPTION_MAX_WORDS_PER_LINE'] or i == len(words) - 1:
                line_end_time = end_time
                
                # Create karaoke effect text with timing
                karaoke_text = self._create_karaoke_text(current_line_word_data, line_start_time)
                
                # Determine if this line should be in top or middle position
                if line_start_time < screenshot_duration:
                    # Line starts during screenshot period - show at top
                    if line_end_time <= screenshot_duration:
                        # Entire line is during screenshot - top only
                        dialogue = f"Dialogue: 0,{self._format_time(line_start_time)},{self._format_time(line_end_time)},Default,,0,0,0,,{karaoke_text}"
                        lines_top.append(dialogue)
                    else:
                        # Line spans across screenshot transition - split it
                        # Top part (during screenshot)
                        dialogue_top = f"Dialogue: 0,{self._format_time(line_start_time)},{self._format_time(screenshot_duration)},Default,,0,0,0,,{karaoke_text}"
                        lines_top.append(dialogue_top)
                        # Middle part (after screenshot)
                        dialogue_middle = f"Dialogue: 0,{self._format_time(screenshot_duration)},{self._format_time(line_end_time)},Default,,0,0,0,,{karaoke_text}"
                        lines_middle.append(dialogue_middle)
                else:
                    # Line is entirely after screenshot - middle only
                    dialogue = f"Dialogue: 0,{self._format_time(line_start_time)},{self._format_time(line_end_time)},Default,,0,0,0,,{karaoke_text}"
                    lines_middle.append(dialogue)
                
                current_line_words = []
                current_line_word_data = []

        # Write top subtitles file
        with open(ass_top_path, "w", encoding='utf-8') as f:
            f.write(header_top)
            f.write("\n".join(lines_top))
        
        # Write middle subtitles file
        with open(ass_middle_path, "w", encoding='utf-8') as f:
            f.write(header_middle)
            f.write("\n".join(lines_middle))
        
        return ass_top_path, ass_middle_path

    def _create_karaoke_text(self, word_data_list: list, line_start_time: float) -> str:
        """Creates ASS karaoke text with timing for individual word highlighting."""
        karaoke_parts = []
        
        for i, word_data in enumerate(word_data_list):
            word_text = word_data['word'].strip().upper()
            word_start = word_data['start']
            word_end = word_data['end']
            
            # Calculate timing relative to line start (in centiseconds)
            word_duration_cs = int((word_end - word_start) * 100)
            
            # Add space before word (except for first word)
            if i > 0:
                karaoke_parts.append(" ")
            
            # ASS karaoke format: {\k<duration>}word
            # Use \k for karaoke effect that highlights the word when it's being spoken
            karaoke_part = f"{{\\k{word_duration_cs}\\c{CONFIG['CAPTION_HIGHLIGHT_COLOR']}}}{word_text}{{\\c{CONFIG['CAPTION_COLOR']}}}"
            karaoke_parts.append(karaoke_part)
        
        return "".join(karaoke_parts)

    def process_single_video(self, audio_path: Path):
        """Generates a single video short using ffmpeg-python."""
        base_name = audio_path.stem
        output_path = self.output_dir / f"{base_name}.mp4"
        tweet_id = base_name.split('_')[0]
        logger.info(f"Searching for screenshot for tweet ID: {tweet_id}")
        screenshot_path = None
        
        # Try multiple patterns to find the screenshot
        search_patterns = [
            f"**/tweet_{tweet_id}_*.png",  # Current format with timestamp
            f"**/tweet_{tweet_id}.png",    # Legacy format
            f"**/*{tweet_id}*.png"         # Fallback pattern
        ]
        
        for pattern in search_patterns:
            found_files = list(CONFIG["SCREENSHOT_DIR"].rglob(pattern))
            if found_files:
                # If multiple files found, use the most recent one
                screenshot_path = max(found_files, key=lambda x: x.stat().st_mtime)
                logger.info(f"Found screenshot: {screenshot_path}")
                break
        
        if not screenshot_path:
            logger.error(f"No screenshot found for tweet ID '{tweet_id}' using any of the search patterns.")
            return

        # Define required asset paths
        bg_video_path = CONFIG["ASSETS_DIR"] / "background_gameplay.mp4"
        avatar_path = CONFIG["ASSETS_DIR"] / "peter_avatar.png"
        
        if output_path.exists():
            logger.info(f"Skipping {output_path.name}, already exists.")
            return
    
        if not all([p and p.exists() for p in [screenshot_path, bg_video_path, avatar_path]]):
            logger.error(f"Missing asset for {base_name}. Required: screenshot, background, avatar. Skipping.")
            if not screenshot_path or not screenshot_path.exists():
                logger.error(f"  -> Specifically, screenshot for tweet ID '{tweet_id}' could not be found.")
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            try:
                # 1. Get Audio Duration & Transcribe
                probe = ffmpeg.probe(str(audio_path))
                audio_duration = float(probe['format']['duration'])
                word_timestamps = self.transcribe_audio(audio_path)
                if not word_timestamps:
                    logger.error(f"Could not get timestamps for {audio_path.name}, skipping video generation.")
                    return
                
                ass_top_path, ass_middle_path = self.create_ass_subtitle_files(word_timestamps, temp_dir_path)

                # 2. Define FFMPEG inputs
                gameplay_input = ffmpeg.input(str(bg_video_path), stream_loop=-1, t=audio_duration)
                screenshot_input = ffmpeg.input(str(screenshot_path))
                avatar_input = ffmpeg.input(str(avatar_path))
                audio_input = ffmpeg.input(str(audio_path))

                # 3. Build the complex filter graph
                # Background processing
                processed_bg = (
                    gameplay_input.video
                    .filter('crop', 'ih*9/16', 'ih')
                    .filter('scale', CONFIG["VIDEO_RESOLUTION"][0], CONFIG["VIDEO_RESOLUTION"][1])
                    .filter('setsar', '1')
                )
                
                # Screenshot overlay
                screenshot_overlay = (
                    screenshot_input.video
                    .filter('scale', CONFIG["VIDEO_RESOLUTION"][0], -1)
                    # Show screenshot only for the first N seconds
                    .filter('setpts', 'PTS-STARTPTS') 
                )
                
                # Avatar overlay
                avatar_overlay = (
                    avatar_input.video
                    .filter('scale', CONFIG["AVATAR_WIDTH"], -1)
                )

                # Chain the overlays
                video_with_ss = processed_bg.overlay(
                    screenshot_overlay,
                    x='(main_w-overlay_w)/2', y='(main_h-overlay_h)/2',
                    enable=f'between(t,0,{CONFIG["SCREENSHOT_DURATION_SECONDS"]})'
                )

                video_with_avatar = video_with_ss.overlay(
                    avatar_overlay,
                    x=CONFIG["AVATAR_POSITION"].split(':')[0], 
                    y=CONFIG["AVATAR_POSITION"].split(':')[1]
                )

                # Add both subtitle filters with different positioning
                video_with_top_subs = video_with_avatar.filter('subtitles', str(ass_top_path))
                final_video = video_with_top_subs.filter('subtitles', str(ass_middle_path))

                # 4. Concatenate final video stream with audio and run
                logger.info(f"Composing and rendering video for {output_path.name}...")
                (
                    ffmpeg
                    .concat(final_video, audio_input.audio, v=1, a=1)
                    .output(
                        str(output_path),
                        vcodec='libx264',
                        acodec='aac',
                        preset='ultrafast',
                        r=CONFIG["VIDEO_FPS"],
                        pix_fmt='yuv420p'
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                logger.info(f"Successfully created {output_path.name}")

            except ffmpeg.Error as e:
                logger.error(f"ffmpeg error on {audio_path.name}:")
                logger.error(f"STDOUT: {e.stdout.decode('utf-8')}")
                logger.error(f"STDERR: {e.stderr.decode('utf-8')}")
            except Exception as e:
                logger.error(f"An unexpected error occurred for {audio_path.name}: {e}")
                logger.error(traceback.format_exc())

    def run_batch_processing(self, limit: int = None):
        """Finds all processed audio and generates a video for each."""
        audio_files = sorted(list(CONFIG["AUDIO_DIR"].glob("*.mp3")))
        if not audio_files:
            logger.error(f"No .mp3 files found in {CONFIG['AUDIO_DIR']}. Did the audio pipeline run successfully?")
            return

        if limit:
            audio_files = audio_files[:limit]

        logger.info(f"Found {len(audio_files)} audio files to process into videos.")
        self.load_whisper_model()

        for audio_path in audio_files:
            self.process_single_video(audio_path)
            
        logger.info("Video generation batch complete.")

def main():
    parser = argparse.ArgumentParser(description="🎬 Peter Griffin Social Media Video Production Pipeline (FFMPEG Edition).")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of videos to generate (for testing).")
    args = parser.parse_args()
    
    pipeline = VideoGeneratorFFMPEG()
    pipeline.run_batch_processing(limit=args.limit)

if __name__ == "__main__":
    main()