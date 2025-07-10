// Simula movimiento del mouse cada 15 minutos
setInterval(() => {
    const event = new MouseEvent("mousemove", {
        bubbles: true,
        cancelable: true,
        clientX: 0,
        clientY: 0
    });
    document.dispatchEvent(event);
}, 900000); // 15 minutos en milisegundos

// Simula una pulsación de tecla invisible cada 15 minutos
setInterval(() => {
    const event = new KeyboardEvent("keydown", {
        bubbles: true,
        cancelable: true,
        key: "Shift"
    });
    document.dispatchEvent(event);
}, 900000); // 15 minutos en milisegundos
