
import { useState, useEffect, useCallback } from "react";
import { fetchServices } from "../lib/api";

export function useServices() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;

    setLoading(true);
    setError(null);

    fetchServices()
      .then((result) => {
        if (active) setData(result);
      })
      .catch((err) => {
        if (active) {
          setData(null);
          setError(err.message || "Unable to load services");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [attempt]);

  const retry = useCallback(() => {
    setAttempt((previous) => previous + 1);
  }, []);

  return { data, loading, error, retry };
}
