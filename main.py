import flet as ft
import sqlite3
import os
from pathlib import Path
from datetime import datetime
import urllib.parse

def main(page: ft.Page):
    page.window_width = 380
    page.window_height = 680
    page.title = "Bitácora Financiera"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.colors.BLUE_GREY_900

    # ==========================================
    # 1. RUTA NATIVA BLINDADA (PATHLIB)
    # ==========================================
    try:
        if page.platform == ft.PagePlatform.ANDROID or page.platform == ft.PagePlatform.IOS:
            directorio_base = Path(page.get_user_data_dir())
        else:
            directorio_base = Path(os.getcwd())
            
        directorio_base.mkdir(parents=True, exist_ok=True)
        DB_NAME = str(directorio_base / "bitacora_financiera.db")
    except:
        DB_NAME = "bitacora_respaldo.db"

    def inicializar_bd():
        try:
            conexion = sqlite3.connect(DB_NAME)
            conexion.execute("PRAGMA synchronous = FULL")
            cursor = conexion.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS movimientos (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                fecha TEXT,
                                concepto TEXT,
                                monto REAL,
                                tipo TEXT
                              )''')
            conexion.commit()
            conexion.close()
        except Exception as e:
            print(f"Error inicializando BD: {e}")
        
    inicializar_bd()

    def notificar(mensaje, color=ft.colors.GREEN_700):
        page.open(ft.SnackBar(ft.Text(mensaje, color=ft.colors.WHITE), bgcolor=color, duration=3000))

    # ==========================================
    # 2. ACCIONES SUPERIORES (WHATSAPP Y TASAS INTELIGENTE)
    # ==========================================
    def abrir_dolar_al_dia(e):
        try:
            # Primero intentamos abrir el esquema personalizado de la app (si está instalada)
            # O en su defecto, ejecutamos la URL directa de la Play Store proporcionada
            page.launch_url("https://play.google.com/store/search?q=dolar+al+dia&c=apps")
        except Exception:
            notificar("No se pudo abrir el enlace de búsqueda", ft.colors.RED_700)

    def mostrar_opciones_compartir(e):
        try:
            conexion = sqlite3.connect(DB_NAME)
            cursor = conexion.cursor()
            cursor.execute("SELECT fecha, concepto, monto, tipo FROM movimientos ORDER BY id ASC")
            movimientos = cursor.fetchall()
            conexion.close()

            saldo_total = 0.0
            texto_movimientos = ""

            if movimientos:
                for mov in movimientos:
                    fecha, concepto, monto, tipo = mov
                    es_ingreso = (tipo == "Depósito")
                    signo = "+" if es_ingreso else "-"
                    
                    if es_ingreso:
                        saldo_total += monto
                    else:
                        saldo_total -= monto
                        
                    texto_movimientos += f"• {fecha} | {concepto}: {signo}${monto:.2f}\n"
            else:
                texto_movimientos = "Sin movimientos registrados.\n"

            reporte = f"📊 *BITÁCORA FINANCIERA*\n💰 Saldo Actual: *${saldo_total:.2f}*\n\n*HISTORIAL DE MOVIMIENTOS:*\n{texto_movimientos}"
            reporte_codificado = urllib.parse.quote(reporte)
            url_whatsapp = f"https://api.whatsapp.com/send?text={reporte_codificado}"

            def enviar_wsp(evt):
                page.close(dialogo_compartir)
                page.launch_url(url_whatsapp)

            dialogo_compartir = ft.AlertDialog(
                title=ft.Text("Exportar Reporte", weight=ft.FontWeight.BOLD),
                content=ft.Column([
                    ft.Text("Selecciona una opción para enviar tu bitácora por WhatsApp:", size=13, color=ft.colors.WHITE70),
                    ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                    ft.FilledButton(
                        "Enviar por WhatsApp",
                        icon=ft.icons.SHARE,
                        color=ft.colors.WHITE,
                        bgcolor=ft.colors.GREEN_600,
                        on_click=enviar_wsp
                    )
                ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                actions=[ft.TextButton("Cerrar", on_click=lambda evt: page.close(dialogo_compartir))]
            )
            page.open(dialogo_compartir)

        except Exception as ex:
            notificar(f"Error al generar reporte: {ex}", ft.colors.RED_700)

    # ==========================================
    # 3. INTERFAZ PRINCIPAL
    # ==========================================
    def construir_interfaz_principal():
        page.clean()

        dialogo_acerca = ft.AlertDialog(
            title=ft.Text("Acerca de", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Text("Bitácora Financiera\nVersión V1.3\n\nControl de ingresos y egresos personales.", size=14, text_align=ft.TextAlign.CENTER),
                ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                ft.TextButton(
                    content=ft.Row([
                        ft.Icon(ft.icons.EMAIL, color=ft.colors.BLUE_400), 
                        ft.Text("Enviar Sugerencia / Soporte", color=ft.colors.BLUE_400)
                    ], alignment=ft.MainAxisAlignment.CENTER, tight=True), 
                    on_click=lambda e: page.launch_url("mailto:myconsultingsca@gmail.com?subject=Sugerencias%20Bitacora%20Financiera")
                )
            ], tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            actions=[ft.TextButton("Cerrar", on_click=lambda e: page.close(dialogo_acerca))]
        )

        page.appbar = ft.AppBar(
            title=ft.Text("Mi Bitácora", weight=ft.FontWeight.BOLD),
            center_title=True,
            bgcolor=ft.colors.BLUE_GREY_800,
            elevation=5,
            actions=[
                ft.IconButton(
                    icon=ft.icons.SHARE,
                    icon_color=ft.colors.GREEN_400,
                    tooltip="Exportar por WhatsApp",
                    on_click=mostrar_opciones_compartir
                ),
                ft.IconButton(
                    icon=ft.icons.CURRENCY_EXCHANGE,
                    icon_color=ft.colors.BLUE_400,
                    tooltip="Buscar Dolar al Día",
                    on_click=abrir_dolar_al_dia
                ),
                ft.IconButton(
                    icon=ft.icons.INFO_OUTLINE,
                    icon_color=ft.colors.ORANGE_400,
                    tooltip="Acerca de y Sugerencias",
                    on_click=lambda e: page.open(dialogo_acerca)
                )
            ]
        )

        texto_saldo = ft.Text("$0.00", size=36, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE)
        tarjeta_saldo = ft.Container(
            content=ft.Column(
                [
                    ft.Text("SALDO ACTUAL", size=14, weight=ft.FontWeight.W_500, color=ft.colors.WHITE70),
                    texto_saldo
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            bgcolor=ft.colors.GREEN_700,
            border_radius=15,
            padding=20,
            margin=15, 
            alignment=ft.alignment.center,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=5, color=ft.colors.BLACK38)
        )

        lista_movimientos = ft.ListView(expand=True, spacing=5, padding=15)

        def cargar_datos():
            lista_movimientos.controls.clear()
            try:
                conexion = sqlite3.connect(DB_NAME)
                cursor = conexion.cursor()
                cursor.execute("SELECT id, fecha, concepto, monto, tipo FROM movimientos ORDER BY id DESC")
                movimientos = cursor.fetchall()
                conexion.close()
                
                saldo_total = 0.0
                
                if not movimientos:
                    lista_movimientos.controls.append(
                        ft.Container(
                            content=ft.Text("No hay registros todavía.\n¡Presiona el botón + para empezar!", 
                                            text_align=ft.TextAlign.CENTER, color=ft.colors.WHITE54),
                            alignment=ft.alignment.center,
                            padding=50
                        )
                    )
                else:
                    for mov in movimientos:
                        id_mov, fecha, concepto, monto, tipo = mov
                        es_ingreso = (tipo == "Depósito")
                        color_icono = ft.colors.GREEN_400 if es_ingreso else ft.colors.RED_400
                        icono = ft.icons.ARROW_UPWARD if es_ingreso else ft.icons.ARROW_DOWNWARD
                        signo = "+" if es_ingreso else "-"
                        
                        if es_ingreso:
                            saldo_total += monto
                        else:
                            saldo_total -= monto

                        lista_movimientos.controls.append(
                            ft.Card(
                                elevation=2,
                                color=ft.colors.BLUE_GREY_800,
                                content=ft.ListTile(
                                    leading=ft.CircleAvatar(content=ft.Icon(icono, color=color_icono), bgcolor=ft.colors.BLUE_GREY_900),
                                    title=ft.Text(concepto, weight=ft.FontWeight.BOLD),
                                    subtitle=ft.Text(fecha, size=12, color=ft.colors.WHITE54),
                                    trailing=ft.Text(f"{signo} ${monto:.2f}", color=color_icono, weight=ft.FontWeight.BOLD, size=16)
                                )
                            )
                        )
                
                texto_saldo.value = f"${saldo_total:.2f}"
                tarjeta_saldo.bgcolor = ft.colors.RED_800 if saldo_total < 0 else ft.colors.GREEN_700
            except Exception as ex:
                print(f"Error cargando datos: {ex}")
            
            page.update()

        # ==========================================
        # 4. DIÁLOGO PARA NUEVO REGISTRO
        # ==========================================
        entrada_monto = ft.TextField(label="Monto ($)", keyboard_type=ft.KeyboardType.NUMBER, prefix_icon=ft.icons.ATTACH_MONEY, border_color=ft.colors.RED_400)
        entrada_concepto = ft.TextField(label="Concepto (Ej: Sueldos y salarios)", capitalization=ft.TextCapitalization.SENTENCES, prefix_icon=ft.icons.TEXT_SNIPPET, border_color=ft.colors.RED_400)
        
        def cambiar_fecha(e):
            if selector_fecha.value:
                boton_fecha.text = selector_fecha.value.strftime("%d/%m/%Y")
                page.update()

        selector_fecha = ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31),
            on_change=cambiar_fecha
        )

        boton_fecha = ft.OutlinedButton(
            text=datetime.now().strftime("%d/%m/%Y"),
            icon=ft.icons.CALENDAR_MONTH,
            on_click=lambda e: page.open(selector_fecha)
        )

        def guardar_registro(tipo_operacion):
            if not entrada_monto.value or not entrada_concepto.value:
                return notificar("Por favor completa el monto y el concepto.", ft.colors.ORANGE_700)
                
            try:
                monto = float(entrada_monto.value.replace(",", "."))
            except ValueError:
                return notificar("Monto numérico inválido.", ft.colors.RED_700)
                
            fecha_registro = boton_fecha.text
            concepto = entrada_concepto.value

            try:
                conexion = sqlite3.connect(DB_NAME)
                cursor = conexion.cursor()
                cursor.execute("INSERT INTO movimientos (fecha, concepto, monto, tipo) VALUES (?, ?, ?, ?)", 
                               (fecha_registro, concepto, monto, tipo_operacion))
                conexion.commit()
                conexion.close()
                
                page.close(dialogo_nuevo)
                notificar(f"{tipo_operacion} de ${monto:.2f} registrado con éxito.", ft.colors.BLUE_700)
                
                entrada_monto.value = ""
                entrada_concepto.value = ""
                boton_fecha.text = datetime.now().strftime("%d/%m/%Y")
                
                cargar_datos()
            except Exception as ex:
                notificar(f"Error al guardar en BD: {ex}", ft.colors.RED_700)

        boton_deposito = ft.FilledButton("Depósito", icon=ft.icons.ADD_CIRCLE, style=ft.ButtonStyle(bgcolor=ft.colors.GREEN_600, color=ft.colors.WHITE), on_click=lambda e: guardar_registro("Depósito"), expand=True)
        boton_gasto = ft.FilledButton("Gasto", icon=ft.icons.REMOVE_CIRCLE, style=ft.ButtonStyle(bgcolor=ft.colors.RED_600, color=ft.colors.WHITE), on_click=lambda e: guardar_registro("Gasto"), expand=True)

        dialogo_nuevo = ft.AlertDialog(
            title=ft.Text("Nuevo Registro"),
            content=ft.Column(
                [
                    entrada_concepto,
                    entrada_monto,
                    ft.Row([ft.Text("Fecha:", weight=ft.FontWeight.W_500), boton_fecha], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=10, color=ft.colors.TRANSPARENT),
                    ft.Row([boton_deposito, boton_gasto], spacing=10)
                ],
                tight=True
            ),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: page.close(dialogo_nuevo))],
            actions_alignment=ft.MainAxisAlignment.END
        )

        page.floating_action_button = ft.FloatingActionButton(
            icon=ft.icons.ADD,
            bgcolor=ft.colors.BLUE_500,
            on_click=lambda e: page.open(dialogo_nuevo)
        )

        page.add(
            ft.Column(
                [
                    tarjeta_saldo,
                    ft.Container(
                        content=ft.Text("HISTORIAL DE MOVIMIENTOS", size=12, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE54),
                        padding=10
                    ),
                    lista_movimientos
                ],
                expand=True
            )
        )

        cargar_datos()

    # Iniciar directamente en la interfaz principal ya que es una bitácora personal
    construir_interfaz_principal()

ft.app(target=main)
