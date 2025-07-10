setInterval(() => {
    const event = new MouseEvent("mousemove", {
        bubbles: true,
        cancelable: true,
        clientX: 0,
        clientY: 0
    });
    document.dispatchEvent(event);
}, 1800000); // cada 30 minutos
