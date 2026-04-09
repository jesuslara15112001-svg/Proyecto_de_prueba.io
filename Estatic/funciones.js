function agregarFila() {
    const contenedor = document.getElementById('lista-productos-venta');
    const fila = document.querySelector('.producto-fila').cloneNode(true);
    fila.querySelectorAll('input').forEach(i => i.value = '');
    contenedor.appendChild(fila);
}
