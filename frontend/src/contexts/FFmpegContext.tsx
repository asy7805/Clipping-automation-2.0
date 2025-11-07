import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { FFmpeg } from '@ffmpeg/ffmpeg';
import { fetchFile, toBlobURL } from '@ffmpeg/util';

interface FFmpegContextType {
  ffmpeg: FFmpeg | null;
  isLoaded: boolean;
  isLoading: boolean;
  loadProgress: number;
  error: string | null;
  isAvailable: boolean;
  loadFFmpeg: () => Promise<void>;
  trimVideo: (file: File, startTime: number, endTime: number) => Promise<string>;
  concatenateClips: (files: File[], onProgress?: (progress: number) => void) => Promise<string>;
  adjustAudioGain: (file: File, gain: number) => Promise<string>;
  extractThumbnails: (file: File, interval: number) => Promise<string[]>;
  extractWaveform: (file: File) => Promise<number[]>;
}

const FFmpegContext = createContext<FFmpegContextType | null>(null);

export const useFFmpeg = () => {
  const context = useContext(FFmpegContext);
  if (!context) {
    throw new Error('useFFmpeg must be used within FFmpegProvider');
  }
  return context;
};

export const FFmpegProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadProgress, setLoadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isAvailable, setIsAvailable] = useState(true);
  const ffmpegRef = useRef<FFmpeg | null>(null);

  const loadFFmpeg = useCallback(async () => {
    if (ffmpegRef.current && isLoaded) return;
    if (isLoading) return;

    setIsLoading(true);
    setError(null);
    
    try {
      const ffmpeg = new FFmpeg();
      
      ffmpeg.on('log', ({ message }) => {
        console.log('[FFmpeg]', message);
      });

      ffmpeg.on('progress', ({ progress }) => {
        setLoadProgress(Math.round(progress * 100));
      });

      // Load FFmpeg with fallback CDNs
      const cdnUrls = [
        'https://unpkg.com/@ffmpeg/core@0.12.6/dist/esm',
        'https://cdn.jsdelivr.net/npm/@ffmpeg/core@0.12.6/dist/esm',
        'https://cdnjs.cloudflare.com/ajax/libs/@ffmpeg/core/0.12.6/dist/esm'
      ];

      let loaded = false;
      for (const baseURL of cdnUrls) {
        try {
          console.log(`Attempting to load FFmpeg from: ${baseURL}`);
          await ffmpeg.load({
            coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
            wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
          });
          loaded = true;
          console.log(`Successfully loaded FFmpeg from: ${baseURL}`);
          break;
        } catch (err) {
          console.warn(`Failed to load from ${baseURL}:`, err);
          continue;
        }
      }

      if (!loaded) {
        throw new Error('Failed to load FFmpeg from all CDN sources. Please check your internet connection.');
      }

      ffmpegRef.current = ffmpeg;
      setIsLoaded(true);
      setLoadProgress(100);
    } catch (err) {
      console.error('Failed to load FFmpeg:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to load FFmpeg';
      setError(errorMessage);
      setIsAvailable(false);
      
      // Show user-friendly error
      console.warn('FFmpeg.wasm failed to load. Client-side operations will be disabled.');
      console.warn('The editor will still work with server-side processing only.');
    } finally {
      setIsLoading(false);
    }
  }, [isLoaded, isLoading]);

  // Trim video operation
  const trimVideo = useCallback(async (file: File, startTime: number, endTime: number): Promise<string> => {
    if (!ffmpegRef.current || !isLoaded) {
      throw new Error('FFmpeg.wasm not available. Please use server-side processing.');
    }

    const ffmpeg = ffmpegRef.current;
    const inputName = 'input.mp4';
    const outputName = 'output.mp4';

    try {
      // Write input file
      await ffmpeg.writeFile(inputName, await fetchFile(file));

      // Run trim command (fast, no re-encoding)
      await ffmpeg.exec([
        '-i', inputName,
        '-ss', startTime.toString(),
        '-to', endTime.toString(),
        '-c', 'copy', // Copy codec for speed
        outputName
      ]);

      // Read output file
      const data = await ffmpeg.readFile(outputName);
      const blob = new Blob([data], { type: 'video/mp4' });
      const url = URL.createObjectURL(blob);

      // Cleanup
      await ffmpeg.deleteFile(inputName);
      await ffmpeg.deleteFile(outputName);

      return url;
    } catch (err) {
      console.error('Trim operation failed:', err);
      throw err;
    }
  }, [isLoaded]);

  // Concatenate clips operation
  const concatenateClips = useCallback(async (
    files: File[], 
    onProgress?: (progress: number) => void
  ): Promise<string> => {
    if (!ffmpegRef.current || !isLoaded) {
      throw new Error('FFmpeg.wasm not available. Please use server-side processing.');
    }

    const ffmpeg = ffmpegRef.current;
    const outputName = 'output.mp4';

    try {
      // Write all input files
      for (let i = 0; i < files.length; i++) {
        await ffmpeg.writeFile(`input${i}.mp4`, await fetchFile(files[i]));
        if (onProgress) onProgress((i / files.length) * 50);
      }

      // Create concat file list
      const concatList = files.map((_, i) => `file 'input${i}.mp4'`).join('\n');
      await ffmpeg.writeFile('concat.txt', concatList);

      // Run concat command
      await ffmpeg.exec([
        '-f', 'concat',
        '-safe', '0',
        '-i', 'concat.txt',
        '-c', 'copy',
        outputName
      ]);

      if (onProgress) onProgress(100);

      // Read output file
      const data = await ffmpeg.readFile(outputName);
      const blob = new Blob([data], { type: 'video/mp4' });
      const url = URL.createObjectURL(blob);

      // Cleanup
      for (let i = 0; i < files.length; i++) {
        await ffmpeg.deleteFile(`input${i}.mp4`);
      }
      await ffmpeg.deleteFile('concat.txt');
      await ffmpeg.deleteFile(outputName);

      return url;
    } catch (err) {
      console.error('Concatenate operation failed:', err);
      throw err;
    }
  }, [isLoaded]);

  // Adjust audio gain operation
  const adjustAudioGain = useCallback(async (file: File, gain: number): Promise<string> => {
    if (!ffmpegRef.current || !isLoaded) {
      throw new Error('FFmpeg.wasm not available. Please use server-side processing.');
    }

    const ffmpeg = ffmpegRef.current;
    const inputName = 'input.mp4';
    const outputName = 'output.mp4';

    try {
      await ffmpeg.writeFile(inputName, await fetchFile(file));

      // Run audio gain adjustment
      await ffmpeg.exec([
        '-i', inputName,
        '-filter:a', `volume=${gain}`,
        '-c:v', 'copy', // Don't re-encode video
        outputName
      ]);

      const data = await ffmpeg.readFile(outputName);
      const blob = new Blob([data], { type: 'video/mp4' });
      const url = URL.createObjectURL(blob);

      // Cleanup
      await ffmpeg.deleteFile(inputName);
      await ffmpeg.deleteFile(outputName);

      return url;
    } catch (err) {
      console.error('Audio gain adjustment failed:', err);
      throw err;
    }
  }, [isLoaded]);

  // Extract thumbnails operation
  const extractThumbnails = useCallback(async (file: File, interval: number): Promise<string[]> => {
    if (!ffmpegRef.current || !isLoaded) {
      throw new Error('FFmpeg.wasm not available. Please use server-side processing.');
    }

    const ffmpeg = ffmpegRef.current;
    const inputName = 'input.mp4';

    try {
      await ffmpeg.writeFile(inputName, await fetchFile(file));

      // Extract frames at interval
      await ffmpeg.exec([
        '-i', inputName,
        '-vf', `fps=1/${interval}`,
        '-q:v', '2', // Quality
        'thumb_%03d.jpg'
      ]);

      // Read all generated thumbnails
      const thumbnails: string[] = [];
      let frameIndex = 1;
      
      while (true) {
        try {
          const frameName = `thumb_${frameIndex.toString().padStart(3, '0')}.jpg`;
          const data = await ffmpeg.readFile(frameName);
          const blob = new Blob([data], { type: 'image/jpeg' });
          const url = URL.createObjectURL(blob);
          thumbnails.push(url);
          await ffmpeg.deleteFile(frameName);
          frameIndex++;
        } catch {
          break; // No more frames
        }
      }

      // Cleanup
      await ffmpeg.deleteFile(inputName);

      return thumbnails;
    } catch (err) {
      console.error('Thumbnail extraction failed:', err);
      throw err;
    }
  }, [isLoaded]);

  // Extract waveform data operation
  const extractWaveform = useCallback(async (file: File): Promise<number[]> => {
    if (!ffmpegRef.current || !isLoaded) {
      throw new Error('FFmpeg.wasm not available. Please use server-side processing.');
    }

    const ffmpeg = ffmpegRef.current;
    const inputName = 'input.mp4';
    const outputName = 'output.wav';

    try {
      await ffmpeg.writeFile(inputName, await fetchFile(file));

      // Extract audio as WAV
      await ffmpeg.exec([
        '-i', inputName,
        '-vn', // No video
        '-acodec', 'pcm_s16le',
        '-ar', '8000', // 8kHz sample rate for faster processing
        '-ac', '1', // Mono
        outputName
      ]);

      // Read WAV file
      const data = await ffmpeg.readFile(outputName);
      
      // Parse WAV data (simplified)
      const arrayBuffer = data.buffer;
      const dataView = new DataView(arrayBuffer);
      const samples: number[] = [];
      
      // Skip WAV header (44 bytes) and read samples
      for (let i = 44; i < dataView.byteLength; i += 2) {
        const sample = dataView.getInt16(i, true);
        samples.push(Math.abs(sample) / 32768); // Normalize to 0-1
      }

      // Downsample to ~200 points for visualization
      const targetLength = 200;
      const downsampled: number[] = [];
      const chunkSize = Math.floor(samples.length / targetLength);
      
      for (let i = 0; i < targetLength; i++) {
        const start = i * chunkSize;
        const end = start + chunkSize;
        const chunk = samples.slice(start, end);
        const avg = chunk.reduce((sum, val) => sum + val, 0) / chunk.length;
        downsampled.push(avg);
      }

      // Cleanup
      await ffmpeg.deleteFile(inputName);
      await ffmpeg.deleteFile(outputName);

      return downsampled;
    } catch (err) {
      console.error('Waveform extraction failed:', err);
      throw err;
    }
  }, [isLoaded]);

  return (
    <FFmpegContext.Provider
      value={{
        ffmpeg: ffmpegRef.current,
        isLoaded,
        isLoading,
        loadProgress,
        error,
        isAvailable,
        loadFFmpeg,
        trimVideo,
        concatenateClips,
        adjustAudioGain,
        extractThumbnails,
        extractWaveform,
      }}
    >
      {children}
    </FFmpegContext.Provider>
  );
};

