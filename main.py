import flet as ft
import sqlite3
from datetime import datetime

def main(page: ft.Page):
    # 1. Configuración de la ventana y tema
    page.window_width = 380
    page.window_height = 680
    page.title = "Credi-Personas"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.colors.BLUE_GREY_900

    # ==========================================
    # INICIALIZAR BASE DE DATOS (ACTUALIZACIÓN)
    # ==========================================
    def inicializar_bd():
        conexion = sqlite3.connect("fiados.db")
        cursor = conexion.cursor()
        # Mantiene la tabla original intacta
        cursor.execute("CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, deuda REAL)")
        # Crea la nueva tabla para el historial automático
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
        page.open(ft.SnackBar(ft.Text(mensaje, color=ft.colors.WHITE), bgcolor=color, duration=2500))

    # ==========================================
    # VENTANA EMERGENTE "ACERCA DE"
    # ==========================================
    def cerrar_acerca_de(e):
        page.close(dialogo_acerca)

    def abrir_acerca_de(e):
        page.open(dialogo_acerca)

    def enviar_correo(e):
        page.launch_url("mailto:myconsultingsca@gmail.com?subject=Sugerencias App Credi-Personas")

    dialogo_acerca = ft.AlertDialog(
        title=ft.Text("Acerca de", weight=ft.FontWeight.BOLD),
        content=ft.Column(
            [
                ft.Text("Credi-Personas\nVersión V1.3\n\nDesarrollado por: EIM", size=16, text_align=ft.TextAlign.CENTER),
                ft.Divider(color=ft.colors.TRANSPARENT),
                ft.TextButton(
                    content=ft.Row([ft.Icon(ft.icons.EMAIL, color=ft.colors.BLUE_400), ft.Text("Enviar sugerencias", color=ft.colors.BLUE_400)], alignment=ft.MainAxisAlignment.CENTER, tight=True),
                    on_click=enviar_correo
                )
            ],
            tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        actions=[ft.TextButton("Cerrar", on_click=cerrar_acerca_de)],
        actions_alignment=ft.MainAxisAlignment.CENTER
    )

    # ==========================================
    # BARRA SUPERIOR (APPBAR)
    # ==========================================
    page.appbar = ft.AppBar(
        title=ft.Text("Credi-Personas", weight=ft.FontWeight.BOLD),
        center_title=True,
        bgcolor=ft.colors.SURFACE_VARIANT,
        elevation=5,
        actions=[boton_tema, ft.IconButton(ft.icons.INFO_OUTLINE, on_click=abrir_acerca_de)]
    )

    # ==========================================
    # VENTANAS EMERGENTES (CRUD Y TRANSACCIONES)
    # ==========================================
    cliente_seleccionado_id = None
    
    # --- A. Dialogo para Nuevo Cliente ---
    entrada_nombre = ft.TextField(label="Nombre completo", capitalization=ft.TextCapitalization.WORDS)
    
    def cerrar_dialogo_nuevo(e):
        page.close(dialogo_nuevo)

    def guardar_nuevo_cliente(e):
        if entrada_nombre.value:
            conexion = sqlite3.connect("fiados.db")
            cursor = conexion.cursor()
            cursor.execute("INSERT INTO clientes (nombre, deuda) VALUES (?, 0.0)", (entrada_nombre.value,))
            conexion.commit()
            conexion.close()
            
            nombre_guardado = entrada_nombre.value
            entrada_nombre.value = ""
            page.close(dialogo_nuevo) 
            notificar(f"Cliente '{nombre_guardado}' registrado.", ft.colors.BLUE_700)
            cargar_datos()
        else:
            notificar("El nombre no puede estar vacío", ft.colors.RED_700)

    dialogo_nuevo = ft.AlertDialog(
        title=ft.Text("Nuevo Cliente"),
        content=entrada_nombre,
        actions=[ft.TextButton("Guardar", on_click=guardar_nuevo_cliente), ft.TextButton("Cancelar", on_click=cerrar_dialogo_nuevo)]
    )

    # --- B. Dialogo para Actualizar Deuda (Generador de Historial) ---
    entrada_monto = ft.TextField(label="Monto ($)", keyboard_type=ft.KeyboardType.NUMBER)

    def cerrar_dialogo_deuda(e):
        page.close(dialogo_deuda)

    def procesar_deuda(operacion):
        try:
            monto = float(entrada_monto.value.replace(",", ".")) 
        except (ValueError, TypeError):
            notificar("Ingresa un monto numérico válido", ft.colors.RED_700)
            return
            
        # Capturar fecha y hora exacta del sistema
        ahora = datetime.now()
        fecha = ahora.strftime("%d/%m/%Y")
        hora = ahora.strftime("%I:%M %p")
            
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
            
        conexion = sqlite3.connect("fiados.db")
        cursor = conexion.cursor()
        
        # 1. Actualiza el saldo general
        cursor.execute("UPDATE clientes SET deuda = deuda + ? WHERE id = ?", (monto_bd, cliente_seleccionado_id))
        
        # 2. Crea el registro en el historial
        cursor.execute("INSERT INTO transacciones (cliente_id, fecha, hora, tipo, monto) VALUES (?, ?, ?, ?, ?)", 
                       (cliente_seleccionado_id, fecha, hora, tipo_transaccion, monto))
                       
        conexion.commit()
        conexion.close()
        
        entrada_monto.value = ""
        page.close(dialogo_deuda) 
        notificar(mensaje, color_alerta)
        cargar_datos()

    dialogo_deuda = ft.AlertDialog(
        title=ft.Text("Actualizar Deuda"),
        content=entrada_monto,
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
        # Borra también el historial de ese cliente para no dejar datos huérfanos
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

    # Controladores adaptados para recibir variables por parámetro
    def abrir_nuevo_cliente(e):
        page.open(dialogo_nuevo)

    def abrir_opciones(id_cliente, nombre_cliente):
        nonlocal cliente_seleccionado_id
        cliente_seleccionado_id = id_cliente
        dialogo_deuda.title.value = f"Operación: {nombre_cliente}"
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
        cursor.execute("SELECT * FROM clientes ORDER BY nombre ASC") 
        clientes = cursor.fetchall()
        
        for cliente in clientes:
            id_cliente = cliente[0]
            nombre = cliente[1]
            deuda = cliente[2]
            
            texto_deuda = f"Deuda: ${deuda:.2f}"
            
            # Buscar el historial de este cliente específico (últimos 20 movimientos)
            cursor.execute("SELECT fecha, hora, tipo, monto FROM transacciones WHERE cliente_id = ? ORDER BY id DESC LIMIT 20", (id_cliente,))
            historial = cursor.fetchall()
            
            controles_historial = []
            
            # Título interno del historial
            controles_historial.append(
                ft.Container(
                    content=ft.Text("Últimos movimientos:", size=12, weight=ft.FontWeight.BOLD, color=ft.colors.ON_SURFACE_VARIANT),
                    padding=ft.padding.only(left=20, top=5, bottom=5)
                )
            )
            
            if historial:
                for trans in historial:
                    # trans[0]=fecha, trans[1]=hora, trans[2]=tipo, trans[3]=monto
                    color_icono = ft.colors.RED_400 if trans[2] == "Crédito" else ft.colors.GREEN_400
                    icono_flecha = ft.icons.ARROW_UPWARD if trans[2] == "Crédito" else ft.icons.ARROW_DOWNWARD
                    
                    controles_historial.append(
                        ft.ListTile(
                            leading=ft.Icon(icono_flecha, color=color_icono, size=20),
                            title=ft.Text(f"{trans[2]}: ${trans[3]:.2f}", size=14, weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(f"{trans[0]} • {trans[1]}", size=12),
                            dense=True,
                            content_padding=ft.padding.only(left=30, right=20)
                        )
                    )
            else:
                controles_historial.append(
                    ft.Container(
                        content=ft.Text("Sin movimientos registrados", size=12, color=ft.colors.ON_SURFACE_VARIANT),
                        padding=ft.padding.only(left=20, bottom=10)
                    )
                )
                
            # Fila de botones de acción en la parte inferior del historial
            fila_botones = ft.Row(
                [
                    ft.TextButton(
                        "Nueva Operación", 
                        icon=ft.icons.ADD_CARD, 
                        icon_color=ft.colors.BLUE_400,
                        # Pasamos las variables directamente a la función
                        on_click=lambda e, id_c=id_cliente, nom=nombre: abrir_opciones(id_c, nom)
                    ),
                    ft.IconButton(
                        icon=ft.icons.DELETE_OUTLINE, 
                        icon_color=ft.colors.RED_400,
                        tooltip="Eliminar Cliente",
                        on_click=lambda e, id_c=id_cliente: abrir_confirmacion_eliminar(id_c)
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            )
            
            controles_historial.append(ft.Divider(height=1, color=ft.colors.OUTLINE_VARIANT))
            controles_historial.append(ft.Container(content=fila_botones, padding=ft.padding.only(left=10, right=10, top=5, bottom=5)))
            
            # Tarjeta principal con propiedad desplegable (ExpansionTile)
            tarjeta = ft.Card(
                elevation=4,
                color=ft.colors.SURFACE_VARIANT,
                content=ft.ExpansionTile(
                    title=ft.Text(nombre, weight=ft.FontWeight.BOLD, size=18),
                    subtitle=ft.Text(
                        texto_deuda, 
                        color=ft.colors.RED_400 if deuda > 0 else ft.colors.GREEN_500,
                        weight=ft.FontWeight.W_500
                    ),
                    leading=ft.CircleAvatar(
                        content=ft.Text(nombre[0].upper(), weight=ft.FontWeight.BOLD),
                        color=ft.colors.WHITE,
                        bgcolor=ft.colors.INDIGO_400
                    ),
                    # Agregamos la lista de historial que armamos arriba
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
            [
                ft.Icon(ft.icons.MENU_BOOK, size=150, color=ft.colors.ON_SURFACE, opacity=0.04),
                ft.Text("CREDI-PERSONAS", size=26, weight=ft.FontWeight.W_900, color=ft.colors.ON_SURFACE, opacity=0.04)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        alignment=ft.alignment.center,
        expand=True
    )

    capas = ft.Stack([marca_agua, lista_clientes], expand=True)
    page.add(capas)
    cargar_datos()

ft.app(target=main)
