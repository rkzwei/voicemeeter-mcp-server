# Audio Test Samples

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
