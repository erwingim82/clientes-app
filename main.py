import flet as ft
import sqlite3
from datetime import datetime
import urllib.parse  # Librería para dar formato web a los mensajes de WhatsApp/Correo

def main(page: ft.Page):
    # 1. Configuración de la ventana y tema
    page.window_width = 380
    page.window_height = 680
    page.title = "Credi-Personas"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.colors.BLUE_GREY_900

    # ==========================================
    # INICIALIZAR BASE DE DATOS (MIGRACIÓN V1.5)
    # ==========================================
    def inicializar_bd():
        conexion = sqlite3.connect("fiados.db")
        cursor = conexion.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, deuda REAL)")
        
        # Intentamos agregar las nuevas columnas si la app viene de versiones anteriores
        try:
            cursor.execute("ALTER TABLE clientes ADD COLUMN telefono TEXT")
        except:
            pass # Si ya existe, simplemente lo ignora
            
        try:
            cursor.execute("ALTER TABLE clientes ADD COLUMN correo TEXT")
        except:
            pass

        cursor.execute('''CREATE TABLE IF NOT EXISTS transacciones (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            cliente_id INTEGER,
                            fecha TEXT,
                            hora TEXT,
                            tipo TEXT,
                            monto REAL
                          )''')
        conexion.commit()
        conexion.close()
        
    inicializar_bd()

    # ==========================================
    # MODO CLARO / OSCURO
    # ==========================================
    def cambiar_tema(e):
        if page.theme_mode == ft.ThemeMode.DARK:
            page.theme_mode = ft.ThemeMode.LIGHT
            page.bgcolor = ft.colors.BLUE_GREY_50
            boton_tema.icon = ft.icons.DARK_MODE
        else:
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = ft.colors.BLUE_GREY_900
            boton_tema.icon = ft.icons.LIGHT_MODE
        page.update()

    boton_tema = ft.IconButton(icon=ft.icons.LIGHT_MODE, on_click=cambiar_tema)

    # ==========================================
    # SISTEMA DE NOTIFICACIONES 
    # ==========================================
    def notificar(mensaje, color=ft.colors.GREEN_700):
        page.open(ft.SnackBar(ft.Text(mensaje, color=ft.colors.WHITE), bgcolor=color, duration=3000))

    # ==========================================
    # VENTANA EMERGENTE "ACERCA DE"
    # ==========================================
    def cerrar_acerca_de(e):
        page.close(dialogo_acerca)

    def abrir_acerca_de(e):
        page.open(dialogo_acerca)

    def enviar_correo_soporte(e):
        page.launch_url("mailto:myconsultingsca@gmail.com?subject=Sugerencias App Credi-Personas")

    dialogo_acerca = ft.AlertDialog(
        title=ft.Text("Acerca de", weight=ft.FontWeight.BOLD),
        content=ft.Column(
            [
                ft.Text("Credi-Personas\nVersión V1.5\n\nDesarrollado por: EIM", size=16, text_align=ft.TextAlign.CENTER),
                ft.Divider(color=ft.colors.TRANSPARENT),
                ft.TextButton(
                    content=ft.Row([ft.Icon(ft.icons.EMAIL, color=ft.colors.BLUE_400), ft.Text("Enviar sugerencias", color=ft.colors.BLUE_400)], alignment=ft.MainAxisAlignment.CENTER, tight=True),
                    on_click=enviar_correo_soporte
                )
            ],
            tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        actions=[ft.TextButton("Cerrar", on_click=cerrar_acerca_de)],
        actions_alignment=ft.MainAxisAlignment.CENTER
    )

    page.appbar = ft.AppBar(
        title=ft.Text("Credi-Personas", weight=ft.FontWeight.BOLD),
        center_title=True,
        bgcolor=ft.colors.SURFACE_VARIANT,
        elevation=5,
        actions=[boton_tema, ft.IconButton(ft.icons.INFO_OUTLINE, on_click=abrir_acerca_de)]
    )

    # ==========================================
    # VARIABLES GLOBALES DE OPERACIÓN
    # ==========================================
    cliente_seleccionado_id = None
    cliente_seleccionado_nombre = ""
    cliente_seleccionado_tlf = ""
    cliente_seleccionado_correo = ""
    cliente_seleccionado_deuda = 0.0

    # ==========================================
    # VENTANAS EMERGENTES (CRUD Y TRANSACCIONES)
    # ==========================================
    
    # --- A. Dialogo para Nuevo Cliente ---
    entrada_nombre = ft.TextField(label="Nombre completo", capitalization=ft.TextCapitalization.WORDS)
    # Nuevos campos
    entrada_telefono = ft.TextField(label="Teléfono (Ej: 584241234567)", keyboard_type=ft.KeyboardType.PHONE)
    entrada_correo = ft.TextField(label="Correo electrónico", keyboard_type=ft.KeyboardType.EMAIL)
    
    def cerrar_dialogo_nuevo(e):
        page.close(dialogo_nuevo)

    def guardar_nuevo_cliente(e):
        if entrada_nombre.value:
            conexion = sqlite3.connect("fiados.db")
            cursor = conexion.cursor()
            cursor.execute("INSERT INTO clientes (nombre, deuda, telefono, correo) VALUES (?, 0.0, ?, ?)", 
                           (entrada_nombre.value, entrada_telefono.value, entrada_correo.value))
            conexion.commit()
            conexion.close()
            
            nombre_guardado = entrada_nombre.value
            entrada_nombre.value = ""
            entrada_telefono.value = ""
            entrada_correo.value = ""
            page.close(dialogo_nuevo) 
            notificar(f"Cliente '{nombre_guardado}' registrado.", ft.colors.BLUE_700)
            cargar_datos()
        else:
            notificar("El nombre no puede estar vacío", ft.colors.RED_700)

    dialogo_nuevo = ft.AlertDialog(
        title=ft.Text("Nuevo Cliente"),
        content=ft.Column([entrada_nombre, entrada_telefono, entrada_correo], tight=True),
        actions=[ft.TextButton("Guardar", on_click=guardar_nuevo_cliente), ft.TextButton("Cancelar", on_click=cerrar_dialogo_nuevo)]
    )

    # --- B. Dialogo para Actualizar Deuda (CON CALENDARIO Y NOTIFICACIONES) ---
    entrada_monto = ft.TextField(label="Monto ($)", keyboard_type=ft.KeyboardType.NUMBER)
    
    opcion_notificacion = ft.Dropdown(
        label="Enviar Recibo por:",
        options=[
            ft.dropdown.Option("Ninguna"),
            ft.dropdown.Option("WhatsApp"),
            ft.dropdown.Option("Correo Electrónico"),
        ],
        value="Ninguna"
    )
    
    def cambiar_fecha(e):
        if selector_fecha.value:
            boton_fecha.text = selector_fecha.value.strftime("%d/%m/%Y")
            page.update()

    selector_fecha = ft.DatePicker(first_date=datetime(2020, 1, 1), last_date=datetime(2030, 12, 31), on_change=cambiar_fecha)

    boton_fecha = ft.OutlinedButton(
        text=datetime.now().strftime("%d/%m/%Y"),
        icon=ft.icons.CALENDAR_MONTH,
        on_click=lambda e: page.open(selector_fecha)
    )

    def cerrar_dialogo_deuda(e):
        page.close(dialogo_deuda)

    def procesar_deuda(operacion):
        try:
            monto = float(entrada_monto.value.replace(",", ".")) 
        except (ValueError, TypeError):
            notificar("Ingresa un monto numérico válido", ft.colors.RED_700)
            return
            
        fecha = boton_fecha.text
        hora = datetime.now().strftime("%I:%M %p")
            
        if operacion == "restar":
            monto_bd = -monto
            tipo_transaccion = "Abono"
            mensaje = f"Abono de ${monto:.2f} registrado"
            color_alerta = ft.colors.GREEN_700
        else:
            monto_bd = monto
            tipo_transaccion = "Crédito"
            mensaje = f"Crédito de ${monto:.2f} aplicado"
            color_alerta = ft.colors.RED_700
            
        # Calcular el nuevo saldo para enviarlo en el recibo
        saldo_final = cliente_seleccionado_deuda + monto_bd
        
        # Construir el texto del recibo
        texto_recibo = f"🧾 *RECIBO CREDI-PERSONAS*\nHola {cliente_seleccionado_nombre}, se ha registrado un {tipo_transaccion} de *${monto:.2f}* el {fecha} a las {hora}.\n\nTu saldo actualizado es de: *${saldo_final:.2f}*."
        texto_recibo_url = urllib.parse.quote(texto_recibo) # Codificar para web/WhatsApp

        conexion = sqlite3.connect("fiados.db")
        cursor = conexion.cursor()
        cursor.execute("UPDATE clientes SET deuda = deuda + ? WHERE id = ?", (monto_bd, cliente_seleccionado_id))
        cursor.execute("INSERT INTO transacciones (cliente_id, fecha, hora, tipo, monto) VALUES (?, ?, ?, ?, ?)", 
                       (cliente_seleccionado_id, fecha, hora, tipo_transaccion, monto))
        conexion.commit()
        conexion.close()
        
        entrada_monto.value = ""
        eleccion_notif = opcion_notificacion.value
        page.close(dialogo_deuda) 
        
        # Disparar las integraciones según lo que se seleccionó
        if eleccion_notif == "WhatsApp":
            if cliente_seleccionado_tlf:
                # Limpiar el teléfono de símbolos o espacios (por si escriben +58)
                tel_limpio = cliente_seleccionado_tlf.replace("+", "").replace(" ", "")
                page.launch_url(f"https://wa.me/{tel_limpio}?text={texto_recibo_url}")
                notificar("Abriendo WhatsApp...", color_alerta)
            else:
                notificar("El cliente no tiene teléfono guardado.", ft.colors.ORANGE_700)
                
        elif eleccion_notif == "Correo Electrónico":
            if cliente_seleccionado_correo:
                page.launch_url(f"mailto:{cliente_seleccionado_correo}?subject=Recibo de Operación&body={texto_recibo_url}")
                notificar("Abriendo Correo...", color_alerta)
            else:
                notificar("El cliente no tiene correo guardado.", ft.colors.ORANGE_700)
        else:
            notificar(mensaje, color_alerta)
            
        cargar_datos()

    contenido_deuda = ft.Column(
        [
            entrada_monto,
            ft.Row([ft.Text("Fecha:", weight=ft.FontWeight.W_500), boton_fecha], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=1),
            opcion_notificacion
        ],
        tight=True
    )

    dialogo_deuda = ft.AlertDialog(
        title=ft.Text("Actualizar Deuda"),
        content=contenido_deuda,
        actions=[
            ft.FilledButton("Crédito (+)", on_click=lambda e: procesar_deuda("sumar"), style=ft.ButtonStyle(bgcolor=ft.colors.RED_700, color=ft.colors.WHITE)),
            ft.FilledButton("Abonar (-)", on_click=lambda e: procesar_deuda("restar"), style=ft.ButtonStyle(bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE)),
            ft.TextButton("Cancelar", on_click=cerrar_dialogo_deuda)
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )

    # --- C. Dialogo para Confirmar Eliminación ---
    def cerrar_dialogo_eliminar(e):
        page.close(dialogo_eliminar)

    def eliminar_cliente_bd(e):
        conexion = sqlite3.connect("fiados.db")
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_seleccionado_id,))
        cursor.execute("DELETE FROM transacciones WHERE cliente_id = ?", (cliente_seleccionado_id,))
        conexion.commit()
        conexion.close()
        
        page.close(dialogo_eliminar)
        notificar("Cliente y su historial eliminados.", ft.colors.RED_700)
        cargar_datos()

    dialogo_eliminar = ft.AlertDialog(
        title=ft.Text("Eliminar Cliente", color=ft.colors.RED_400),
        content=ft.Text("¿Estás seguro de que deseas eliminar este registro?\nSe borrará todo su historial."),
        actions=[
            ft.TextButton("Sí, eliminar", on_click=eliminar_cliente_bd, style=ft.ButtonStyle(color=ft.colors.RED_400)),
            ft.TextButton("No, cancelar", on_click=cerrar_dialogo_eliminar)
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # Controladores de apertura
    def abrir_nuevo_cliente(e):
        page.open(dialogo_nuevo)

    def abrir_opciones(id_cliente, nombre_cliente, tlf, correo, deuda):
        nonlocal cliente_seleccionado_id, cliente_seleccionado_nombre, cliente_seleccionado_tlf, cliente_seleccionado_correo, cliente_seleccionado_deuda
        cliente_seleccionado_id = id_cliente
        cliente_seleccionado_nombre = nombre_cliente
        cliente_seleccionado_tlf = tlf
        cliente_seleccionado_correo = correo
        cliente_seleccionado_deuda = deuda
        
        dialogo_deuda.title.value = f"Operación: {nombre_cliente}"
        boton_fecha.text = datetime.now().strftime("%d/%m/%Y")
        opcion_notificacion.value = "Ninguna" # Reiniciar menú al abrir
        page.open(dialogo_deuda)

    def abrir_confirmacion_eliminar(id_cliente):
        nonlocal cliente_seleccionado_id
        cliente_seleccionado_id = id_cliente
        page.open(dialogo_eliminar)

    # ==========================================
    # BOTÓN FLOTANTE
    # ==========================================
    page.floating_action_button = ft.FloatingActionButton(icon=ft.icons.ADD, bgcolor=ft.colors.INDIGO_500, on_click=abrir_nuevo_cliente)

    # ==========================================
    # BASE DE DATOS, HISTORIAL Y TARJETAS
    # ==========================================
    lista_clientes = ft.ListView(expand=True, spacing=10, padding=15)

    def cargar_datos():
        lista_clientes.controls.clear()
        
        conexion = sqlite3.connect("fiados.db")
        cursor = conexion.cursor()
        # Traemos también los nuevos campos
        cursor.execute("SELECT id, nombre, deuda, telefono, correo FROM clientes ORDER BY nombre ASC") 
        clientes = cursor.fetchall()
        
        for cliente in clientes:
            id_cliente = cliente[0]
            nombre = cliente[1]
            deuda = cliente[2]
            telefono = cliente[3] if cliente[3] else ""
            correo = cliente[4] if cliente[4] else ""
            
            # Formato de la tarjeta con los nuevos datos
            texto_subtitulo = f"Deuda: ${deuda:.2f}"
            datos_contacto = []
            if telefono: datos_contacto.append(f"📱 {telefono}")
            if correo: datos_contacto.append(f"✉️ {correo}")
            
            if datos_contacto:
                texto_subtitulo += "\n" + " | ".join(datos_contacto)
            
            cursor.execute("SELECT fecha, hora, tipo, monto FROM transacciones WHERE cliente_id = ? ORDER BY id DESC LIMIT 20", (id_cliente,))
            historial = cursor.fetchall()
            
            controles_historial = []
            controles_historial.append(
                ft.Container(content=ft.Text("Últimos movimientos:", size=12, weight=ft.FontWeight.BOLD, color=ft.colors.ON_SURFACE_VARIANT), padding=ft.padding.only(left=20, top=5, bottom=5))
            )
            
            if historial:
                for trans in historial:
                    color_icono = ft.colors.RED_400 if trans[2] == "Crédito" else ft.colors.GREEN_400
                    icono_flecha = ft.icons.ARROW_UPWARD if trans[2] == "Crédito" else ft.icons.ARROW_DOWNWARD
                    controles_historial.append(
                        ft.ListTile(
                            leading=ft.Icon(icono_flecha, color=color_icono, size=20),
                            title=ft.Text(f"{trans[2]}: ${trans[3]:.2f}", size=14, weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(f"{trans[0]} • {trans[1]}", size=12),
                            dense=True, content_padding=ft.padding.only(left=30, right=20)
                        )
                    )
            else:
                controles_historial.append(
                    ft.Container(content=ft.Text("Sin movimientos registrados", size=12, color=ft.colors.ON_SURFACE_VARIANT), padding=ft.padding.only(left=20, bottom=10))
                )
                
            fila_botones = ft.Row(
                [
                    ft.TextButton("Nueva Operación", icon=ft.icons.ADD_CARD, icon_color=ft.colors.BLUE_400, on_click=lambda e, id_c=id_cliente, nom=nombre, tlf=telefono, corr=correo, d=deuda: abrir_opciones(id_c, nom, tlf, corr, d)),
                    ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_color=ft.colors.RED_400, tooltip="Eliminar Cliente", on_click=lambda e, id_c=id_cliente: abrir_confirmacion_eliminar(id_c))
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            )
            
            controles_historial.append(ft.Divider(height=1, color=ft.colors.OUTLINE_VARIANT))
            controles_historial.append(ft.Container(content=fila_botones, padding=ft.padding.only(left=10, right=10, top=5, bottom=5)))
            
            tarjeta = ft.Card(
                elevation=4,
                color=ft.colors.SURFACE_VARIANT,
                content=ft.ExpansionTile(
                    title=ft.Text(nombre, weight=ft.FontWeight.BOLD, size=18),
                    subtitle=ft.Text(texto_subtitulo, color=ft.colors.RED_400 if deuda > 0 else ft.colors.GREEN_500, weight=ft.FontWeight.W_500),
                    leading=ft.CircleAvatar(content=ft.Text(nombre[0].upper(), weight=ft.FontWeight.BOLD), color=ft.colors.WHITE, bgcolor=ft.colors.INDIGO_400),
                    controls=controles_historial 
                )
            )
            lista_clientes.controls.append(tarjeta)
            
        conexion.close()
        page.update()

    # ==========================================
    # MARCA DE AGUA (CAPAS / STACK)
    # ==========================================
    marca_agua = ft.Container(
        content=ft.Column(
            [ft.Icon(ft.icons.MENU_BOOK, size=150, color=ft.colors.ON_SURFACE, opacity=0.04), ft.Text("CREDI-PERSONAS", size=26, weight=ft.FontWeight.W_900, color=ft.colors.ON_SURFACE, opacity=0.04)],
            alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        alignment=ft.alignment.center, expand=True
    )

    capas = ft.Stack([marca_agua, lista_clientes], expand=True)
    page.add(capas)
    cargar_datos()

ft.app(target=main)
