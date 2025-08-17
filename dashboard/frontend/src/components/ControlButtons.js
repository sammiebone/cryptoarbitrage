function ControlButtons({ status }) {
    const handleStart = () => {
        console.log("Requesting to start bot...");
        fetch('/api/start', { method: 'POST' })
            .then(response => response.json())
            .then(data => console.log('Start response:', data))
            .catch(error => console.error('Error starting bot:', error));
    };

    const handleStop = () => {
        console.log("Requesting to stop bot...");
        fetch('/api/stop', { method: 'POST' })
            .then(response => response.json())
            .then(data => console.log('Stop response:', data))
            .catch(error => console.error('Error stopping bot:', error));
    };

    const buttonStyle = {
        padding: '10px 20px',
        margin: '5px',
        fontSize: '16px',
        cursor: 'pointer',
        border: '1px solid transparent',
        borderRadius: '5px',
        color: 'white',
        transition: 'opacity 0.2s ease',
    };

    const startButtonStyle = { ...buttonStyle, backgroundColor: '#28a745' };
    const stopButtonStyle = { ...buttonStyle, backgroundColor: '#dc3545' };

    return React.createElement('div', { style: { margin: '20px 0' } },
        React.createElement('button', {
            onClick: handleStart,
            style: { ...startButtonStyle, cursor: status === 'running' ? 'not-allowed' : 'pointer', opacity: status === 'running' ? 0.6 : 1 },
            disabled: status === 'running'
        }, 'Start Bot'),
        React.createElement('button', {
            onClick: handleStop,
            style: { ...stopButtonStyle, cursor: status !== 'running' ? 'not-allowed' : 'pointer', opacity: status !== 'running' ? 0.6 : 1 },
            disabled: status !== 'running'
        }, 'Stop Bot')
    );
}
