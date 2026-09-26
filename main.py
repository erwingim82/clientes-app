import flet as ft
import sqlite3
from datetime import datetime
import urllib.parse

def main(page: ft.Page):
    # 1. Configuración de la ventana y tema
    page.window_width = 380
    page.window_height = 680
    page.title = "Credi-Personas"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.colors.BLUE_GREY_900

    # ==========================================
    # BASE DE DATOS (CON PREGUNTAS DE SEGURIDAD)
    # ==========================================
    DB_NAME = "credipersonas_prod.db"

    def inicializar_bd():
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        
        cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT, clave TEXT)")
        
        # Actualización para V1.8: Agregar columnas de seguridad sin borrar datos
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN pregunta TEXT")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN respuesta TEXT")
        except sqlite3.OperationalError:
            pass # Si ya existen, ignora el error
            
        cursor.execute("CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, deuda REAL, telefono TEXT, correo TEXT)")
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

    def notificar(mensaje, color=ft.colors.GREEN_700):
        page.open(ft.SnackBar(ft.Text(mensaje, color=ft.colors.WHITE), bgcolor=color, duration=3000))

    # ==========================================
    # MÓDULO DE LOGIN, REGISTRO Y RECUPERACIÓN
    # ==========================================
    def mostrar_pantalla_acceso():
        page.clean()
        page.appbar = None 
        
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        hay_usuarios = cursor.fetchone()[0] > 0
        conexion.close()

        # Elementos de Interfaz Login/Registro
        txt_usuario = ft.TextField(label="Usuario", prefix_icon=ft.icons.PERSON, width=300)
        txt_clave = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, prefix_icon=ft.icons.LOCK, width=300)
        
        # Elementos nuevos para Registro de Seguridad
        drop_pregunta = ft.Dropdown(
            label="Pregunta de Seguridad",
            options=[
                ft.dropdown.Option("¿Cuál es el nombre de tu primera mascota?"),
                ft.dropdown.Option("¿En qué ciudad naciste?"),
                ft.dropdown.Option("¿Cuál es tu color favorito?"),
                ft.dropdown.Option("¿Nombre de tu mejor amigo de la infancia?"),
            ],
            width=300
        )
        txt_respuesta = ft.TextField(label="Respuesta secreta", width=300)

        def iniciar_sesion(e):
            conexion = sqlite3.connect(DB_NAME)
            cursor = conexion.cursor()
            cursor.execute("SELECT * FROM usuarios WHERE usuario = ? AND clave = ?", (txt_usuario.value, txt_clave.value))
            usuario_valido = cursor.fetchone()
            conexion.close()

            if usuario_valido:
                construir_interfaz_principal()
            else:
                notificar("Usuario o contraseña incorrectos", ft.colors.RED_700)

        def registrar_admin(e):
            if txt_usuario.value and txt_clave.value and drop_pregunta.value and txt_respuesta.value:
                conexion = sqlite3.connect(DB_NAME)
                cursor = conexion.cursor()
                # Guardamos la respuesta en minúsculas para que sea más fácil validarla después
                resp_seguridad = txt_respuesta.value.strip().lower()
                cursor.execute("INSERT INTO usuarios (usuario, clave, pregunta, respuesta) VALUES (?, ?, ?, ?)", 
                               (txt_usuario.value, txt_clave.value, drop_pregunta.value, resp_seguridad))
                conexion.commit()
                conexion.close()
                notificar("Administrador creado con éxito", ft.colors.BLUE_700)
                construir_interfaz_principal()
            else:
                notificar("Por favor completa todos los campos", ft.colors.RED_700)

        # --- FLUJO DE RECUPERACIÓN DE CLAVE ---
        txt_rec_usuario = ft.TextField(label="Tu Usuario")
        txt_rec_respuesta = ft.TextField(label="Respuesta")
        txt_rec_nueva_clave = ft.TextField(label="Nueva Contraseña", password=True, can_reveal_password=True)
        lbl_pregunta = ft.Text(weight=ft.FontWeight.BOLD)
        paso_recuperacion = 1
        usuario_recuperacion = ""

        def cerrar_recuperacion(e):
            page.close(dialogo_recuperar)

        def avanzar_recuperacion(e):
            nonlocal paso_recuperacion, usuario_recuperacion
            conexion = sqlite3.connect(DB_NAME)
            cursor = conexion.cursor()

            if paso_recuperacion == 1:
                cursor.execute("SELECT pregunta FROM usuarios WHERE usuario = ?", (txt_rec_usuario.value,))
                res = cursor.fetchone()
                if res and res[0]: # Si existe y tiene pregunta
                    usuario_recuperacion = txt_rec_usuario.value
                    lbl_pregunta.value = f"Pregunta: {res[0]}"
                    paso_recuperacion = 2
                    dialogo_recuperar.content = ft.Column([lbl_pregunta, txt_rec_respuesta], tight=True)
                    page.update()
                else:
                    notificar("Usuario no encontrado o no tiene pregunta configurada", ft.colors.RED_700)

            elif paso_recuperacion == 2:
                resp_ingresada = txt_rec_respuesta.value.strip().lower()
                cursor.execute("SELECT id FROM usuarios WHERE usuario = ? AND respuesta = ?", (usuario_recuperacion, resp_ingresada))
                if cursor.fetchone():
                    paso_recuperacion = 3
                    dialogo_recuperar.content = ft.Column([ft.Text("Ingresa tu nueva contraseña:"), txt_rec_nueva_clave], tight=True)
                    boton_avanzar_rec.text = "Guardar nueva clave"
                    page.update()
                else:
                    notificar("Respuesta incorrecta", ft.colors.RED_700)

            elif paso_recuperacion == 3:
                if txt_rec_nueva_clave.value:
                    cursor.execute("UPDATE usuarios SET clave = ? WHERE usuario = ?", (txt_rec_nueva_clave.value, usuario_recuperacion))
                    conexion.commit()
                    page.close(dialogo_recuperar)
                    notificar("Contraseña actualizada. Inicia sesión.", ft.colors.GREEN_700)
                else:
                    notificar("La contraseña no puede estar vacía", ft.colors.RED_700)

            conexion.close()

        boton_avanzar_rec = ft.TextButton("Siguiente", on_click=avanzar_recuperacion)
        dialogo_recuperar = ft.AlertDialog(
            title=ft.Text("Recuperar Contraseña"),
            content=ft.Column([ft.Text("Ingresa tu usuario para buscar tu pregunta secreta:"), txt_rec_usuario], tight=True),
            actions=[boton_avanzar_rec, ft.TextButton("Cancelar", on_click=cerrar_recuperacion)]
        )

        def iniciar_recuperacion(e):
            nonlocal paso_recuperacion
            paso_recuperacion = 1
            txt_rec_usuario.value = txt_rec_respuesta.value = txt_rec_nueva_clave.value = ""
            boton_avanzar_rec.text = "Siguiente"
            dialogo_recuperar.content = ft.Column([ft.Text("Ingresa tu usuario para buscar tu pregunta secreta:"), txt_rec_usuario], tight=True)
            page.open(dialogo_recuperar)

        # --- RENDERIZADO DE PANTALLA DE ACCESO ---
        if hay_usuarios:
            titulo = ft.Text("Iniciar Sesión", size=24, weight=ft.FontWeight.BOLD)
            boton_accion = ft.FilledButton("Entrar", on_click=iniciar_sesion, width=300, style=ft.ButtonStyle(bgcolor=ft.colors.INDIGO_500))
            boton_olvide = ft.TextButton("¿Olvidaste tu contraseña?", on_click=iniciar_recuperacion)
            elementos_pantalla = [ft.Icon(ft.icons.LOCK_PERSON, size=80, color=ft.colors.INDIGO_400), titulo, ft.Divider(color=ft.colors.TRANSPARENT, height=20), txt_usuario, txt_clave, boton_accion, boton_olvide]
        else:
            titulo = ft.Text("Crear Administrador", size=24, weight=ft.FontWeight.BOLD)
            boton_accion = ft.FilledButton("Registrar y Entrar", on_click=registrar_admin, width=300, style=ft.ButtonStyle(bgcolor=ft.colors.GREEN_600))
            elementos_pantalla = [
                ft.Icon(ft.icons.ADMIN_PANEL_SETTINGS, size=80, color=ft.colors.GREEN_400), titulo, 
                ft.Text("Configura tu acceso de seguridad", size=14, color=ft.colors.WHITE54),
                ft.Divider(color=ft.colors.TRANSPARENT, height=10),
                txt_usuario, txt_clave, drop_pregunta, txt_respuesta, boton_accion
            ]

        contenedor_login = ft.Container(
            content=ft.Column(elementos_pantalla, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.center, expand=True
        )
        page.add(contenedor_login)

    # ==========================================
    # APLICACIÓN PRINCIPAL
    # ==========================================
    def construir_interfaz_principal():
        page.clean()

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

        dialogo_acerca = ft.AlertDialog(
            title=ft.Text("Acerca de", weight=ft.FontWeight.BOLD),
            content=ft.Column([ft.Text("Credi-Personas\nVersión V1.8 (Seguridad)\n\nDesarrollado por: EIM", size=16, text_align=ft.TextAlign.CENTER), ft.TextButton(content=ft.Row([ft.Icon(ft.icons.EMAIL, color=ft.colors.BLUE_400), ft.Text("Soporte", color=ft.colors.BLUE_400)], alignment=ft.MainAxisAlignment.CENTER, tight=True), on_click=lambda e: page.launch_url("mailto:myconsultingsca@gmail.com?subject=Soporte App"))], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            actions=[ft.TextButton("Cerrar", on_click=lambda e: page.close(dialogo_acerca))]
        )

        page.appbar = ft.AppBar(
            title=ft.Text("Credi-Personas", weight=ft.FontWeight.BOLD), center_title=True, bgcolor=ft.colors.SURFACE_VARIANT, elevation=5,
            actions=[boton_tema, ft.IconButton(ft.icons.INFO_OUTLINE, on_click=lambda e: page.open(dialogo_acerca))]
        )

        cliente_seleccionado_id = None
        cliente_seleccionado_nombre = ""
        cliente_seleccionado_tlf = ""
        cliente_seleccionado_correo = ""
        cliente_seleccionado_deuda = 0.0

        # --- A. Nuevo Cliente ---
        entrada_nombre = ft.TextField(label="Nombre completo", capitalization=ft.TextCapitalization.WORDS)
        entrada_telefono = ft.TextField(label="Teléfono (Ej: +584241234567)", keyboard_type=ft.KeyboardType.PHONE)
        entrada_correo = ft.TextField(label="Correo electrónico", keyboard_type=ft.KeyboardType.EMAIL)
        
        def guardar_nuevo_cliente(e):
            if entrada_nombre.value:
                conexion = sqlite3.connect(DB_NAME)
                cursor = conexion.cursor()
                cursor.execute("INSERT INTO clientes (nombre, deuda, telefono, correo) VALUES (?, 0.0, ?, ?)", (entrada_nombre.value, entrada_telefono.value, entrada_correo.value))
                conexion.commit()
                conexion.close()
                page.close(dialogo_nuevo) 
                notificar(f"Cliente '{entrada_nombre.value}' registrado.", ft.colors.BLUE_700)
                entrada_nombre.value = entrada_telefono.value = entrada_correo.value = ""
                cargar_datos()
            else:
                notificar("El nombre no puede estar vacío", ft.colors.RED_700)

        dialogo_nuevo = ft.AlertDialog(title=ft.Text("Nuevo Cliente"), content=ft.Column([entrada_nombre, entrada_telefono, entrada_correo], tight=True), actions=[ft.TextButton("Guardar", on_click=guardar_nuevo_cliente), ft.TextButton("Cancelar", on_click=lambda e: page.close(dialogo_nuevo))])

        # --- B. Editar Cliente ---
        editar_nombre = ft.TextField(label="Nombre completo", capitalization=ft.TextCapitalization.WORDS)
        editar_telefono = ft.TextField(label="Teléfono (Ej: +584241234567)", keyboard_type=ft.KeyboardType.PHONE)
        editar_correo = ft.TextField(label="Correo electrónico", keyboard_type=ft.KeyboardType.EMAIL)

        def confirmar_edicion_bd(e):
            conexion = sqlite3.connect(DB_NAME)
            cursor = conexion.cursor()
            cursor.execute("UPDATE clientes SET nombre = ?, telefono = ?, correo = ? WHERE id = ?", (editar_nombre.value, editar_telefono.value, editar_correo.value, cliente_seleccionado_id))
            conexion.commit()
            conexion.close()
            page.close(dialogo_confirmar_edicion)
            page.close(dialogo_editar)
            notificar("Datos actualizados correctamente.", ft.colors.BLUE_700)
            cargar_datos()

        dialogo_confirmar_edicion = ft.AlertDialog(title=ft.Text("Confirmar cambios", color=ft.colors.ORANGE_400), content=ft.Text("¿Estás seguro de modificar los datos personales de este cliente?"), actions=[ft.TextButton("Sí, guardar", on_click=confirmar_edicion_bd, style=ft.ButtonStyle(color=ft.colors.ORANGE_400)), ft.TextButton("No, volver", on_click=lambda e: page.close(dialogo_confirmar_edicion))], actions_alignment=ft.MainAxisAlignment.END)
        dialogo_editar = ft.AlertDialog(title=ft.Text("Editar Cliente"), content=ft.Column([editar_nombre, editar_telefono, editar_correo], tight=True), actions=[ft.TextButton("Actualizar", on_click=lambda e: page.open(dialogo_confirmar_edicion)), ft.TextButton("Cancelar", on_click=lambda e: page.close(dialogo_editar))])

        def abrir_dialogo_editar(id_cliente, nombre, tlf, correo):
            nonlocal cliente_seleccionado_id
            cliente_seleccionado_id = id_cliente
            editar_nombre.value, editar_telefono.value, editar_correo.value = nombre, tlf, correo
            page.open(dialogo_editar)

        # --- C. Registrar Operación ---
        entrada_monto = ft.TextField(label="Ingrese el monto", keyboard_type=ft.KeyboardType.NUMBER)
        opcion_notificacion = ft.Dropdown(label="Enviar Recibo por:", options=[ft.dropdown.Option("Ninguna"), ft.dropdown.Option("WhatsApp"), ft.dropdown.Option("Correo Electrónico")], value="Ninguna")
        
        def cambiar_fecha(e):
            if selector_fecha.value:
                boton_fecha.text = selector_fecha.value.strftime("%d/%m/%Y")
                page.update()

        selector_fecha = ft.DatePicker(first_date=datetime(2020, 1, 1), last_date=datetime(2030, 12, 31), on_change=cambiar_fecha)
        boton_fecha = ft.OutlinedButton(text=datetime.now().strftime("%d/%m/%Y"), icon=ft.icons.CALENDAR_MONTH, on_click=lambda e: page.open(selector_fecha))

        def procesar_deuda(operacion):
            try:
                monto = float(entrada_monto.value.replace(",", ".")) 
            except (ValueError, TypeError):
                notificar("Monto numérico inválido", ft.colors.RED_700)
                return
                
            fecha, hora = boton_fecha.text, datetime.now().strftime("%I:%M %p")
                
            if operacion == "restar":
                monto_bd, tipo_transaccion, color_alerta = -monto, "Amortización", ft.colors.GREEN_700
                mensaje = f"Amortización de ${monto:.2f} registrada"
            else:
                monto_bd, tipo_transaccion, color_alerta = monto, "Crédito", ft.colors.RED_700
                mensaje = f"Crédito de ${monto:.2f} otorgado"
                
            saldo_final = cliente_seleccionado_deuda + monto_bd
            texto_recibo_url = urllib.parse.quote(f"🧾 *RECIBO CREDI-PERSONAS*\nHola {cliente_seleccionado_nombre}, se ha registrado un/a {tipo_transaccion} por *${monto:.2f}* el {fecha} a las {hora}.\n\nTu saldo actualizado es de: *${saldo_final:.2f}*.") 

            conexion = sqlite3.connect(DB_NAME)
            cursor = conexion.cursor()
            cursor.execute("UPDATE clientes SET deuda = deuda + ? WHERE id = ?", (monto_bd, cliente_seleccionado_id))
            cursor.execute("INSERT INTO transacciones (cliente_id, fecha, hora, tipo, monto) VALUES (?, ?, ?, ?, ?)", (cliente_seleccionado_id, fecha, hora, tipo_transaccion, monto))
            conexion.commit()
            conexion.close()
            
            entrada_monto.value = ""
            eleccion_notif = opcion_notificacion.value
            page.close(dialogo_deuda) 
            
            if eleccion_notif == "WhatsApp" and cliente_seleccionado_tlf:
                page.launch_url(f"https://wa.me/{cliente_seleccionado_tlf.replace('+', '').replace(' ', '')}?text={texto_recibo_url}")
            elif eleccion_notif == "Correo Electrónico" and cliente_seleccionado_correo:
                page.launch_url(f"mailto:{cliente_seleccionado_correo}?subject=Recibo de Operación&body={texto_recibo_url}")
            else:
                notificar(mensaje, color_alerta)
                if eleccion_notif != "Ninguna": notificar("Faltan datos de contacto del cliente", ft.colors.ORANGE_700)
            cargar_datos()

        dialogo_deuda = ft.AlertDialog(title=ft.Text("Registrar Operación"), content=ft.Column([entrada_monto, ft.Row([ft.Text("Fecha:", weight=ft.FontWeight.W_500), boton_fecha], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Divider(height=1), opcion_notificacion], tight=True), actions=[ft.FilledButton("Otorgar crédito", on_click=lambda e: procesar_deuda("sumar"), style=ft.ButtonStyle(bgcolor=ft.colors.RED_700, color=ft.colors.WHITE)), ft.FilledButton("Amortizar capital", on_click=lambda e: procesar_deuda("restar"), style=ft.ButtonStyle(bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE)), ft.TextButton("Cancelar", on_click=lambda e: page.close(dialogo_deuda))], actions_alignment=ft.MainAxisAlignment.CENTER)

        def abrir_opciones(id_cliente, nombre_cliente, tlf, correo, deuda):
            nonlocal cliente_seleccionado_id, cliente_seleccionado_nombre, cliente_seleccionado_tlf, cliente_seleccionado_correo, cliente_seleccionado_deuda
            cliente_seleccionado_id, cliente_seleccionado_nombre, cliente_seleccionado_tlf, cliente_seleccionado_correo, cliente_seleccionado_deuda = id_cliente, nombre_cliente, tlf, correo, deuda
            dialogo_deuda.title.value = f"Operación: {nombre_cliente}"
            boton_fecha.text = datetime.now().strftime("%d/%m/%Y")
            opcion_notificacion.value = "Ninguna" 
            page.open(dialogo_deuda)

        # --- D. Eliminar Cliente ---
        def eliminar_cliente_bd(e):
            conexion = sqlite3.connect(DB_NAME)
            cursor = conexion.cursor()
            cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_seleccionado_id,))
            cursor.execute("DELETE FROM transacciones WHERE cliente_id = ?", (cliente_seleccionado_id,))
            conexion.commit()
            conexion.close()
            page.close(dialogo_eliminar)
            notificar("Cliente y su historial eliminados.", ft.colors.RED_700)
            cargar_datos()

        dialogo_eliminar = ft.AlertDialog(title=ft.Text("Eliminar Cliente", color=ft.colors.RED_400), content=ft.Text("¿Estás seguro de que deseas eliminar este registro?\nSe borrará todo su historial."), actions=[ft.TextButton("Sí, eliminar", on_click=eliminar_cliente_bd, style=ft.ButtonStyle(color=ft.colors.RED_400)), ft.TextButton("No, cancelar", on_click=lambda e: page.close(dialogo_eliminar))], actions_alignment=ft.MainAxisAlignment.END)

        def abrir_confirmacion_eliminar(id_cliente):
            nonlocal cliente_seleccionado_id
            cliente_seleccionado_id = id_cliente
            page.open(dialogo_eliminar)

        # ==========================================
        # INTERFAZ Y RENDERIZADO
        # ==========================================
        page.floating_action_button = ft.FloatingActionButton(icon=ft.icons.ADD, bgcolor=ft.colors.INDIGO_500, on_click=lambda e: page.open(dialogo_nuevo))
        lista_clientes = ft.ListView(expand=True, spacing=10, padding=15)

        def cargar_datos():
            lista_clientes.controls.clear()
            conexion = sqlite3.connect(DB_NAME)
            cursor = conexion.cursor()
            cursor.execute("SELECT id, nombre, deuda, telefono, correo FROM clientes ORDER BY nombre ASC") 
            clientes = cursor.fetchall()
            
            for cliente in clientes:
                id_cliente, nombre, deuda = cliente[0], cliente[1], cliente[2]
                telefono, correo = cliente[3] if cliente[3] else "", cliente[4] if cliente[4] else ""
                
                texto_subtitulo = f"Deuda: ${deuda:.2f}"
                datos_contacto = []
                if telefono: datos_contacto.append(f"📱 {telefono}")
                if correo: datos_contacto.append(f"✉️ {correo}")
                if datos_contacto: texto_subtitulo += "\n" + " | ".join(datos_contacto)
                
                cursor.execute("SELECT fecha, hora, tipo, monto FROM transacciones WHERE cliente_id = ? ORDER BY id DESC LIMIT 20", (id_cliente,))
                historial = cursor.fetchall()
                
                controles_historial = [ft.Container(content=ft.Text("Últimos movimientos:", size=12, weight=ft.FontWeight.BOLD, color=ft.colors.ON_SURFACE_VARIANT), padding=ft.padding.only(left=20, top=5, bottom=5))]
                if historial:
                    for trans in historial:
                        color_icono = ft.colors.RED_400 if trans[2] == "Crédito" else ft.colors.GREEN_400
                        icono_flecha = ft.icons.ARROW_UPWARD if trans[2] == "Crédito" else ft.icons.ARROW_DOWNWARD
                        controles_historial.append(ft.ListTile(leading=ft.Icon(icono_flecha, color=color_icono, size=20), title=ft.Text(f"{trans[2]}: ${trans[3]:.2f}", size=14, weight=ft.FontWeight.BOLD), subtitle=ft.Text(f"{trans[0]} • {trans[1]}", size=12), dense=True, content_padding=ft.padding.only(left=30, right=20)))
                else:
                    controles_historial.append(ft.Container(content=ft.Text("Sin movimientos registrados", size=12, color=ft.colors.ON_SURFACE_VARIANT), padding=ft.padding.only(left=20, bottom=10)))
                    
                fila_botones = ft.Row([
                    ft.TextButton("Nueva Operación", icon=ft.icons.ADD_CARD, icon_color=ft.colors.BLUE_400, on_click=lambda e, id_c=id_cliente, nom=nombre, tlf=telefono, corr=correo, d=deuda: abrir_opciones(id_c, nom, tlf, corr, d)),
                    ft.Row([
                        ft.IconButton(icon=ft.icons.EDIT, icon_color=ft.colors.ORANGE_400, tooltip="Editar Cliente", on_click=lambda e, id_c=id_cliente, n=nombre, t=telefono, c=correo: abrir_dialogo_editar(id_c, n, t, c)),
                        ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_color=ft.colors.RED_400, tooltip="Eliminar Cliente", on_click=lambda e, id_c=id_cliente: abrir_confirmacion_eliminar(id_c))
                    ])
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                
                controles_historial.extend([ft.Divider(height=1, color=ft.colors.OUTLINE_VARIANT), ft.Container(content=fila_botones, padding=ft.padding.only(left=10, right=10, top=5, bottom=5))])
                
                tarjeta = ft.Card(elevation=4, color=ft.colors.SURFACE_VARIANT, content=ft.ExpansionTile(title=ft.Text(nombre, weight=ft.FontWeight.BOLD, size=18), subtitle=ft.Text(texto_subtitulo, color=ft.colors.RED_400 if deuda > 0 else ft.colors.GREEN_500, weight=ft.FontWeight.W_500), leading=ft.CircleAvatar(content=ft.Text(nombre[0].upper(), weight=ft.FontWeight.BOLD), color=ft.colors.WHITE, bgcolor=ft.colors.INDIGO_400), controls=controles_historial))
                lista_clientes.controls.append(tarjeta)
                
            conexion.close()
            page.update()

        marca_agua = ft.Container(content=ft.Column([ft.Icon(ft.icons.MENU_BOOK, size=150, color=ft.colors.ON_SURFACE, opacity=0.04), ft.Text("CREDI-PERSONAS", size=26, weight=ft.FontWeight.W_900, color=ft.colors.ON_SURFACE, opacity=0.04)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), alignment=ft.alignment.center, expand=True)
        page.add(ft.Stack([marca_agua, lista_clientes], expand=True))
        cargar_datos()

    # Iniciar flujo
    mostrar_pantalla_acceso()

ft.app(target=main)
