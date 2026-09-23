import flet as ft
import sqlite3

def main(page: ft.Page):
    # 1. Configuración de la ventana y tema
    page.window_width = 380
    page.window_height = 680
    page.title = "Credi-Personas"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.colors.BLUE_GREY_900

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

    boton_tema = ft.IconButton(
        icon=ft.icons.LIGHT_MODE,
        on_click=cambiar_tema
    )

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

    dialogo_acerca = ft.AlertDialog(
        title=ft.Text("Acerca de", weight=ft.FontWeight.BOLD),
        content=ft.Text(
            "Credi-Personas\nVersión V1.1\n\nDesarrollado por: EIM", 
            size=16, 
            text_align=ft.TextAlign.CENTER
        ),
        actions=[
            ft.TextButton("Cerrar", on_click=cerrar_acerca_de)
        ],
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
        actions=[
            boton_tema, # Agregamos el switch de luz aquí
            ft.IconButton(ft.icons.INFO_OUTLINE, on_click=abrir_acerca_de) 
        ]
    )

    # ==========================================
    # VENTANAS EMERGENTES (NUEVO Y DEUDA)
    # ==========================================
    
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
        actions=[
            ft.TextButton("Guardar", on_click=guardar_nuevo_cliente),
            ft.TextButton("Cancelar", on_click=cerrar_dialogo_nuevo)
        ]
    )

    # --- B. Dialogo para Actualizar Deuda ---
    cliente_seleccionado_id = None
    entrada_monto = ft.TextField(label="Monto ($)", keyboard_type=ft.KeyboardType.NUMBER)

    def cerrar_dialogo_deuda(e):
        page.close(dialogo_deuda)

    def procesar_deuda(operacion):
        try:
            monto = float(entrada_monto.value.replace(",", ".")) 
        except (ValueError, TypeError):
            notificar("Ingresa un monto numérico válido", ft.colors.RED_700)
            return
            
        if operacion == "restar":
            monto_final = -monto
            mensaje = f"Abono de ${monto:.2f} registrado"
            color_alerta = ft.colors.GREEN_700
        else:
            monto_final = monto
            mensaje = f"Crédito de ${monto:.2f} aplicado"
            color_alerta = ft.colors.RED_700
            
        conexion = sqlite3.connect("fiados.db")
        cursor = conexion.cursor()
        cursor.execute("UPDATE clientes SET deuda = deuda + ? WHERE id = ?", (monto_final, cliente_seleccionado_id))
        conexion.commit()
        conexion.close()
        
        entrada_monto.value = ""
        page.close(dialogo_deuda) 
        notificar(mensaje, color_alerta)
        cargar_datos()

    # Botones a color (FilledButton) en la ventana
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

    def abrir_nuevo_cliente(e):
        page.open(dialogo_nuevo)

    def abrir_opciones(e):
        nonlocal cliente_seleccionado_id
        cliente_seleccionado_id = e.control.data
        dialogo_deuda.title.value = f"Monto para {e.control.title.value}"
        page.open(dialogo_deuda)

    # ==========================================
    # BOTÓN FLOTANTE (ESTILO MÓVIL)
    # ==========================================
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.icons.ADD,
        bgcolor=ft.colors.INDIGO_500,
        on_click=abrir_nuevo_cliente
    )

    # ==========================================
    # BASE DE DATOS Y TARJETAS
    # ==========================================
    lista_clientes = ft.ListView(expand=True, spacing=10, padding=15)

    def cargar_datos():
        lista_clientes.controls.clear()
        
        conexion = sqlite3.connect("fiados.db")
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM clientes ORDER BY nombre ASC") 
        
        for cliente in cursor.fetchall():
            id_cliente = cliente[0]
            nombre = cliente[1]
            deuda = cliente[2]
            
            texto_deuda = f"Deuda: ${deuda:.2f}"
            
            tarjeta = ft.Card(
                elevation=4,
                color=ft.colors.SURFACE_VARIANT,
                content=ft.Container(
                    padding=10,
                    content=ft.ListTile(
                        data=id_cliente,
                        leading=ft.CircleAvatar(
                            content=ft.Text(nombre[0].upper(), weight=ft.FontWeight.BOLD),
                            color=ft.colors.WHITE,
                            bgcolor=ft.colors.INDIGO_400
                        ),
                        title=ft.Text(nombre, weight=ft.FontWeight.BOLD, size=18),
                        subtitle=ft.Text(
                            texto_deuda, 
                            color=ft.colors.RED_400 if deuda > 0 else ft.colors.GREEN_500,
                            weight=ft.FontWeight.W_500
                        ),
                        trailing=ft.Icon(ft.icons.EDIT_NOTE, color=ft.colors.ON_SURFACE_VARIANT),
                        on_click=abrir_opciones 
                    )
                )
            )
            lista_clientes.controls.append(tarjeta)
            
        conexion.close()
        page.update()

    # ==========================================
    # MARCA DE AGUA (CAPAS / STACK)
    # ==========================================
    # Usamos ON_SURFACE para que el logo se vuelva gris oscuro en modo claro y blanco en modo oscuro
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

    capas = ft.Stack(
        [
            marca_agua,    
            lista_clientes 
        ],
        expand=True
    )

    page.add(capas)
    cargar_datos()

ft.app(target=main)
