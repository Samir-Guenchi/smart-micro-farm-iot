import { useEffect, useState } from "react";
import { type Forecast, getForecast } from "./forecast";

export function useForecast(lat: number | null, lon: number | null, enabled = true) {
  const [state, setState] = useState<{ forecast: Forecast | null; cached: boolean; error: boolean }>({ forecast: null, cached: false, error: false });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!enabled || lat === null || lon === null) return;
    let live = true;
    setState((s) => ({ ...s, error: false }));
    getForecast(lat, lon)
      .then(({ forecast, cached }) => live && setState({ forecast, cached, error: false }))
      .catch(() => live && setState((s) => ({ ...s, error: true })));
    return () => {
      live = false;
    };
  }, [lat, lon, enabled, attempt]);
  return { ...state, retry: () => setAttempt((n) => n + 1) };
}
