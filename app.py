from flask import Flask, render_template, request, redirect, send_file, url_for
import sqlite3
from datetime import datetime
import pandas as pd
import io

app = Flask(__name__)

# ------------------------------
# BASE DE DATOS
# ------------------------------
def crear_tablas():
    conn = sqlite3.connect("negocio.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            cantidad REAL,
            precio REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            cliente TEXT,
            productos TEXT,
            total REAL,
            estado_pago TEXT,
            fecha_pago TEXT
        )
    """)

    conn.commit()
    conn.close()

crear_tablas()

# ------------------------------
# FUNCIONES AUXILIARES
# ------------------------------
def obtener_productos():
    conn = sqlite3.connect("negocio.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos")
    datos = cursor.fetchall()
    conn.close()
    return datos

def obtener_ventas():
    conn = sqlite3.connect("negocio.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ventas ORDER BY fecha DESC")
    datos = cursor.fetchall()
    conn.close()
    return datos

def obtener_venta_por_cliente(cliente):
    conn = sqlite3.connect("negocio.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM ventas
        WHERE cliente LIKE ?
        ORDER ORDER BY fecha DESC
    """, ('%' + cliente + '%',))
    datos = cursor.fetchall()
    conn.close()
    return datos

def obtener_producto(id_producto):
    conn = sqlite3.connect("negocio.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos WHERE id=?", (id_producto,))
    dato = cursor.fetchone()
    conn.close()
    return dato

# ------------------------------
# RUTAS PRINCIPALES
# ------------------------------
@app.route("/")
def inicio():
    return render_template("index.html",
                           productos=obtener_productos(),
                           ventas=obtener_ventas())

# ------------------------------
# INVENTARIO
# ------------------------------
@app.route("/agregar", methods=["POST"])
def agregar():
    nombre = request.form["nombre"].strip()
    cantidad = float(request.form["cantidad"])
    precio = float(request.form["precio"])

    conn = sqlite3.connect("negocio.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO productos (nombre, cantidad, precio) VALUES (?, ?, ?)",
                   (nombre, cantidad, precio))
    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/eliminar/<int:id>")
def eliminar(id):
    conn = sqlite3.connect("negocio.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

# EDITAR PRODUCTO
@app.route("/editar_producto/<int:id>", methods=["GET", "POST"])
def editar_producto(id):
    if request.method == "POST":
        cantidad = float(request.form["cantidad"])
        precio = float(request.form["precio"])

        conn = sqlite3.connect("negocio.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE productos
            SET cantidad=?, precio=?
            WHERE id=?
        """, (cantidad, precio, id))
        conn.commit()
        conn.close()
        return redirect("/")

    producto = obtener_producto(id)
    return render_template("editar_producto.html", producto=producto)

# ------------------------------
# REGISTRAR VENTA
# ------------------------------
@app.route("/venta", methods=["POST"])
def venta():
    cliente = request.form["cliente"].strip()
    ids = request.form.getlist("id_producto[]")
    cantidades = request.form.getlist("cantidad_vender[]")
    estado_pago = request.form["estado_pago"]
    fecha_pago = request.form.get("fecha_pago", "")

    if estado_pago == "Pendiente":
        fecha_pago = ""

    conn = sqlite3.connect("negocio.db")
    cursor = conn.cursor()

    lista_productos = []
    total = 0

    for i in range(len(ids)):
        if not cantidades[i] or cantidades[i].strip() == "":
            continue

        cantidad_vender = float(cantidades[i])

        cursor.execute("SELECT nombre, precio, cantidad FROM productos WHERE id=?", (ids[i],))
        fila = cursor.fetchone()
        if not fila:
            continue

        nombre, precio, stock = fila

        if stock <= 0 or cantidad_vender <= 0:
            continue

        if cantidad_vender > stock:
            cantidad_vender = stock

        nuevo_stock = stock - cantidad_vender
        cursor.execute("UPDATE productos SET cantidad=? WHERE id=?", (nuevo_stock, ids[i]))

        subtotal = precio * cantidad_vender
        total += subtotal

        lista_productos.append(f"{nombre} x{cantidad_vender}")

    if not lista_productos:
        conn.commit()
        conn.close()
        return redirect("/")

    productos_texto = ", ".join(lista_productos)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    cursor.execute("""
        INSERT INTO ventas (fecha, cliente, productos, total, estado_pago, fecha_pago)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (fecha, cliente, productos_texto, total, estado_pago, fecha_pago))

    conn.commit()
    conn.close()

    return redirect("/")

# ------------------------------
# MARCAR COMO PAGADO
# ------------------------------
@app.route("/marcar_pagado/<int:id>", methods=["POST"])
def marcar_pagado(id):
    fecha_pago = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = sqlite3.connect("negocio.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE ventas
        SET estado_pago='Pagado', fecha_pago=?
        WHERE id=?
    """, (fecha_pago, id))

    conn.commit()
    conn.close()

    return redirect("/")

# ------------------------------
# BUSCAR VENTAS POR CLIENTE
# ------------------------------
@app.route("/buscar_ventas")
def buscar_ventas():
    cliente = request.args.get("cliente", "").strip()
    ventas = obtener_venta_por_cliente(cliente)

    return render_template("index.html",
                           productos=obtener_productos(),
                           ventas=ventas,
                           cliente_busqueda=cliente)

# ------------------------------
# IMPRIMIR VENTAS
# ------------------------------
@app.route("/imprimir_ventas")
def imprimir_ventas():
    ventas = obtener_ventas()
    return render_template("imprimir_ventas.html", ventas=ventas)

# ------------------------------
# EXPORTAR HISTORIAL A EXCEL
# ------------------------------
@app.route("/exportar_excel_ventas")
def exportar_excel_ventas():
    ventas = obtener_ventas()
    df = pd.DataFrame(ventas, columns=["ID", "Fecha", "Cliente", "Productos", "Total", "Estado Pago", "Fecha Pago"])

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Ventas")

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="historial_ventas.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ------------------------------
# EXPORTAR INVENTARIO A EXCEL
# ------------------------------
@app.route("/exportar_excel_inventario")
def exportar_excel_inventario():
    productos = obtener_productos()
    df = pd.DataFrame(productos, columns=["ID", "Nombre", "Cantidad", "Precio"])

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Inventario")

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="inventario.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ------------------------------
# EJECUTAR
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)