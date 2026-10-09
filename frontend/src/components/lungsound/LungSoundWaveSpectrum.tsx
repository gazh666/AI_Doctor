'use client';

import { useEffect, useRef } from 'react';

interface LungSoundWaveSpectrumProps {
  audioUrl: string | null;
}

/**
 * 呼吸音波形 + 频谱可视化。
 * 使用原生 Web Audio API 解码音频，Canvas 自绘，无第三方依赖。
 * - 波形图：时域峰值包络
 * - 频谱图：对中段采样做 FFT，绘制 0~4kHz 幅度谱（覆盖呼吸音主要频段）
 */
export function LungSoundWaveSpectrum({ audioUrl }: LungSoundWaveSpectrumProps) {
  const waveCanvasRef = useRef<HTMLCanvasElement>(null);
  const specCanvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!audioUrl) return;
    let cancelled = false;

    (async () => {
      try {
        const res = await fetch(audioUrl);
        const buf = await res.arrayBuffer();
        const AudioCtx =
          window.AudioContext ||
          (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        const ctx = new AudioCtx();
        const audioBuffer = await ctx.decodeAudioData(buf);
        if (cancelled) {
          void ctx.close();
          return;
        }
        drawWaveform(audioBuffer);
        drawSpectrum(audioBuffer);
        void ctx.close();
      } catch (e) {
        console.error('呼吸音可视化绘制失败：', e);
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioUrl]);

  function drawWaveform(buffer: AudioBuffer) {
    const canvas = waveCanvasRef.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    const c = canvas.getContext('2d');
    if (!c) return;
    c.scale(dpr, dpr);
    c.clearRect(0, 0, width, height);

    let data = buffer.getChannelData(0);
    // 单声道对齐：若有则取均值
    if (buffer.numberOfChannels > 1) {
      const right = buffer.getChannelData(1);
      const merged = new Float32Array(data.length);
      for (let i = 0; i < data.length; i++) {
        merged[i] = (data[i] + right[i]) / 2;
      }
      data = merged;
    }

    const steps = Math.min(2000, Math.floor(width));
    const block = Math.max(1, Math.floor(data.length / steps));
    const midY = height / 2;

    c.strokeStyle = '#3b82f6';
    c.lineWidth = 1.5;
    c.beginPath();
    for (let s = 0; s < steps; s++) {
      let peak = 0;
      const start = s * block;
      for (let j = 0; j < block; j++) {
        const v = Math.abs(data[start + j] || 0);
        if (v > peak) peak = v;
      }
      const x = (s / steps) * width;
      const y = midY - peak * midY * 0.95;
      if (s === 0) c.moveTo(x, y);
      else c.lineTo(x, y);
    }
    c.stroke();

    // 中线
    c.strokeStyle = '#e2e8f0';
    c.lineWidth = 1;
    c.setLineDash([3, 3]);
    c.beginPath();
    c.moveTo(0, midY);
    c.lineTo(width, midY);
    c.stroke();
    c.setLineDash([]);
  }

  function drawSpectrum(buffer: AudioBuffer) {
    const canvas = specCanvasRef.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    const c = canvas.getContext('2d');
    if (!c) return;
    c.scale(dpr, dpr);
    c.clearRect(0, 0, width, height);

    let data = buffer.getChannelData(0);
    if (buffer.numberOfChannels > 1) {
      const right = buffer.getChannelData(1);
      for (let i = 0; i < data.length; i++) data[i] = (data[i] + right[i]) / 2;
    }

    // 取中段 4096 点做 FFT（radix-2 要求 2 的幂）
    const fftSize = 4096;
    const offset = Math.max(0, Math.floor((data.length - fftSize) / 2));
    const re = new Float32Array(fftSize);
    const im = new Float32Array(fftSize);
    for (let i = 0; i < fftSize; i++) re[i] = data[offset + i] || 0;

    fft(re, im);

    const sampleRate = buffer.sampleRate;
    const maxFreq = Math.min(4000, sampleRate / 2); // 呼吸音主要频段
    const binWidth = sampleRate / fftSize;
    const maxBin = Math.min(re.length / 2, Math.ceil(maxFreq / binWidth));

    // 对数幅度，归一化到 0~1
    let magMax = 0;
    const mags = new Float32Array(maxBin);
    for (let i = 1; i < maxBin; i++) {
      const m = Math.sqrt(re[i] * re[i] + im[i] * im[i]);
      mags[i] = m;
      if (m > magMax) magMax = m;
    }
    if (magMax === 0) magMax = 1;

    const barW = width / maxBin;
    const gradTop = height * 0.9;
    c.fillStyle = '#10b981';
    for (let i = 0; i < maxBin; i++) {
      const norm = mags[i] / magMax;
      const h = Math.pow(norm, 0.6) * gradTop;
      c.fillRect(i * barW, height - h, Math.max(1, barW - 1), h);
    }

    // 频率刻度（0 / 1k / 2k / 3k / 4k Hz）
    c.fillStyle = '#94a3b8';
    c.font = '10px sans-serif';
    const ticks = [0, 1000, 2000, 3000, 4000];
    for (const f of ticks) {
      const x = (f / maxFreq) * width;
      c.fillText(`${f >= 1000 ? f / 1000 + 'k' : f}`, Math.min(x, width - 24), height - 2);
    }
  }

  return (
    <div className="space-y-3">
      <div>
        <div className="text-xs font-medium text-gray-600 mb-1">Waveform</div>
        <canvas
          ref={waveCanvasRef}
          className="w-full h-16 bg-slate-50 rounded-lg border border-slate-100"
        />
      </div>
      <div>
        <div className="text-xs font-medium text-gray-600 mb-1">Spectrum (0–4 kHz)</div>
        <canvas
          ref={specCanvasRef}
          className="w-full h-20 bg-slate-50 rounded-lg border border-slate-100"
        />
      </div>
    </div>
  );
}

/** 迭代 radix-2 FFT，原地计算。 */
function fft(re: Float32Array, im: Float32Array) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      [re[i], re[j]] = [re[j], re[i]];
      [im[i], im[j]] = [im[j], im[i]];
    }
  }

  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len;
    const wRe = Math.cos(ang);
    const wIm = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let curRe = 1;
      let curIm = 0;
      for (let k = 0; k < len / 2; k++) {
        const uRe = re[i + k];
        const uIm = im[i + k];
        const vRe = re[i + k + len / 2] * curRe - im[i + k + len / 2] * curIm;
        const vIm = re[i + k + len / 2] * curIm + im[i + k + len / 2] * curRe;
        re[i + k] = uRe + vRe;
        im[i + k] = uIm + vIm;
        re[i + k + len / 2] = uRe - vRe;
        im[i + k + len / 2] = uIm - vIm;
        const nextRe = curRe * wRe - curIm * wIm;
        curIm = curRe * wIm + curIm * wRe;
        curRe = nextRe;
      }
    }
  }
}