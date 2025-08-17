function LogViewer({ logs }) {
    const containerStyles = {
        backgroundColor: '#222',
        color: '#eee',
        fontFamily: 'monospace',
        padding: '15px',
        margin: '10px 0',
        borderRadius: '5px',
        height: '500px',
        overflowY: 'scroll',
        display: 'flex',
        flexDirection: 'column-reverse', // To keep the view scrolled to the bottom
    };

    const preStyles = {
        margin: 0,
        whiteSpace: 'pre-wrap', // To wrap long lines
        wordBreak: 'break-all',
    };

    // We use createElement here to avoid needing a JSX transpiler for this step.
    return React.createElement(
        'div',
        { style: containerStyles },
        React.createElement(
            'pre',
            { style: preStyles },
            logs.join('\n')
        )
    );
}
