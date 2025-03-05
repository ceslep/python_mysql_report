# python -m waitress --listen=0.0.0.0:8000 server:app

from flask import Flask, request, render_template, jsonify, send_file
import pymysql
import os
from dotenv import load_dotenv
from reportlab.lib.pagesizes import legal
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,Frame
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.enums import TA_JUSTIFY


por_margen = 0.3

margen_izquierdo = por_margen * inch
margen_derecho = por_margen * inch
margen_superior = por_margen * inch
margen_inferior = por_margen * inch


# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# Conexión a la base de datos


def get_db_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB"),
        port=int(os.getenv("MYSQL_PORT")),
        cursorclass=pymysql.cursors.DictCursor
    )

# Ruta inicial para servir index.html


@app.route('/')
def index():
    return render_template('index.html')

# Ruta para buscar un estudiante por código, estudiante o nombres


@app.route('/buscar', methods=['GET'])
def buscar_estudiante():
    criterio = request.args.get('criterio')
    partes = criterio.split('-')
    if not criterio:
        return jsonify({"error": "Debe proporcionar un criterio de búsqueda (código, estudiante o nombres)"}), 400

    conexion = get_db_connection()
    with conexion.cursor() as cursor:

        if len(partes) == 3:
            # Si hay tres partes (asignacion-nivel-numero)
            asignacion, nivel, numero = partes

    # Construir la consulta SQL para el caso con tres partes
            sql_estudiante = """
        SELECT estugrupos.*, sedes.sede
        FROM estugrupos
        INNER JOIN (
            SELECT codigo, MAX(year) AS max_year
            FROM estugrupos
            GROUP BY codigo
        ) AS ultimos ON estugrupos.codigo = ultimos.codigo AND estugrupos.year = ultimos.max_year
        LEFT JOIN sedes ON estugrupos.asignacion = sedes.ind
        WHERE estugrupos.asignacion = %s AND estugrupos.nivel = %s AND estugrupos.numero = %s
        and year=year(curdate())
        ORDER BY nombres
    """

    # Ejecutar la consulta con las tres partes del criterio
            cursor.execute(sql_estudiante, (asignacion, nivel, numero))

        elif len(partes) == 2:
            # Si hay dos partes (nivel-numero)
            nivel, numero = partes

    # Construir la consulta SQL para el caso con dos partes
            sql_estudiante = """
        SELECT estugrupos.*, sedes.sede
        FROM estugrupos
        INNER JOIN (
            SELECT codigo, MAX(year) AS max_year
            FROM estugrupos
            GROUP BY codigo
        ) AS ultimos ON estugrupos.codigo = ultimos.codigo AND estugrupos.year = ultimos.max_year
        LEFT JOIN sedes ON estugrupos.asignacion = sedes.ind
        WHERE estugrupos.nivel = %s AND estugrupos.numero = %s
        and year=year(curdate())
        ORDER BY nombres
    """

    # Ejecutar la consulta con las dos partes del criterio
            cursor.execute(sql_estudiante, (nivel, numero))

        else:
            # Si no hay guiones o tiene un formato no reconocido
            sql_estudiante = """
        SELECT estugrupos.*, sedes.sede
        FROM estugrupos
        INNER JOIN (
            SELECT codigo, MAX(year) AS max_year
            FROM estugrupos
            GROUP BY codigo
        ) AS ultimos ON estugrupos.codigo = ultimos.codigo AND estugrupos.year = ultimos.max_year
        LEFT JOIN sedes ON estugrupos.asignacion = sedes.ind
        WHERE estugrupos.codigo LIKE %s OR estugrupos.estudiante LIKE %s OR estugrupos.nombres LIKE %s
        and year=year(curdate())
        ORDER BY nombres
    """

    # Ejecutar la consulta con el criterio completo
            cursor.execute(
                sql_estudiante, (f"%{criterio}%", f"%{criterio}%", f"%{criterio}%"))

# Obtener los resultados
    estudiante = cursor.fetchall()

    conexion.close()

    if not estudiante:
        return jsonify({"error": "Estudiante no encontrado"}), 404

    return jsonify(estudiante)


def agregar_recuadro(canvas, doc):
    # Obtener las dimensiones de la página
    ancho, alto = legal

    # Calcular las coordenadas del rectángulo
    x1 = margen_izquierdo
    y1 = margen_inferior
    x2 = ancho - margen_derecho
    y2 = alto - margen_superior

    # Dibujar el rectángulo
    canvas.rect(x1, y1, x2 - x1, y2 - y1)
    dibujar_footer(canvas, doc)
    x_qr = 485
    y_qr = 25  # Coordenada inferior donde se coloca la imagen
    ancho_qr = 100
    alto_qr = 100

    canvas.drawImage("images/qrcode.jpg", x_qr, y_qr, width=ancho_qr, height=alto_qr)
   # dibujar_informacion_acudiente(canvas, doc,x=x_qr,y=y_qr)


def construir_encabezado():
    """
    Genera una tabla de 2 filas x 3 columnas que reproduce el encabezado
    tal como se ve en la imagen:
      --------------------------------------------------------------
      | escudo.png    | SECRETARÍA DE EDUCACIÓN...  | Página: 1... |
      | (col 0, row0) | INSTITUCIÓN EDUCATIVA...     | Código...    |
      |               | NIT...                       | v.02         |
      |               |                               | 26/01/2012   |
      --------------------------------------------------------------
      | REGISTRO DE MATRÍCULA... | DEPENDENCIA | SECRETARÍA        |
      --------------------------------------------------------------
    """

    styles = getSampleStyleSheet()
    style_normal = styles['Normal']
    style_normal.fontName = 'Helvetica'
    style_normal.fontSize = 9
    # Centra el texto en cada celda
    style_normal.alignment = TA_CENTER

    # 1. Intentamos cargar la imagen del escudo
    logo_path = os.path.join("images", "escudo.png")
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=70, height=80)
    else:
        logo = Paragraph("No se encontró escudo.png", style_normal)

    # 2. Texto central (primera fila, columna 2)
    texto_institucional = Paragraph(
        "SECRETARÍA DE EDUCACIÓN DEL DEPARTAMENTO DE CALDAS<br/>"
        "INSTITUCIÓN EDUCATIVA DE OCCIDENTE<br/>"
        "NIT 890802641-2  DANE 117042000561<br/><br/>"
        "<font size='7'>"
        "INSTITUCIÓN EDUCATIVA DE OCCIDENTE DE ANSERMA CALDAS PLANTEL OFICIAL APROBADO POR RESOLUCION No 4859-6 DE JUNIO 23 DE 2017, "
        "RESOLUCION DE FUSION No 00507 DE MARZO 6 DE 2003 EMANADA DE LA SECRETARIA DE EDUCACION DEPARTAMENTAL Y SEGÚN PLAN DE ESTUDIOS "
        "LEY 115 Y DECRETO 1860."
        "</font>",
        style_normal
    )

    # 3. Texto derecho (primera fila, columna 3)
    texto_derecho_superior = Paragraph(
        "Página: 1<br/>"
        "Código: GAFMIR-40-02<br/>"
        "v.02<br/>"
        "26/01/2012",
        style_normal
    )

    # 4. Texto para la segunda fila
    texto_registro = Paragraph(
        "REGISTRO DE MATRÍCULA (SIMAT - EDUADMIN)", style_normal)
    texto_secretaria = Paragraph("DEPENDENCIA SECRETARÍA", style_normal)

    # --------------------------------------------------------------------
    # Construimos la estructura de la tabla
    # Fila 1 => [escudo, texto_institucional, texto_derecho_superior]
    # Fila 2 => [REGISTRO..., DEPENDENCIA, SECRETARÍA]
    data = [
        [logo, texto_institucional, texto_derecho_superior],
        ["", texto_registro,  texto_secretaria]
    ]

    # Ajusta los anchos de las columnas según tu diseño
    col_widths = [80, 408, 80]

    table = Table(data, colWidths=col_widths)

    # Estilos de la tabla
    table.setStyle(TableStyle([
        # Borde exterior y líneas internas
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 1, colors.black),
        # Alineación vertical de todas las celdas
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Opcional: alinear la imagen al centro de su celda
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        # Ajusta rellenos
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    return table

def construir_tabla_firmas():
    """
    Retorna una tabla (3 filas x 2 columnas) con el título FIRMAS en la primera fila (fusionada)
    y luego las líneas para Alumno, Padre/Acudiente, Rector y Secretaria.
    """

    styles = getSampleStyleSheet()
    style_center = ParagraphStyle(
        name='CenterStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        alignment=TA_CENTER
    )

    # Fila 1: "FIRMAS" (celda fusionada)

    # Fila 2: Alumno | Padre o Acudiente
    # Usamos <br/> para salto de línea y guiones como la "línea de firma"
    alumno = Paragraph("_______________________<br/>Estudiante<br/>  <br/>   <br/> <br/> <br/>", style_center)
    padre = Paragraph("_______________________ <br/>Padre o Acudiente<br/><font size='6'>Manifiesto que he sido informado como acudiente y me comprometo a acceder y descargar el Manual de Convivencia vigente a través del siguiente enlace en la página oficial de la institución educativa: https://iedeoccidente.edu.co/documentos/manual_de_convivencia_ieo.pdf o el QR dado en la parte inferior</font>", style_center)
    fila2 = [alumno, padre]

    # Fila 3: Rector | Secretaria
    rector = Paragraph("_______________________<br/>Rector", style_center)
    secretaria = Paragraph("", style_center)
    fila3 = [rector, secretaria]

    data = [ fila2, fila3]

    # Creamos la tabla (3 filas x 2 columnas)
    table = Table(data, colWidths=[200, 200])  # Ajusta anchos a tu gusto

    # Estilos
    table.setStyle(TableStyle([
        # Fusión de la primera fila (0,0) a (1,0)
       
        # Centrar todo el contenido
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Opcional: bordes (si deseas mostrarlos)
        # ('BOX', (0,0), (-1,-1), 1, colors.black),
        # ('INNERGRID', (0,0), (-1,-1), 0.5, colors.grey),
        # Espacios internos
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    return table


def dibujar_footer(canvas, doc):
    """
    Dibuja en el canvas el texto de contacto (teléfonos, e-mail, dirección)
    centrado en la parte inferior de la página, con letra pequeña.
    """
    canvas.saveState()
    
    # Ajusta el tamaño de fuente y tipo
    canvas.setFont("Helvetica", 8)  # Letra pequeña
    
    # Obtenemos el ancho y alto de la página actual
    # (Si usas "legal", ajusta a: width, height = legal)
    width, height = doc.pagesize
    
    # Definimos las líneas de texto que deseas mostrar
    lineas = [
        "TELÉFONOS: SECRETARÍA 314 661 03 44 e-mail iedeoccidente@sedcaldas.gov.co",
        "Cr 5 11-19 ANSERMA CALDAS"
    ]
    
    # Punto de inicio (desde el borde inferior). Ajusta según necesites
    y = 0.35 * inch  # a media pulgada del borde inferior, por ejemplo
    
    # Dibujamos cada línea de manera centrada
    for linea in reversed(lineas):
        canvas.drawCentredString(width / 2, y, linea)
        y += 10  # Separa las líneas verticalmente (10 puntos de espacio)
    
    canvas.restoreState()




def dibujar_informacion_acudiente(canvas, doc, x=6.5*inch, y=0.18*inch, width=1.5*inch, height=2.2*inch):
    """
    Dibuja un texto en un Frame a partir de (x, y), con un ancho y alto especificados.
    El texto se ajusta (wrap) automáticamente al ancho del Frame.

    Parámetros:
    - canvas: el objeto canvas de ReportLab (lo recibe en onFirstPage / onLaterPages).
    - doc: el objeto de documento (SimpleDocTemplate, etc.).
    - x, y: coordenadas de la esquina inferior izquierda del Frame (en puntos).
    - width: ancho del Frame en puntos.
    - height: alto del Frame en puntos.

    Ajusta los valores por defecto (x, y, width, height) según necesites.
    """

    # Tu texto completo
    texto = (
        "Manifiesto que he sido informado como acudiente y me comprometo a acceder y descargar "
        "el Manual de Convivencia vigente a través del siguiente enlace en la página oficial "
        "de la institución educativa: "
        "https://iedeoccidente.edu.co/documentos/manual_de_convivencia_ieo.pdf"
    )

    # Definir un estilo básico
    styles = getSampleStyleSheet()
    estilo = styles['Normal']
    estilo.fontName = "Helvetica"
    estilo.fontSize = 5      # Letra pequeña
    estilo.leading = 11      # Espacio entre líneas
    estilo.alignment = TA_JUSTIFY  # Justificar texto (opcional)

    # Creamos el Paragraph con el estilo
    p = Paragraph(texto, estilo)

    # Creamos un Frame en las coordenadas indicadas, con el ancho y alto especificados
    frame = Frame(x, y, width, height, showBoundary=0)

    # Agregamos el Paragraph al Frame para que lo dibuje en el canvas
    frame.addFromList([p], canvas)



# Ruta para generar un PDF con información completa del estudiante
@app.route('/generar_pdf', methods=['GET'])
def generar_pdf():
    codigo = request.args.get('codigo')

    if not codigo:
        return "Código no proporcionado", 400

    conexion = get_db_connection()
    with conexion.cursor() as cursor:
        sql_estudiante = """
        SELECT estugrupos.*, sedes.sede 
        FROM estugrupos 
        LEFT JOIN sedes ON estugrupos.asignacion = sedes.ind 
        WHERE codigo = %s 
        ORDER BY year DESC 
        LIMIT 1
        """
        cursor.execute(sql_estudiante, (codigo,))
        estudiante = cursor.fetchone()

    conexion.close()

    if not estudiante:
        return "Estudiante no encontrado", 404

    pdf_path = f"temp/Estudiante_{codigo}.pdf"
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    doc = SimpleDocTemplate(pdf_path, pagesize=legal, topMargin=20,   # <--- Menor margen superior
                            leftMargin=30,
                            rightMargin=30,
                            bottomMargin=50)
    elements = []
    encabezado_tabla = construir_encabezado()
    elements.append(encabezado_tabla)
    styles = getSampleStyleSheet()

    # Título
    elements.append(Paragraph("Información del Estudiante", styles['Title']))
    elements.append(Spacer(1, 10))

    # Datos del estudiante
    data = [
        ["Código:", estudiante.get("codigo", "N/A"),
         "Año:", estudiante.get("year", "N/A")],
        ["Identificación:", estudiante.get(
            "estudiante", "N/A"), "Tipo de sangre:", estudiante.get("tipoSangre", "N/A")],
        ["Nombres:", estudiante.get("nombres", "N/A"),
         "Género:", estudiante.get("genero", "N/A")],
        ["Email Estudiante:", estudiante.get(
            "email_estudiante", "N/A"), "Sede:", estudiante.get("sede", "N/A")],
        ["Fecha de Nacimiento:", estudiante.get(
            "fecnac", "N/A"), "Edad:", estudiante.get("edad", "N/A")],
        ["Lugar de Nacimiento:", estudiante.get(
            "lugarNacimiento", "N/A"), "", ""],  # Se expandirá en la tabla
        ["Tipo de Documento:", estudiante.get(
            "tdei", "N/A"), "Fecha de Expedición:", estudiante.get("fechaExpedicion", "N/A")],
        ["Lugar de Expedición:", estudiante.get(
            "lugarExpedicion", "N/A"), "", ""]  # Se expandirá en la tabla
    ]

    # Crear tabla sin líneas
    table = Table(data, colWidths=[110, 200, 110, 130], rowHeights=12)
    table.setStyle(TableStyle([
        # Alinea el contenido en la parte superior
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),      # Relleno izquierdo reducido
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),     # Relleno derecho reducido
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),    # Relleno inferior reducido
        ('TOPPADDING', (0, 0), (-1, -1), 2),       # Relleno superior reducido
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        # Negrilla en primera columna
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        # Negrilla en primera columna
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        # Negrilla en tercera columna
        ('FONTNAME', (3, 0), (3, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('SPAN', (1, 5), (3, 5)),  # Fusiona "Lugar de Nacimiento"
        ('SPAN', (1, 7), (3, 7)),  # Fusiona "Lugar de Expedición"
    ]))
    elements.append(table)
    elements.append(Spacer(1, 10))

    data = [
        ["Teléfono 1 :", estudiante.get(
            "telefono1", "N/A"), "Teléfono 2:", estudiante.get("telefono2", "N/A")],
        ["Dirección:", estudiante.get(
            "direccion", "N/A"), "Zona y lugar:", estudiante.get("lugar", "N/A")],
        ["Nivel Sisben:", estudiante.get(
            "sisben", "N/A"), "Estrato:", estudiante.get("estrato", "N/A")],
        ["RGSS", estudiante.get("eps", "N/A"), "Activo:",
         estudiante.get("activo", "N/A")],
        ["Banda:", estudiante.get(
            "banda", "N/A"), "Desertor:", estudiante.get("desertor", "N/A")],
        ["Estado anterior:", estudiante.get(
            "eanterior", "N/A"), "Estado:", estudiante.get("estado", "N/A")],  # Se expandirá en la tabla
    ]

    # Crear tabla sin líneas
    table = Table(data, colWidths=[110, 180, 110, 150], rowHeights=12)
    table.setStyle(TableStyle([
        # Alinea el contenido en la parte superior
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),      # Relleno izquierdo reducido
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),     # Relleno derecho reducido
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),    # Relleno inferior reducido
        ('TOPPADDING', (0, 0), (-1, -1), 2),       # Relleno superior reducido
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        # Negrilla en primera columna
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        # Negrilla en primera columna

    ]))
    elements.append(table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Información Académica", styles['Title']))
    elements.append(Spacer(1, 10))

    data = [
        ["Asignación:", estudiante.get(
            "asignacion", "N/A"), "Nivel:", estudiante.get("nivel", "N/A")],
        ["Número:", estudiante.get("numero", "N/A"), "", ""],
        # Dos celdas vacías para mantener el formato
        ["Sede Actual:", estudiante.get("sede", "N/A"), "", ""],
    ]
    table = Table(data, colWidths=[110, 180, 110, 150], rowHeights=12)
    table.setStyle(TableStyle([
        # Alinea el contenido en la parte superior
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),      # Relleno izquierdo reducido
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),     # Relleno derecho reducido
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),    # Relleno inferior reducido
        ('TOPPADDING', (0, 0), (-1, -1), 2),       # Relleno superior reducido
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        # Negrilla en primera columna
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        # Negrilla en primera columna
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        # Negrilla en tercera columna

    ]))

    elements.append(table)
    mi_estilo = ParagraphStyle(
        'LeftAligned',
        parent=styles['Normal'],
        alignment=0
    )
    iexterna = estudiante.get(
        "institucion_externa", "N/A")
    if iexterna != "":
        elements.append(Paragraph("Institución Externa", styles['Title']))
        elements.append(Paragraph(iexterna, mi_estilo))
        elements.append(Spacer(1, 10))

    otraInformacion = estudiante.get(
        "otraInformacion", "N/A")

    if otraInformacion != "":
        elements.append(Paragraph("Otra Información", styles['Title']))
        elements.append(Paragraph(otraInformacion, mi_estilo))
        elements.append(Spacer(1, 10))

    elements.append(Paragraph("Padres y Acudientes", styles['Title']))
    elements.append(Spacer(1, 10))
    data = [
        ["Padre:", estudiante.get(
            "padre", "N/A"), "Identificación Padre:", estudiante.get("padreid", "N/A")],
        ["Ocupación:", estudiante.get(
            "ocupacionpadre", "N/A").replace("_", " "), "Teléfono Padre:", estudiante.get("telefonopadre", "N/A")],
        ["Madre:", estudiante.get(
            "madre", "N/A"), "Identificación Madre:", estudiante.get("madreid", "N/A")],
        ["Ocupación:", estudiante.get(
            "ocupacionmadre", "N/A").replace("_", " "), "Teléfono Madre:", estudiante.get("telefonomadre", "N/A")],
        ["Acudiente:", estudiante.get(
            "acudiente", "N/A"), "Identificación Acudiente:", estudiante.get("idacudiente", "N/A")],
        ["Parentesco Acudiente:", estudiante.get(
            "parentesco", "N/A"), "Teléfono:", estudiante.get("telefono_acudiente", "N/A")],


    ]
    table = Table(data, colWidths=[110, 180, 120, 150], rowHeights=12)
    table.setStyle(TableStyle([
        # Alinea el contenido en la parte superior
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),      # Relleno izquierdo reducido
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),     # Relleno derecho reducido
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),    # Relleno inferior reducido
        ('TOPPADDING', (0, 0), (-1, -1), 2),       # Relleno superior reducido
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        # Negrilla en primera columna
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        # Negrilla en primera columna
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),

    ]))
    elements.append(table)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Información Referencial", styles['Title']))
    elements.append(Spacer(1, 10))
    data = [["Victima de Conflicto:", estudiante.get("victimaConflicto", "N/A"), "Desplazado de :", estudiante.get("lugarDesplazamiento", "N/A")], [
        "Fecha desplazamiento:", estudiante.get("fechaDesplazamiento", "N/A"), "H.E.D.:", estudiante.get("HED", "N/A")],
         ["Etnia:",estudiante.get("etnia", "N/A")], ["Discapacidad:", estudiante.get("discapacidad", "N/A"),]]
    table = Table(data, colWidths=[110, 180, 110, 150], rowHeights=12)
    table.setStyle(TableStyle([
        # Alinea el contenido en la parte superior
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),      # Relleno izquierdo reducido
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),     # Relleno derecho reducido
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),    # Relleno inferior reducido
        ('TOPPADDING', (0, 0), (-1, -1), 2),       # Relleno superior reducido
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        # Negrilla en primera columna
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        # Negrilla en primera columna
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),

    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))
    """ ruta_imagen = os.path.join("images", "qrcode.jpg")
    if os.path.exists(ruta_imagen):
        # Crear el objeto Image, ajustando ancho y alto según necesites
        imagen_qr = Image(ruta_imagen, width=100, height=100)
        imagen_qr.hAlign = 'RIGHT'
        elements.append(Spacer(1, 10))
        elements.append(imagen_qr)
    else:
        elements.append(
            Paragraph("Imagen QR no encontrada.", styles['Normal'])) """
        
    tabla_firmas = construir_tabla_firmas()
    elements.append(tabla_firmas)    
    # Generar PDF
    doc.build(elements, onFirstPage=agregar_recuadro,
              onLaterPages=agregar_recuadro)
    return send_file(pdf_path, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
