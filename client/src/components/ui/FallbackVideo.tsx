import { useRef, useEffect, CSSProperties } from 'react';

export interface FallbackVideoProps {
  src: string;
  isPlaying: boolean;
  onEnded?: () => void;
  onTimeUpdate?: (currentTime: number) => void;
}

export function FallbackVideo({ src, isPlaying, onEnded, onTimeUpdate }: FallbackVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying) {
      video.play().catch(() => {
        /* autoplay may be blocked by browser policy */
      });
    } else {
      video.pause();
    }
  }, [isPlaying]);

  const containerStyle: CSSProperties = {
    position: 'absolute',
    inset: 0,
    zIndex: 10,
    backgroundColor: '#000',
  };

  const videoStyle: CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  };

  return (
    <div style={containerStyle} data-testid="fallback-video">
      <video
        ref={videoRef}
        src={src}
        style={videoStyle}
        playsInline
        muted
        onEnded={onEnded}
        onTimeUpdate={() => {
          if (onTimeUpdate && videoRef.current) {
            onTimeUpdate(videoRef.current.currentTime);
          }
        }}
      />
    </div>
  );
}
