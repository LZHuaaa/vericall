import React, { useEffect, useRef } from 'react';
import { AudioVisualizerProps } from '../types';

const AudioVisualizer: React.FC<AudioVisualizerProps> = ({ isSpeaking, volume }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let currentHeight = 0;

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;

      // Smooth volume transition
      const targetHeight = Math.min(volume * 500, 150); 
      currentHeight += (targetHeight - currentHeight) * 0.2;
      
      const safeHeight = Math.max(currentHeight, 5); // Minimum size

      // Draw energetic circles
      ctx.beginPath();
      ctx.arc(centerX, centerY, safeHeight + 20, 0, 2 * Math.PI);
      ctx.strokeStyle = '#D97706'; // Amber 600
      ctx.lineWidth = 3;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(centerX, centerY, safeHeight, 0, 2 * Math.PI);
      ctx.fillStyle = '#F59E0B'; // Amber 500
      ctx.fill();

      // Inner glow
      if (volume > 0.05) {
          ctx.beginPath();
          ctx.arc(centerX, centerY, safeHeight * 0.6, 0, 2 * Math.PI);
          ctx.fillStyle = '#FEF3C7'; // Amber 100
          ctx.fill();
      }

      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => cancelAnimationFrame(animationFrameId);
  }, [volume]);

  return (
    <div className="relative w-48 h-48 mx-auto flex items-center justify-center">
        <canvas ref={canvasRef} width={200} height={200} className="absolute inset-0" />
        {!isSpeaking && volume < 0.01 && (
            <div className="absolute inset-0 flex items-center justify-center opacity-30">
               <span className="text-4xl">💤</span>
            </div>
        )}
    </div>
  );
};

export default AudioVisualizer;
