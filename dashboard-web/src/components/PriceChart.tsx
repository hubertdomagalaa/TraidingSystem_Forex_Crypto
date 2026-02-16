'use client';

import { useEffect, useRef, useState } from 'react';

interface PriceChartProps {
  entry: number;
  stopLoss: number;
  takeProfit: number;
  direction: 'LONG' | 'SHORT' | 'HOLD';
}

function generateMockPriceData(entry: number, count: number = 50): number[] {
  const data: number[] = [];
  let price = entry * 0.998;
  const volatility = entry * 0.001;

  for (let i = 0; i < count; i++) {
    const change = (Math.random() - 0.48) * volatility;
    price += change;
    data.push(price);
  }
  return data;
}

export function PriceChart({ entry, stopLoss, takeProfit, direction }: PriceChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [priceData, setPriceData] = useState<number[]>([]);
  const [isAnimating, setIsAnimating] = useState(true);

  useEffect(() => {
    if (entry > 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPriceData(generateMockPriceData(entry));
    }
  }, [entry]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || priceData.length === 0 || entry === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    const allPrices = [...priceData, entry, stopLoss, takeProfit];
    const minPrice = Math.min(...allPrices) * 0.9995;
    const maxPrice = Math.max(...allPrices) * 1.0005;
    const priceRange = maxPrice - minPrice;

    const priceToY = (price: number) => height - ((price - minPrice) / priceRange) * height;

    const slY = priceToY(stopLoss);
    const tpY = priceToY(takeProfit);
    const entryY = priceToY(entry);

    ctx.fillStyle = 'rgba(255, 0, 85, 0.1)';
    if (direction === 'LONG') {
      ctx.fillRect(0, slY, width, height - slY);
    } else {
      ctx.fillRect(0, 0, width, slY);
    }

    ctx.fillStyle = 'rgba(0, 255, 157, 0.1)';
    if (direction === 'LONG') {
      ctx.fillRect(0, 0, width, tpY);
    } else {
      ctx.fillRect(0, tpY, width, height - tpY);
    }

    const drawLevel = (y: number, color: string, levelLabel: string, price: number) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = color;
      ctx.font = '10px monospace';
      ctx.fillText(`${levelLabel}: ${price.toFixed(4)}`, 5, y - 3);
    };

    drawLevel(slY, '#ff0055', 'SL', stopLoss);
    drawLevel(tpY, '#00ff9d', 'TP', takeProfit);
    drawLevel(entryY, '#ffffff', 'Entry', entry);

    const gradient = ctx.createLinearGradient(0, 0, width, 0);
    gradient.addColorStop(0, 'rgba(0, 180, 216, 0.3)');
    gradient.addColorStop(1, 'rgba(0, 180, 216, 1)');

    ctx.strokeStyle = gradient;
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.beginPath();

    const animatedLength = isAnimating ? Math.max(2, Math.floor(priceData.length * 0.7)) : priceData.length;

    priceData.slice(0, animatedLength).forEach((price, i) => {
      const x = (i / (priceData.length - 1)) * width;
      const y = priceToY(price);
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });

    ctx.stroke();
    ctx.strokeStyle = 'rgba(0, 180, 216, 0.3)';
    ctx.lineWidth = 6;
    ctx.stroke();

    const lastPrice = priceData[animatedLength - 1];
    const lastX = ((animatedLength - 1) / (priceData.length - 1)) * width;
    const lastY = priceToY(lastPrice);

    ctx.beginPath();
    ctx.arc(lastX, lastY, 8, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(0, 180, 216, 0.3)';
    ctx.fill();

    ctx.beginPath();
    ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
    ctx.fillStyle = '#00b4d8';
    ctx.fill();
  }, [priceData, entry, stopLoss, takeProfit, direction, isAnimating]);

  useEffect(() => {
    if (priceData.length > 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIsAnimating(true);
      const timer = setTimeout(() => setIsAnimating(false), 1000);
      return () => clearTimeout(timer);
    }
  }, [priceData]);

  if (entry === 0) {
    return (
      <div className="glass-card-static p-4">
        <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-4">Price Chart</h3>
        <div className="h-40 flex items-center justify-center border border-dashed border-[var(--border-glass)] rounded-lg">
          <div className="text-center text-[var(--text-muted)]">
            <span className="text-sm">Waiting for signal...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card-static p-4">
      <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-4">Price Levels</h3>

      <div className="relative h-40 rounded-lg overflow-hidden bg-[var(--bg-secondary)]">
        <canvas ref={canvasRef} width={300} height={160} className="w-full h-full" />
      </div>

      <div className="mt-3 flex justify-between text-xs">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-[var(--accent-red)] rounded" />
          <span className="text-[var(--accent-red)] font-mono">SL: {stopLoss.toFixed(4)}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-white rounded" />
          <span className="text-white font-mono">Entry: {entry.toFixed(4)}</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-[var(--accent-green)] rounded" />
          <span className="text-[var(--accent-green)] font-mono">TP: {takeProfit.toFixed(4)}</span>
        </span>
      </div>
    </div>
  );
}
