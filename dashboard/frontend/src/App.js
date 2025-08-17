import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import './App.css';
import StatusIndicator from './components/StatusIndicator';
import LogViewer from './components/LogViewer';
import ControlButtons from './components/ControlButtons';

// Connect to the socket server
const socket = io.connect('http://localhost:5000');

function App() {
  const [status, setStatus] = useState('unknown');
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    // Get initial status
    fetch('/api/status')
      .then((res) => res.json())
      .then((data) => setStatus(data.status));

    // Listen for status updates
    socket.on('status_update', (data) => {
      setStatus(data.status);
    });

    // Listen for log messages
    socket.on('log_message', (data) => {
      setLogs((prevLogs) => [...prevLogs, data.data]);
    });

    // Clean up the connection on component unmount
    return () => {
      socket.off('status_update');
      socket.off('log_message');
    };
  }, []);

  const handleStart = () => {
    fetch('/api/start', { method: 'POST' })
      .then((res) => res.json())
      .then((data) => console.log(data.message));
  };

  const handleStop = () => {
    fetch('/api/stop', { method: 'POST' })
      .then((res) => res.json())
      .then((data) => console.log(data.message));
  };

  return (
    <div className="App">
      <h1>Arbitrage Bot Dashboard</h1>
      <StatusIndicator status={status} />
      <ControlButtons status={status} onStart={handleStart} onStop={handleStop} />
      <LogViewer logs={logs} />
    </div>
  );
}

export default App;
