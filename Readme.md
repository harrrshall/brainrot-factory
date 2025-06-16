# Brainrot Factory 🤖

Welcome to Brainrot Factory! This is a complete, multi-stage pipeline that automates the creation of short-form videos for platforms like TikTok, YouTube Shorts, and Instagram Reels.

The pipeline works by:

1.  **Scraping** trending content from your X (Twitter) feed.
2.  **Generating** entertaining narration scripts using an LLM (like Google's Gemini).
3.  **Cloning** a character's voice (e.g., Peter Griffin) using the open-source **[Chatterbox TTS](https://github.com/resemble-ai/chatterbox)** model to create high-quality audio narrations.
4.  **Composing** a final video by combining the narration with gameplay footage, a character avatar, tweet screenshots, and dynamic, word-for-word captions.

This repository contains all the scripts and instructions needed to set up and run your own automated content factory.

## Table of Contents

- [Features](#features)
- [Final Video Example](#final-video-example)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Set Up Python Environments](#2-set-up-python-environments)
  - [3. Prepare Required Assets](#3-prepare-required-assets)
- [The 5-Step Content Generation Workflow](#the-5-step-content-generation-workflow)
  - [**Step 1: Scrape Tweets**](#step-1-scrape-tweets)
  - [**Step 2: Generate Narration Scripts**](#step-2-generate-narration-scripts)
  - [**Step 3: Clean and Organize Scripts**](#step-3-clean-and-organize-scripts)
  - [**Step 4: Generate Voice-Cloned Audio**](#step-4-generate-voice-cloned-audio)
  - [**Step 5: Render the Final Videos**](#step-5-render-the-final-videos)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Features

- **End-to-End Automation:** From data collection to final video rendering.
- **High-Quality Voice Cloning:** Leverages the powerful Chatterbox TTS model for realistic voice synthesis.
- **Dynamic Video Composition:** Uses `ffmpeg` to robustly layer gameplay, images, and audio.
- **Automatic Captions:** Employs OpenAI's Whisper for accurate, word-level timestamping and caption generation.
- **Social Media Optimized:** Produces 9:16 vertical videos at 60fps, perfect for modern platforms.
- **Modular and Configurable:** Easily change the character voice, background video, fonts, and more by editing config files.

## Final Video Example

The final output is a ready-to-upload video with all the essential elements for high engagement:

| Element                    | Description                                                             |
| :------------------------- | :---------------------------------------------------------------------- |
| **Gameplay Background**    | A looping video (e.g., Subway Surfers, Minecraft parkour).              |
| **Tweet Screenshot**       | Displayed for the first 5 seconds as a powerful hook.                   |
| **Character Avatar**       | Overlaid in a corner to maintain character presence.                    |
| **Voice-Cloned Narration** | High-quality audio commentary in the chosen character's voice.          |
| **Dynamic Captions**       | Large, outlined text appears word-by-word, synchronized with the audio. |

<p align="center">
  <img src="https://i.imgur.com/tHqgR7c.png" alt="Video structure diagram" width="600">
</p>

## Prerequisites

Before you start, ensure you have the following installed on your system (Linux/macOS recommended):

- **Python 3.9** or higher.
- **Node.js and npm** (if required by your tweet download script).
- **Git** for cloning the repository.
- **FFmpeg:** A critical system dependency for all audio and video processing.

  ```bash
  # On Debian/Ubuntu
  sudo apt update && sudo apt install ffmpeg

  # On macOS (using Homebrew)
  brew install ffmpeg
  ```

- An **NVIDIA GPU** is highly recommended for the voice generation step, as it will be significantly faster than running on a CPU.

## Installation and Setup

Follow these one-time setup steps to prepare your project.

### 1. Clone the Repository

```bash
git clone https://github.com/harrrshall/brainrot-factory
cd brainrot-factory
```

### 2. Set Up Python Environments

This project uses two separate virtual environments to prevent dependency conflicts between data processing and the heavy AI/ML libraries.

#### **Environment A: `myenv` (for data processing)**

This lightweight environment is for preparing the text scripts.

```bash
# From the project root directory
python3 -m venv myenv
source myenv/bin/activate

# Install dependencies (create a requirements.txt file for this)
# pip install -r requirements.txt

# Deactivate when done
deactivate
```

#### **Environment B: `chatterbox-venv` (for AI and Video)**

This environment contains PyTorch, Chatterbox, Whisper, and FFmpeg tools.

```bash
# Navigate into the chatterbox subdirectory
cd chatterbox

# Create and activate the environment
python3 -m venv chatterbox-venv
source chatterbox-venv/bin/activate

# Install Chatterbox and its core dependencies from the local files
pip install -e .

# Install the other required libraries for video and audio
pip install pydub tqdm ffmpeg-python "openai-whisper==20231117" Pillow

# Deactivate for now. You will activate this environment for Steps 4 and 5.
deactivate
```

### 3. Prepare Required Assets

You must provide the following media files for the pipeline to work. Place them in the specified directories:

- **Character Voice Sample: (Already Available)**

  - **File:** A 5-15 second, clean `.mp3` or `.wav` audio clip of the character's voice.
  - **Location:** `chatterbox/peter.mp3`

- **Gameplay Video: (Already Available)**

  - **File:** A video of gameplay footage (e.g., Subway Surfers, Minecraft, etc.).
  - **Location:** `video_assets/background_gameplay.mp4`

- **Character Avatar: (Already Available)**
  - **File:** A transparent `.png` image of the character.
  - **Location:** `video_assets/peter_avatar.png`

## The 5-Step Content Generation Workflow

Execute these steps in sequence to create a batch of videos.

### **Step 1: Scrape Tweets**

This step uses a JavaScript snippet to extract tweet data from your live X (Twitter) feed.

1.  **Open X (Twitter)** in your browser and scroll through your feed to load tweets.
2.  **Open the Developer Console** (`Ctrl+Shift+J` or `Cmd+Option+J`).
3.  **Copy the entire contents** of the `find_trending_tweet.js` file.
4.  **Paste the code into the console** and press `Enter`.
5.  A `tweets.csv` file will be downloaded to your computer. **Move this file into the project's root directory.**

### **Step 2: Generate Narration Scripts**

Use a powerful Large Language Model (LLM) like Gemini or ChatGPT to convert the raw tweet data into entertaining narration scripts.

1.  **Open your preferred LLM** (e.g., `gemini.google.com`).
2.  **Upload the `tweets.csv`** file you just downloaded.
3.  **Use the following prompt:**

    > Act as a scriptwriter for viral social media content. Your task is to turn the raw data in the attached CSV into engaging narration scripts for a commentator with a humorous, slightly unhinged personality like Peter Griffin.
    >
    > For each tweet, generate at least two script variations with different styles (e.g., one 'dramatic' and one 'casual').
    >
    > Your output must be a single, valid JSON array. Each object in the array should represent one narration script and must contain the following keys: `tweet_id`, `author_name`, `original_text`, `narration_text`, and `style`.

4.  **Save the LLM's output** as `gemini_narrations.json` in the project's root directory.

### **Step 3: Clean and Organize Scripts**

This step standardizes the JSON from the LLM and prepares it for the next stages.

1.  **Activate the `myenv` environment:**
    ```bash
    source myenv/bin/activate
    ```
2.  **Run the cleaning script:**
    ```bash
    # This command assumes your script is named 'clean_text_for_tts.py'
    # and is adapted to take the new JSON file as input.
    python3 clean_text_for_tts.py --input-file gemini_narrations.json
    ```
3.  **Verify the output:** A new, cleaned, and timestamped JSON file will be created in the `twitter_analysis/narrations/` directory.

### **Step 4: Generate Voice-Cloned Audio**

This is where the magic happens! We'll use Chatterbox to synthesize the narrations in Peter Griffin's voice.

1.  **Activate the `chatterbox-venv` environment:**
    ```bash
    # Make sure you are in the project root directory
    source chatterbox/chatterbox-venv/bin/activate
    ```
2.  **Run the narration script:** You need to provide the path to the cleaned JSON file from Step 3.
    ```bash
    # Replace [timestamp] with the actual filename
    python3 chatterbox/process_narrations.py twitter_analysis/narrations/narration_scripts_[timestamp].json
    ```
3.  **Check the output:** The generated `.mp3` audio files will appear in `chatterbox/audio_production/final_audio/`.

### **Step 5: Render the Final Videos**

The final step combines everything into polished videos.

1.  **Ensure `chatterbox-venv` is still active.**
2.  **Run the video generation script from the project root:**
    ```bash
    python3 generate_videos.py
    ```
    _You can use `--limit <number>` to test with a smaller number of videos, e.g., `python generate_videos.py --limit 2`._
3.  **Done!** Your finished videos are now in the `final_videos_ffmpeg/` directory, ready to be uploaded.

## Configuration

You can easily customize the output by editing the `CONFIG` dictionary at the top of `generate_videos.py`. This allows you to change:

- Video resolution and FPS.
- Avatar size and position.
- Caption font, size, color, and style.
- The Whisper model used for transcription (a larger model is more accurate but slower).

## Troubleshooting

- **`ffmpeg: command not found`**: You must install FFmpeg on your system. See the [Prerequisites](#prerequisites) section.
- **`Error: Missing asset...`**: The video script could not find one of the required files (`background_gameplay.mp4`, `peter_avatar.png`, or a tweet screenshot). Check that all files are in their correct locations as specified in the [Prepare Required Assets](#3-prepare-required-assets) section and that the filenames match exactly.
- **Font Errors in `ffmpeg`**: If you see an error like `Font not found`, make sure the font specified in `generate_videos.py` is installed on your operating system.
- **Slow Performance**: Voice generation and video rendering are very demanding. For best results, use a computer with a powerful CPU and a dedicated NVIDIA GPU.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details. Note that dependencies like Chatterbox TTS may have their own licenses.
