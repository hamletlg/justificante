#!/usr/bin/env python3
"""Comprueba un justificante de asistencia usando SOLO el propio PDF.

Uso:  python3 verificar_pdf.py justificante.pdf

Extrae el texto y recalcula el SHA-256 del registro y de la imagen incrustada, y los
compara con las huellas impresas. Si alguien ha editado el nombre, el DNI, la fecha de
la sesión o la firma, no coinciden.

Requiere: poppler-utils (pdftotext, pdfimages).
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

MESES = {m: i + 1 for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"])}


def iso_de(texto):
    """'20 de octubre de 2026' -> '2026-10-20'."""
    m = re.search(r"(\d{1,2}) de (\w+) de (\d{4})", texto)
    if not m:
        return None
    mes = MESES.get(m.group(2).lower())
    if not mes:
        return None
    return "%s-%02d-%02d" % (m.group(3), mes, int(m.group(1)))


def seccion_curso(lineas):
    """Líneas entre 'ACCIÓN FORMATIVA' y la primera 'Fecha:'."""
    try:
        i = next(n for n, l in enumerate(lineas) if l.strip().startswith("ACCIÓN FORMATIVA"))
    except StopIteration:
        return None
    partes = []
    for l in lineas[i + 1:]:
        if l.strip().startswith("Fecha:"):
            break
        if l.strip():
            partes.append(l.strip())
    return " ".join(partes) or None


def main(ruta):
    if not os.path.exists(ruta):
        print("No existe el fichero:", ruta)
        return 2

    texto = subprocess.run(["pdftotext", "-layout", ruta, "-"],
                           capture_output=True, text=True, check=True).stdout
    lineas = texto.splitlines()

    def buscar(pat):
        m = re.search(pat, texto, re.M)
        return m.group(1).strip() if m else None

    curso = seccion_curso(lineas)
    fecha_sesion_txt = buscar(r"^Fecha:\s+(.+)$")
    nombre_completo = buscar(r"^Nombre y apellidos:\s+(.+)$")
    dni = buscar(r"^DNI / NIE:\s+(\S+)$")
    img_impresa = buscar(r"HUELLA SHA-256 DE LA IMAGEN DE LA FIRMA\s*\n\s*([0-9a-f]{64})")
    reg_impresa = buscar(r"HUELLA SHA-256 DEL REGISTRO\s*\n\s*([0-9a-f]{64})")

    faltan = [n for n, v in [("curso", curso), ("fecha", fecha_sesion_txt),
                             ("nombre", nombre_completo), ("DNI", dni),
                             ("huella de imagen", img_impresa), ("huella de registro", reg_impresa)] if not v]
    if faltan:
        print("FALTAN CAMPOS en el texto del PDF:", ", ".join(faltan))
        print("¿Seguro que es un justificante generado por la aplicación?")
        return 2

    if ", " not in nombre_completo:
        print("El campo de nombre no tiene el formato 'APELLIDOS, Nombre'.")
        return 2
    apellidos, nombre = nombre_completo.rsplit(", ", 1)
    fecha_sesion = iso_de(fecha_sesion_txt) or fecha_sesion_txt

    # 1) la imagen incrustada, tal cual
    tmp = tempfile.mkdtemp(prefix="verif-")
    subprocess.run(["pdfimages", "-j", ruta, os.path.join(tmp, "img")],
                   capture_output=True, check=True)
    imagenes = sorted(f for f in os.listdir(tmp) if f.startswith("img"))
    if not imagenes:
        print("El PDF no contiene ninguna imagen: falta la firma.")
        return 2
    ruta_img = os.path.join(tmp, imagenes[0])
    with open(ruta_img, "rb") as fh:
        img_real = hashlib.sha256(fh.read()).hexdigest()

    # 2) la huella del registro, con el mismo JSON canónico que usa la app
    canon = json.dumps(
        {"apellidos": apellidos, "curso": curso, "dni": dni,
         "fecha_sesion": fecha_sesion, "img_sha256": img_impresa, "nombre": nombre},
        separators=(",", ":"), ensure_ascii=False)
    reg_real = hashlib.sha256(canon.encode("utf-8")).hexdigest()

    print("Documento :", os.path.basename(ruta))
    print("Curso     :", curso)
    print("Sesión    :", fecha_sesion_txt, "->", fecha_sesion)
    print("Asistente :", apellidos, "/", nombre, "/ DNI", dni)
    print()
    print("Imagen de la firma")
    print("  impresa    :", img_impresa)
    print("  recalculada:", img_real, "->", "IGUAL" if img_real == img_impresa else "DISTINTA")
    print("Registro")
    print("  canon      :", canon)
    print("  impresa    :", reg_impresa)
    print("  recalculada:", reg_real, "->", "IGUAL" if reg_real == reg_impresa else "DISTINTA")
    print()
    ok = img_real == img_impresa and reg_real == reg_impresa
    print("RESULTADO:", "DOCUMENTO ÍNTEGRO" if ok else "EL DOCUMENTO NO CUADRA: se ha modificado algo")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
