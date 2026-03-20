import { useCallback, useState } from "react";

export default function useShake<T extends string>() {
  const [shakeField, setShakeField] = useState<T | null>(null);

  const shake = useCallback((field: T) => {
    setShakeField(field);
    setTimeout(() => setShakeField(null), 500);
  }, []);

  const isShaking = useCallback((field: T) => shakeField === field, [shakeField]);

  return { shake, isShaking };
}
