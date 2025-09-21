import { useState } from "react";

type ImageLoaderProps = {
  src: string | null,
  alt?: string,
  fallback?: string
}

export default function ImageLoader({ src, alt, fallback }: ImageLoaderProps) {
  const [imgError, setImgError] = useState(false);

  if (src && !imgError) {
    return (
      <img src={src} alt={alt} loading="lazy" onError={() => setImgError(true)} />
    );
  } else {
    return (
      <div className="image-fallback">
        { fallback || "?" }
      </div>
    );
  }
}