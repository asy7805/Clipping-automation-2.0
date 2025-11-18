/**
 * FFmpeg.wasm Operations Utility
 * 
 * This module provides convenient wrapper functions for common FFmpeg.wasm operations.
 * All functions are designed to be non-blocking and provide progress feedback where applicable.
 */

import { FFmpeg } from '@ffmpeg/ffmpeg';
import { fetchFile } from '@ffmpeg/util';

export interface TrimOptions {
  startTime: number;
  endTime: number;
  copyCodec?: boolean; // Fast trim without re-encoding
}

export interface ConcatenateOptions {
  onProgress?: (progress: number) => void;
  format?: 'mp4' | 'mov' | 'webm';
}

export interface AudioGainOptions {
  gain: number; // Volume multiplier (1.0 = 100%, 2.0 = 200%, etc.)
  copyVideo?: boolean; // Don't re-encode video
}

export interface ThumbnailOptions {
  interval: number; // Seconds between thumbnails
  quality?: number; // 1-31, lower is better (default: 2)
  maxCount?: number; // Maximum number of thumbnails
}

export interface WaveformOptions {
  sampleRate?: number; // Audio sample rate (default: 8000)
  targetLength?: number; // Number of data points for visualization (default: 200)
}

/**
 * Trim a video file to a specific time range
 * This operation is very fast as it uses codec copy by default
 */
export async function trimVideo(
  ffmpeg: FFmpeg,
  file: File,
  options: TrimOptions
): Promise<Blob> {
  const inputName = `trim_input_${Date.now()}.mp4`;
  const outputName = `trim_output_${Date.now()}.mp4`;

  try {
    await ffmpeg.writeFile(inputName, await fetchFile(file));

    const args = [
      '-i', inputName,
      '-ss', options.startTime.toString(),
      '-to', options.endTime.toString(),
    ];

    if (options.copyCodec !== false) {
      args.push('-c', 'copy'); // Fast copy without re-encoding
    }

    args.push(outputName);

    await ffmpeg.exec(args);

    const data = await ffmpeg.readFile(outputName);
    const blob = new Blob([data], { type: 'video/mp4' });

    // Cleanup
    await ffmpeg.deleteFile(inputName);
    await ffmpeg.deleteFile(outputName);

    return blob;
  } catch (error) {
    console.error('Trim operation failed:', error);
    throw new Error(`Failed to trim video: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Concatenate multiple video clips into a single video
 */
export async function concatenateClips(
  ffmpeg: FFmpeg,
  files: File[],
  options: ConcatenateOptions = {}
): Promise<Blob> {
  const { onProgress, format = 'mp4' } = options;
  const outputName = `concat_output_${Date.now()}.${format}`;
  const inputFiles: string[] = [];

  try {
    // Write all input files
    for (let i = 0; i < files.length; i++) {
      const inputName = `concat_input_${i}_${Date.now()}.mp4`;
      await ffmpeg.writeFile(inputName, await fetchFile(files[i]));
      inputFiles.push(inputName);
      
      if (onProgress) {
        onProgress((i / files.length) * 50);
      }
    }

    // Create concat list file
    const concatList = inputFiles.map(name => `file '${name}'`).join('\n');
    const listFileName = `concat_list_${Date.now()}.txt`;
    await ffmpeg.writeFile(listFileName, concatList);

    // Execute concat
    await ffmpeg.exec([
      '-f', 'concat',
      '-safe', '0',
      '-i', listFileName,
      '-c', 'copy',
      outputName
    ]);

    if (onProgress) onProgress(100);

    const data = await ffmpeg.readFile(outputName);
    const blob = new Blob([data], { type: `video/${format}` });

    // Cleanup
    for (const inputFile of inputFiles) {
      await ffmpeg.deleteFile(inputFile);
    }
    await ffmpeg.deleteFile(listFileName);
    await ffmpeg.deleteFile(outputName);

    return blob;
  } catch (error) {
    console.error('Concatenate operation failed:', error);
    throw new Error(`Failed to concatenate clips: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Adjust audio volume/gain of a video
 */
export async function adjustAudioGain(
  ffmpeg: FFmpeg,
  file: File,
  options: AudioGainOptions
): Promise<Blob> {
  const inputName = `audio_input_${Date.now()}.mp4`;
  const outputName = `audio_output_${Date.now()}.mp4`;

  try {
    await ffmpeg.writeFile(inputName, await fetchFile(file));

    const args = [
      '-i', inputName,
      '-filter:a', `volume=${options.gain}`,
    ];

    if (options.copyVideo !== false) {
      args.push('-c:v', 'copy'); // Don't re-encode video
    }

    args.push(outputName);

    await ffmpeg.exec(args);

    const data = await ffmpeg.readFile(outputName);
    const blob = new Blob([data], { type: 'video/mp4' });

    // Cleanup
    await ffmpeg.deleteFile(inputName);
    await ffmpeg.deleteFile(outputName);

    return blob;
  } catch (error) {
    console.error('Audio gain adjustment failed:', error);
    throw new Error(`Failed to adjust audio gain: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Extract thumbnail images from a video at regular intervals
 */
export async function extractThumbnails(
  ffmpeg: FFmpeg,
  file: File,
  options: ThumbnailOptions
): Promise<string[]> {
  const { interval, quality = 2, maxCount } = options;
  const inputName = `thumb_input_${Date.now()}.mp4`;
  const timestamp = Date.now();

  try {
    await ffmpeg.writeFile(inputName, await fetchFile(file));

    const args = [
      '-i', inputName,
      '-vf', `fps=1/${interval}`,
      '-q:v', quality.toString(),
    ];

    if (maxCount) {
      args.push('-frames:v', maxCount.toString());
    }

    args.push(`thumb_${timestamp}_%03d.jpg`);

    await ffmpeg.exec(args);

    // Collect all generated thumbnails
    const thumbnails: string[] = [];
    let frameIndex = 1;

    while (true) {
      try {
        const frameName = `thumb_${timestamp}_${frameIndex.toString().padStart(3, '0')}.jpg`;
        const data = await ffmpeg.readFile(frameName);
        const blob = new Blob([data], { type: 'image/jpeg' });
        const url = URL.createObjectURL(blob);
        thumbnails.push(url);
        await ffmpeg.deleteFile(frameName);
        frameIndex++;

        if (maxCount && frameIndex > maxCount) break;
      } catch {
        break; // No more frames
      }
    }

    // Cleanup
    await ffmpeg.deleteFile(inputName);

    return thumbnails;
  } catch (error) {
    console.error('Thumbnail extraction failed:', error);
    throw new Error(`Failed to extract thumbnails: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Extract audio waveform data for visualization
 * Returns normalized amplitude values (0-1) for rendering waveforms
 */
export async function extractWaveform(
  ffmpeg: FFmpeg,
  file: File,
  options: WaveformOptions = {}
): Promise<number[]> {
  const { sampleRate = 8000, targetLength = 200 } = options;
  const inputName = `waveform_input_${Date.now()}.mp4`;
  const outputName = `waveform_output_${Date.now()}.wav`;

  try {
    await ffmpeg.writeFile(inputName, await fetchFile(file));

    // Extract audio as WAV
    await ffmpeg.exec([
      '-i', inputName,
      '-vn', // No video
      '-acodec', 'pcm_s16le',
      '-ar', sampleRate.toString(),
      '-ac', '1', // Mono
      outputName
    ]);

    // Read and parse WAV file
    const data = await ffmpeg.readFile(outputName);
    const arrayBuffer = data.buffer;
    const dataView = new DataView(arrayBuffer);
    const samples: number[] = [];

    // Skip WAV header (44 bytes) and read samples
    for (let i = 44; i < dataView.byteLength; i += 2) {
      const sample = dataView.getInt16(i, true);
      samples.push(Math.abs(sample) / 32768); // Normalize to 0-1
    }

    // Downsample to target length
    const downsampled: number[] = [];
    const chunkSize = Math.floor(samples.length / targetLength);

    for (let i = 0; i < targetLength; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, samples.length);
      const chunk = samples.slice(start, end);
      
      if (chunk.length > 0) {
        const max = Math.max(...chunk); // Use peak amplitude for better visualization
        downsampled.push(max);
      }
    }

    // Cleanup
    await ffmpeg.deleteFile(inputName);
    await ffmpeg.deleteFile(outputName);

    return downsampled;
  } catch (error) {
    console.error('Waveform extraction failed:', error);
    throw new Error(`Failed to extract waveform: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Get video metadata (duration, resolution, etc.)
 */
export async function getVideoMetadata(
  ffmpeg: FFmpeg,
  file: File
): Promise<{ duration: number; width: number; height: number }> {
  // This is a placeholder - FFmpeg.wasm doesn't directly provide metadata extraction
  // In practice, you'd use the browser's HTMLVideoElement for this
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    video.preload = 'metadata';

    video.onloadedmetadata = () => {
      resolve({
        duration: video.duration,
        width: video.videoWidth,
        height: video.videoHeight,
      });
      URL.revokeObjectURL(video.src);
    };

    video.onerror = () => {
      reject(new Error('Failed to load video metadata'));
      URL.revokeObjectURL(video.src);
    };

    video.src = URL.createObjectURL(file);
  });
}

/**
 * Convert blob to base64 data URL (useful for caching)
 */
export function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Create a video element from a blob for preview
 */
export function createVideoElement(blob: Blob): HTMLVideoElement {
  const video = document.createElement('video');
  video.src = URL.createObjectURL(blob);
  video.controls = true;
  return video;
}









