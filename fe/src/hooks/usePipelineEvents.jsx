import React, { useState, useEffect, createContext, useContext } from 'react';

const PipelineEventsContext = createContext({ events: [], isConnected: false });

export function PipelineEventsProvider({ children, url = 'wss://dev-be-y3xjsd-eb65f5-18-207-163-209.sslip.io/api/v1/ws/events' }) {
  const [events, setEvents] = useState([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    let ws = null;
    let reconnectTimeout = null;
    let isIntentionalClose = false;

    const connect = () => {
      ws = new WebSocket(url);

      ws.onopen = () => {
        setIsConnected(true);
        console.log('Connected to pipeline events');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setEvents((prev) => [...prev, data]);
        } catch (e) {
          console.error('Failed to parse WebSocket message', e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (!isIntentionalClose) {
          console.log('Disconnected from pipeline events. Reconnecting...');
          reconnectTimeout = setTimeout(connect, 3000);
        }
      };

      ws.onerror = (err) => {
        if (!isIntentionalClose) {
          console.error('WebSocket error:', err);
        }
        ws.close();
      };
    };

    connect();

    return () => {
      isIntentionalClose = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) {
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close();
        }
      }
    };
  }, [url]);

  return (
    <PipelineEventsContext.Provider value={{ events, isConnected }}>
      {children}
    </PipelineEventsContext.Provider>
  );
}

export function usePipelineEvents() {
  return useContext(PipelineEventsContext);
}
