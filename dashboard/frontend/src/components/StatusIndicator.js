function StatusIndicator({ status }) {
    const styles = {
        padding: '10px 15px',
        borderRadius: '5px',
        color: 'white',
        fontWeight: 'bold',
        textAlign: 'center',
        textTransform: 'uppercase',
        margin: '10px 0',
        transition: 'background-color 0.3s ease',
    };

    let backgroundColor;
    switch (status) {
        case 'running':
            backgroundColor = '#28a745'; // Green
            break;
        case 'stopped':
            backgroundColor = '#6c757d'; // Gray
            break;
        case 'error':
            backgroundColor = '#dc3545'; // Red
            break;
        default:
            backgroundColor = '#ffc107'; // Yellow for unknown/disconnected
    }

    styles.backgroundColor = backgroundColor;

    return React.createElement(
        'div',
        { style: styles },
        `Status: ${status}`
    );
}
