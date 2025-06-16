#!/usr/bin/env python3
"""
(Efficient V2) Enhanced Peter Griffin TTS Audio Production Pipeline
Integrates with Chatterbox TTS for high-quality voice cloning
Optimized for batch processing and social media output
"""

import os
import json
import datetime
import random
import argparse
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import traceback

try:
    import torch
    import torchaudio
    from pydub import AudioSegment
    from tqdm import tqdm
    from chatterbox.tts import ChatterboxTTS
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Please ensure you're in the chatterbox-venv environment and run:")
    print("pip install pydub tqdm torch torchaudio")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audio_production.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Peter Griffin Character Integration ---
PETER_INTROS = [
    "You know what really grinds my gears?",
    "Hey Lois, check this out!",
    "Holy crap, listen to this!",
    "Oh my God, this is worse than that time I",
    "Freakin' sweet! Get this:",
    "Roadhouse! So anyway,",
    "Bird is the word, but also",
    "Nyehehehehe, so",
]

PETER_COMMENTARY = [
    "Nyehehehehe.",
    "Alright!",
    "This is worse than the time I fought that giant chicken.",
    "That's what she said... wait, what?",
    "Holy schnikes!",
    "Giggity... wait, that's Quagmire.",
    "Ah geez, this stinks worse than Meg.",
    "Sweet Jesus on a pogo stick!",
]

PETER_TRANSITIONS = [
    "But wait, there's more!",
    "Speaking of which,",
    "Oh, and another thing,",
    "You know what else?",
    "Hold on to your butts,",
]

# Enhanced style mapping with Peter Griffin personality
STYLE_TO_MODULATION = {
    "casual": {
        "exaggeration": 0.8,
        "cfg_weight": 0.6,
        "temperature": 0.75,
        "description": "Laid-back Peter"
    },
    "dramatic": {
        "exaggeration": 1.5,
        "cfg_weight": 0.4,
        "temperature": 0.85,
        "description": "Excited Peter"
    },
    "informative": {
        "exaggeration": 0.6,
        "cfg_weight": 0.65,
        "temperature": 0.7,
        "description": "Smart Peter (rare)"
    },
    "comedic": {
        "exaggeration": 1.2,
        "cfg_weight": 0.45,
        "temperature": 0.8,
        "description": "Funny Peter"
    },
    "default": {
        "exaggeration": 0.75,
        "cfg_weight": 0.55,
        "temperature": 0.75,
        "description": "Standard Peter"
    },
}

class PeterGriffinTTSPipeline:
    """Main pipeline class for Peter Griffin TTS generation"""
    
    def __init__(self, ref_voice_path: str = "peter.mp3"):
        self.ref_voice_path = ref_voice_path
        self.model: Optional[ChatterboxTTS] = None
        # REFACTOR: Store the cloned voice condition here
        self.peter_griffin_conds: Optional[Dict] = None
        self.device = self._detect_device()
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'total_duration': 0.0,
            'start_time': None,
            'end_time': None
        }
        
    def _detect_device(self) -> str:
        """Detect the best available device for processing"""
        if torch.cuda.is_available():
            device = "cuda"
            logger.info(f"Using CUDA GPU: {torch.cuda.get_device_name()}")
        elif torch.backends.mps.is_available():
            device = "mps"
            logger.info("Using Apple MPS")
        else:
            device = "cpu"
            logger.info("Using CPU (this will be slower)")
        return device
    
    def setup_pipeline(self) -> bool:
        """
        REFACTOR: New method to load model and clone voice ONCE.
        """
        try:
            logger.info("Loading Chatterbox TTS model...")
            self.model = ChatterboxTTS.from_pretrained(device=self.device)
            logger.info("Model loaded.")
            
            if os.path.exists(self.ref_voice_path):
                logger.info(f"Cloning voice from '{self.ref_voice_path}'... This happens only once.")
                # This prepares the voice prompt and stores it in the model's internal state.
                self.model.prepare_conditionals(self.ref_voice_path, exaggeration=0.5)
                logger.info("Voice cloned successfully!")
            else:
                logger.warning(f"Reference voice file not found: {self.ref_voice_path}. Using default voice.")
            
            logger.info("Pipeline setup complete and ready!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup pipeline: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def create_output_structure(self) -> Dict[str, Path]:
        """Create organized output directory structure"""
        base_dir = Path("audio_production")
        dirs = {
            'final_audio': base_dir / "final_audio",
            'temp_audio': base_dir / "temp_audio",
            'reports': base_dir / "reports",
        }
        for dir_path in dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
        return dirs
    
    def enhance_text_with_peter_personality(self, text: str, style: str) -> str:
        """Add Peter Griffin personality to the narration text"""
        if style == "dramatic":
            intro = random.choice(PETER_INTROS[:4])
            commentary = random.choice(PETER_COMMENTARY[:4])
        elif style == "comedic":
            intro = random.choice(PETER_INTROS[4:])
            commentary = random.choice(PETER_COMMENTARY[4:])
        else:
            intro = random.choice(PETER_INTROS)
            commentary = random.choice(PETER_COMMENTARY)
        
        if len(text) > 200 and random.random() > 0.7:
            transition = random.choice(PETER_TRANSITIONS)
            enhanced_text = f"{intro} {text} {transition} {commentary}"
        else:
            enhanced_text = f"{intro} {text} {commentary}"
        return enhanced_text
    
    def chunk_text_smartly(self, text: str, max_length: int = 300) -> List[str]:
        """Intelligently chunk text for optimal TTS processing"""
        if len(text) <= max_length:
            return [text]
        
        chunks, current_chunk = [], ""
        # Split by sentences for natural pauses
        sentences = [s.strip() for s in text.replace('!', '.').replace('?', '.').split('.') if s]
        
        for sentence in sentences:
            if not sentence:
                continue
            if len(current_chunk) + len(sentence) + 1 <= max_length:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    def generate_audio_from_chunks(self, text_chunks: List[str], modulation_settings: Dict) -> Optional[torch.Tensor]:
        """
        REFACTOR: Generate audio from chunks using the pre-cloned voice.
        """
        audio_segments = []
        for chunk in text_chunks:
            # Note: We no longer pass audio_prompt_path here!
            # The model uses the voice that was prepared in setup_pipeline().
            wav_chunk = self.model.generate(
                text=chunk,
                **{k: v for k, v in modulation_settings.items() if k != 'description'}
            )
            audio_segments.append(wav_chunk)
        
        return torch.cat(audio_segments, dim=-1) if audio_segments else None
    
    def process_single_script(self, script: Dict, output_dirs: Dict) -> Dict:
        """Process a single narration script"""
        tweet_id = script.get("tweet_id", f"unknown_{random.randint(1000, 9999)}")
        style = script.get("style", "default")
        narration_text = script.get("narration_text", "")
        
        metadata = {
            'tweet_id': tweet_id,
            'style': style,
            'processing_timestamp': datetime.datetime.now().isoformat(),
            'processing_status': 'pending',
            'original_script': script
        }
        
        if not narration_text.strip():
            metadata.update({
                'processing_status': 'failed',
                'error': 'Empty narration text'
            })
            return metadata
        
        base_filename = f"{tweet_id}_{style}_{int(time.time())}"
        temp_path = output_dirs['temp_audio'] / f"{base_filename}.wav"
        final_path = output_dirs['final_audio'] / f"{base_filename}.mp3"
        
        try:
            start_time = time.time()
            modulation_settings = STYLE_TO_MODULATION.get(style, STYLE_TO_MODULATION["default"])
            enhanced_text = self.enhance_text_with_peter_personality(narration_text, style)
            text_chunks = self.chunk_text_smartly(enhanced_text)
            
            wav_tensor = self.generate_audio_from_chunks(text_chunks, modulation_settings)
            
            generation_info = {
                'chunks_processed': len(text_chunks),
                'processing_time': time.time() - start_time,
                'enhanced_text': enhanced_text
            }
            
            if wav_tensor is None:
                metadata.update({
                    'processing_status': 'failed',
                    'error': 'Audio generation failed',
                    'generation_info': generation_info
                })
                return metadata
            
            audio_info = self.enhance_and_export_audio(wav_tensor, temp_path, final_path, tweet_id)
            
            if audio_info['success']:
                metadata.update({
                    'processing_status': 'success',
                    'output_files': {
                        'temp_wav': str(temp_path),
                        'final_mp3': str(final_path)
                    },
                    'audio_info': audio_info,
                    'generation_info': generation_info,
                    'modulation_settings': modulation_settings
                })
            else:
                metadata.update({
                    'processing_status': 'failed',
                    'error': f"Audio enhancement failed: {audio_info.get('error', 'Unknown error')}"
                })
            
        except Exception as e:
            metadata.update({
                'processing_status': 'failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            logger.error(f"Failed to process tweet {tweet_id}: {e}")
        
        return metadata
    
    def enhance_and_export_audio(self, wav_tensor: torch.Tensor, temp_path: Path, final_path: Path, tweet_id: str) -> Dict:
        """Enhanced audio processing with social media optimization"""
        try:
            torchaudio.save(str(temp_path), wav_tensor, self.model.sr)
            audio = AudioSegment.from_wav(str(temp_path))
            normalized_audio = audio.normalize(headroom=0.1)
            compressed_audio = normalized_audio.compress_dynamic_range(threshold=-20.0, ratio=4.0)
            enhanced_audio = compressed_audio + 1
            enhanced_audio.export(
                str(final_path),
                format="mp3",
                bitrate="192k",
                parameters=["-ac", "1"],
                tags={
                    "artist": "Peter Griffin",
                    "title": f"Tweet Narration {tweet_id}"
                }
            )
            return {
                'success': True,
                'duration_seconds': round(len(enhanced_audio) / 1000.0, 2),
                'file_size_mb': round(final_path.stat().st_size / (1024 * 1024), 2)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_batch(self, narration_scripts: List[Dict]) -> Tuple[List[Dict], Dict]:
        """Process a batch of narration scripts with progress tracking"""
        self.stats['start_time'] = datetime.datetime.now()
        self.stats['total_processed'] = len(narration_scripts)
        output_dirs = self.create_output_structure()
        all_metadata = []
        
        for script in tqdm(narration_scripts, desc="🎭 Peter Griffin Narrating"):
            metadata = self.process_single_script(script, output_dirs)
            all_metadata.append(metadata)
            
            if metadata['processing_status'] == 'success':
                self.stats['successful'] += 1
                self.stats['total_duration'] += metadata.get('audio_info', {}).get('duration_seconds', 0)
            else:
                self.stats['failed'] += 1
        
        self.stats['end_time'] = datetime.datetime.now()
        return all_metadata, output_dirs
    
    def generate_comprehensive_report(self, metadata_list: List[Dict], output_dirs: Dict) -> str:
        """Generate a comprehensive processing report"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_dirs['reports'] / f"peter_griffin_tts_report_{timestamp}.json"
        
        successful_items = [m for m in metadata_list if m['processing_status'] == 'success']
        total_duration = sum(
            item.get('audio_info', {}).get('duration_seconds', 0)
            for item in successful_items
        )
        
        report = {
            'pipeline_info': {
                'version': '2.1_efficient'
            },
            'processing_stats': {
                'total_scripts': len(metadata_list),
                'successful': len(successful_items)
            },
            'audio_stats': {
                'total_audio_duration_minutes': round(total_duration / 60, 2)
            },
            'detailed_metadata': metadata_list
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        return str(report_path)


def main():
    """Main execution function with improved argument parsing"""
    parser = argparse.ArgumentParser(
        description="🎭 Peter Griffin TTS Audio Production Pipeline"
    )
    parser.add_argument(
        "input_json",
        type=str,
        help="Path to narration scripts JSON"
    )
    parser.add_argument(
        "--ref-voice",
        type=str,
        default="peter.mp3",
        help="Path to reference voice file"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Process only the first N scripts"
    )
    args = parser.parse_args()
    
    if not os.path.exists(args.input_json):
        logger.error(f"Input file not found: {args.input_json}")
        return 1
    
    try:
        with open(args.input_json, 'r', encoding='utf-8') as f:
            narration_scripts = json.load(f)
        
        if args.batch_size:
            narration_scripts = narration_scripts[:args.batch_size]
        
        # REFACTOR: Use the new setup method
        pipeline = PeterGriffinTTSPipeline(ref_voice_path=args.ref_voice)
        if not pipeline.setup_pipeline():
            return 1
        
        metadata_list, output_dirs = pipeline.process_batch(narration_scripts)
        report_path = pipeline.generate_comprehensive_report(metadata_list, output_dirs)
        
        print("\n" + "="*60)
        print("🎭 EFFICIENT PETER GRIFFIN TTS PIPELINE COMPLETE 🎭")
        print("="*60)
        print(f"✅ Successfully processed: {pipeline.stats['successful']}")
        print(f"❌ Failed: {pipeline.stats['failed']}")
        print(f"⏱️  Total processing time: {(pipeline.stats['end_time'] - pipeline.stats['start_time']).total_seconds():.1f}s")
        print(f"🎵 Total audio generated: {pipeline.stats['total_duration']:.1f} seconds")
        print(f"📁 Final audio files: audio_production/final_audio/")
        print(f"📊 Detailed report: {report_path}")
        print("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit(main())


# python3 process_narrations.py json file