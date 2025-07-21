"""Generate audio test samples for Voicemeeter testing.

This script creates various audio test files that can be used to test
Voicemeeter functionality and audio routing.
"""

import os
import math
import wave
import struct


def generate_sine_wave(frequency, duration, sample_rate=44100, amplitude=0.5):
    """Generate a sine wave audio signal."""
    frames = int(duration * sample_rate)
    audio_data = []
    
    for i in range(frames):
        # Generate sine wave
        value = amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)
        # Convert to 16-bit integer
        audio_data.append(int(value * 32767))
    
    return audio_data


def generate_stereo_test(left_freq, right_freq, duration, sample_rate=44100, amplitude=0.5):
    """Generate a stereo test signal with different frequencies in each channel."""
    frames = int(duration * sample_rate)
    audio_data = []
    
    for i in range(frames):
        # Left channel
        left_value = amplitude * math.sin(2 * math.pi * left_freq * i / sample_rate)
        # Right channel
        right_value = amplitude * math.sin(2 * math.pi * right_freq * i / sample_rate)
        
        # Convert to 16-bit integers
        left_sample = int(left_value * 32767)
        right_sample = int(right_value * 32767)
        
        audio_data.append((left_sample, right_sample))
    
    return audio_data


def save_mono_wav(filename, audio_data, sample_rate=44100):
    """Save mono audio data to a WAV file."""
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        # Pack audio data
        packed_data = struct.pack('<' + 'h' * len(audio_data), *audio_data)
        wav_file.writeframes(packed_data)


def save_stereo_wav(filename, audio_data, sample_rate=44100):
    """Save stereo audio data to a WAV file."""
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(2)  # Stereo
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        # Pack audio data (interleaved left/right)
        packed_data = b''
        for left, right in audio_data:
            packed_data += struct.pack('<hh', left, right)
        wav_file.writeframes(packed_data)


def generate_sweep(start_freq, end_freq, duration, sample_rate=44100, amplitude=0.5):
    """Generate a frequency sweep from start_freq to end_freq."""
    frames = int(duration * sample_rate)
    audio_data = []
    
    for i in range(frames):
        # Calculate current frequency (linear sweep)
        progress = i / frames
        current_freq = start_freq + (end_freq - start_freq) * progress
        
        # Generate sine wave at current frequency
        value = amplitude * math.sin(2 * math.pi * current_freq * i / sample_rate)
        audio_data.append(int(value * 32767))
    
    return audio_data


def generate_white_noise(duration, sample_rate=44100, amplitude=0.3):
    """Generate white noise."""
    import random
    frames = int(duration * sample_rate)
    audio_data = []
    
    for i in range(frames):
        # Generate random value between -1 and 1
        value = amplitude * (random.random() * 2 - 1)
        audio_data.append(int(value * 32767))
    
    return audio_data


def create_audio_samples():
    """Create all audio test samples."""
    output_dir = "audio_samples"
    
    print("Generating audio test samples...")
    print(f"Output directory: {output_dir}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Basic tone tests (440Hz A note)
    print("1. Generating basic tone test (440Hz)...")
    tone_440 = generate_sine_wave(440, 3.0)  # 3 seconds
    save_mono_wav(os.path.join(output_dir, "tone_440hz_3sec.wav"), tone_440)
    
    # 2. Low frequency test (100Hz)
    print("2. Generating low frequency test (100Hz)...")
    tone_100 = generate_sine_wave(100, 2.0)  # 2 seconds
    save_mono_wav(os.path.join(output_dir, "tone_100hz_2sec.wav"), tone_100)
    
    # 3. High frequency test (8000Hz)
    print("3. Generating high frequency test (8000Hz)...")
    tone_8k = generate_sine_wave(8000, 2.0)  # 2 seconds
    save_mono_wav(os.path.join(output_dir, "tone_8000hz_2sec.wav"), tone_8k)
    
    # 4. Stereo test (different frequencies in each channel)
    print("4. Generating stereo test (440Hz left, 880Hz right)...")
    stereo_test = generate_stereo_test(440, 880, 3.0)  # 3 seconds
    save_stereo_wav(os.path.join(output_dir, "stereo_test_440_880.wav"), stereo_test)
    
    # 5. Frequency sweep (20Hz to 20kHz)
    print("5. Generating frequency sweep (20Hz to 20kHz)...")
    sweep = generate_sweep(20, 20000, 10.0)  # 10 seconds
    save_mono_wav(os.path.join(output_dir, "frequency_sweep_20hz_20khz.wav"), sweep)
    
    # 6. Short beep for testing
    print("6. Generating short beep (1kHz)...")
    beep = generate_sine_wave(1000, 0.5)  # 0.5 seconds
    save_mono_wav(os.path.join(output_dir, "beep_1khz_500ms.wav"), beep)
    
    # 7. White noise test
    print("7. Generating white noise test...")
    noise = generate_white_noise(3.0)  # 3 seconds
    save_mono_wav(os.path.join(output_dir, "white_noise_3sec.wav"), noise)
    
    # 8. Channel identification tones (for multi-channel testing)
    print("8. Generating channel identification tones...")
    frequencies = [200, 300, 400, 500, 600, 700, 800, 900]  # Different freq for each channel
    for i, freq in enumerate(frequencies):
        tone = generate_sine_wave(freq, 2.0)
        filename = f"channel_{i+1}_tone_{freq}hz.wav"
        save_mono_wav(os.path.join(output_dir, filename), tone)
    
    print("\n✅ Audio samples generated successfully!")
    print(f"Files created in: {os.path.abspath(output_dir)}")
    
    # List all created files
    print("\nGenerated files:")
    for filename in sorted(os.listdir(output_dir)):
        if filename.endswith('.wav'):
            filepath = os.path.join(output_dir, filename)
            size = os.path.getsize(filepath)
            print(f"  📄 {filename} ({size:,} bytes)")


def create_readme():
    """Create a README file for the audio samples."""
    readme_content = """# Audio Test Samples

This directory contains various audio test files for testing Voicemeeter functionality.

## Files Description

### Basic Tones
- `tone_440hz_3sec.wav` - 440Hz tone (A note) for 3 seconds
- `tone_100hz_2sec.wav` - 100Hz low frequency tone for 2 seconds  
- `tone_8000hz_2sec.wav` - 8000Hz high frequency tone for 2 seconds
- `beep_1khz_500ms.wav` - Short 1kHz beep (0.5 seconds)

### Stereo Testing
- `stereo_test_440_880.wav` - Stereo test with 440Hz in left channel, 880Hz in right channel

### Frequency Analysis
- `frequency_sweep_20hz_20khz.wav` - 10-second sweep from 20Hz to 20kHz
- `white_noise_3sec.wav` - 3 seconds of white noise

### Channel Identification
- `channel_1_tone_200hz.wav` through `channel_8_tone_900hz.wav` - Individual channel identification tones

## Usage

These files can be used to:

1. **Test Voicemeeter routing** - Play files through different strips to verify routing
2. **Check audio levels** - Monitor input/output levels in Voicemeeter
3. **Verify stereo separation** - Use stereo test file to check left/right channel routing
4. **Test frequency response** - Use sweep and different frequency tones
5. **Identify channels** - Use channel identification tones for multi-channel setups

## Playing Files

You can play these files using:
- Windows Media Player
- VLC Media Player
- Any audio player that supports WAV files
- Command line: `start filename.wav` (Windows)

## Technical Specifications

- **Format**: WAV (uncompressed)
- **Sample Rate**: 44.1 kHz
- **Bit Depth**: 16-bit
- **Channels**: Mono (except stereo test file)
- **Amplitude**: Normalized to prevent clipping

## Integration with MCP Server

These files can be used with the Voicemeeter MCP Server to:
- Test parameter changes while audio is playing
- Monitor real-time audio levels
- Verify routing configurations
- Test preset loading

## Regenerating Files

To regenerate these files, run:
```bash
python generate_audio_samples.py
```

This will recreate all test files in the audio_samples directory.
"""
    
    with open("audio_samples/README.md", "w") as f:
        f.write(readme_content)
    
    print("📝 Created README.md for audio samples")


def main():
    """Main function to generate all audio samples."""
    print("VOICEMEETER AUDIO TEST SAMPLE GENERATOR")
    print("=" * 50)
    
    try:
        create_audio_samples()
        create_readme()
        
        print("\n🎉 All audio samples generated successfully!")
        print("\nThese files can be used to test:")
        print("  • Voicemeeter audio routing")
        print("  • Input/output level monitoring")
        print("  • Stereo channel separation")
        print("  • Frequency response")
        print("  • Multi-channel setups")
        
        print(f"\nTo use: Play any WAV file while testing the MCP server")
        print(f"Location: {os.path.abspath('audio_samples')}")
        
    except Exception as e:
        print(f"❌ Error generating audio samples: {e}")
        return False
    
    return True


if __name__ == "__main__":
    main()
