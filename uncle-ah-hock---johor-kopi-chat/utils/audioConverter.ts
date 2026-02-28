/**
 * Audio Converter Module
 * Converts WebM audio to MP3 format using lamejs
 */

import lamejs from 'lamejs';

/**
 * Convert WebM blob to MP3 format
 * @param webmBlob WebM audio blob from MediaRecorder
 * @returns MP3 blob
 */
export async function convertToMp3(webmBlob: Blob): Promise<Blob> {
  try {
    // Decode WebM to PCM audio data
    const audioContext = new AudioContext();
    const arrayBuffer = await webmBlob.arrayBuffer();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

    // Get audio data from buffer
    const channels = audioBuffer.numberOfChannels;
    const sampleRate = audioBuffer.sampleRate;
    const samples = audioBuffer.length;

    // Convert to mono if stereo (lamejs expects mono or stereo)
    let leftChannel: Float32Array;
    let rightChannel: Float32Array | undefined;

    if (channels === 1) {
      leftChannel = audioBuffer.getChannelData(0);
    } else {
      leftChannel = audioBuffer.getChannelData(0);
      rightChannel = audioBuffer.getChannelData(1);
    }

    // Convert Float32Array to Int16Array (PCM 16-bit)
    const leftPCM = float32ToInt16(leftChannel);
    const rightPCM = rightChannel ? float32ToInt16(rightChannel) : undefined;

    // Initialize MP3 encoder
    const mp3encoder = new lamejs.Mp3Encoder(
      channels,
      sampleRate,
      128 // bitrate: 128 kbps
    );

    // Encode to MP3
    const mp3Data: Int8Array[] = [];
    const sampleBlockSize = 1152; // samples per mp3 frame

    for (let i = 0; i < samples; i += sampleBlockSize) {
      const leftChunk = leftPCM.subarray(i, i + sampleBlockSize);
      const rightChunk = rightPCM ? rightPCM.subarray(i, i + sampleBlockSize) : undefined;

      let mp3buf: Int8Array;
      if (rightChunk) {
        mp3buf = mp3encoder.encodeBuffer(leftChunk, rightChunk);
      } else {
        mp3buf = mp3encoder.encodeBuffer(leftChunk);
      }

      if (mp3buf.length > 0) {
        mp3Data.push(mp3buf);
      }
    }

    // Flush remaining data
    const mp3buf = mp3encoder.flush();
    if (mp3buf.length > 0) {
      mp3Data.push(mp3buf);
    }

    // Create blob from MP3 data
    const mp3Blob = new Blob(mp3Data as BlobPart[], { type: 'audio/mp3' });

    console.log(`✅ Audio converted: ${webmBlob.size} bytes (WebM) → ${mp3Blob.size} bytes (MP3)`);
    return mp3Blob;

  } catch (error) {
    console.error('❌ MP3 conversion failed:', error);
    // Fallback: return original blob if conversion fails
    return webmBlob;
  }
}

/**
 * Convert Float32Array to Int16Array (PCM 16-bit)
 */
function float32ToInt16(buffer: Float32Array): Int16Array {
  const int16 = new Int16Array(buffer.length);
  for (let i = 0; i < buffer.length; i++) {
    const s = Math.max(-1, Math.min(1, buffer[i]));
    int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return int16;
}

/**
 * Get audio duration in seconds from blob
 */
export async function getAudioDuration(blob: Blob): Promise<number> {
  try {
    const audioContext = new AudioContext();
    const arrayBuffer = await blob.arrayBuffer();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    return audioBuffer.duration;
  } catch (error) {
    console.error('Failed to get audio duration:', error);
    return 0;
  }
}
