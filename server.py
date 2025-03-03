#python -m waitress --listen=0.0.0.0:8000 server:app

from flask import Flask, request, render_template, jsonify, send_file
import pymysql
import os
from dotenv import load_dotenv
from reportlab.lib.pagesizes import legal
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch

por_margen=0.3

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

    doc = SimpleDocTemplate(pdf_path, pagesize=legal)
    elements = []
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
    iexterna=estudiante.get(
        "institucion_externa", "N/A")
    if iexterna!="":    
        elements.append(Paragraph("Institución Externa", styles['Title']))
        elements.append(Paragraph(iexterna, mi_estilo))
        elements.append(Spacer(1, 10))


    otraInformacion=estudiante.get(
        "otraInformacion", "N/A")

    if otraInformacion!="":
        elements.append(Spacer(1, 10))
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
        "Fecha desplazamiento:", estudiante.get("fechaDesplazamiento", "N/A"), "H.E.D.:", estudiante.get("HED", "N/A")], ["Discapacidad:", estudiante.get("discapacidad", "N/A"),]]
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
    # Generar PDF
    doc.build(elements, onFirstPage=agregar_recuadro, onLaterPages=agregar_recuadro)
    return send_file(pdf_path, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
